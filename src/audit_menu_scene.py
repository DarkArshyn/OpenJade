"""Audit stored transforms, instance lighting and object identity in an existing preview."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from probe_menu3d import records
from inspect_menu_scene_links import static_links
from menu_primary_geometry import primary_mesh, instance_colors
from menu_fog_state import transform_fog_points
from menu_colored_raster import raster
from resolve_camera_function_bodies import HASH


def instance_lighting(data, offset, vertex_count):
    if offset < 0 or offset + 22 > len(data):
        raise ValueError('Truncated instance descriptor')
    flags = struct.unpack_from('<I', data, offset + 8)[0]
    count = struct.unpack_from('<I', data, offset + 18)[0]
    if count != vertex_count or offset + 22 + count * 4 > len(data):
        raise ValueError('Instance color count/extent mismatch')
    return dict(flags=f'0x{flags:08X}', color_count=count,
                direct_recorded_colors=bool(flags & 0x40 and count),
                native_branch='00432600: direct instance RGB and clear light-enable bit' if flags & 0x40 and count else 'conditional lighting path unresolved')


def audit(source, scene_dir, output):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASH: raise ValueError('Unsupported source')
    scene = json.loads((scene_dir / 'scene.json').read_text())
    if scene['source_sha256'] != HASH: raise ValueError('Scene source mismatch')
    output.mkdir(parents=True, exist_ok=False)
    by = {}
    for record in records(raw): by.setdefault(record['key'], []).append(record)
    def payload(key):
        rows = by[key]
        if len(rows) != 1: raise ValueError('Ambiguous resource')
        row = rows[0]
        return raw[row['offset']+12:row['end']]
    camera = scene['camera']
    data = payload(camera['key']); n = struct.unpack_from('<I', data, 16)[0]
    matrix = np.array(struct.unpack_from('<16f', data, n+30)).reshape(4, 4)
    right, up, forward = matrix[0,:3], matrix[2,:3], -matrix[1,:3]
    angle = math.radians(camera['yaw_adjustment'])
    right, forward = math.cos(angle)*right-math.sin(angle)*forward, math.sin(angle)*right+math.cos(angle)*forward
    angle = math.radians(camera['pitch_adjustment'])
    up, forward = math.cos(angle)*up-math.sin(angle)*forward, math.sin(angle)*up+math.cos(angle)*forward
    basis = np.array([right, -forward, up])
    materials = {item['key']: item['slot'] for item in scene['materials']}
    objects, textures, rows = [], {}, []
    for index, accepted in enumerate(scene['accepted'], 1):
        data = payload(accepted['key']); link = static_links(data)
        v, tri, groups, ids, nv, colors, layout = primary_mesh(payload(link['mesh']))
        matrix = np.array(struct.unpack_from('<16f', data, link['matrix_offset'])).reshape(4, 4)
        world = transform_fog_points(v[:,:3], matrix)
        rli, color_offset = instance_colors(data, link['link_offset'], nv)
        try: lighting = instance_lighting(data, link['link_offset'], nv)
        except ValueError as error: lighting = dict(unresolved=str(error))
        row = dict(key=accepted['key'], name=link['name'], identity=index,
                   translation=matrix[3,:3].tolist(), rotation_rows=matrix[:3,:3].tolist(),
                   scale_fields=matrix[:3,3].tolist(), matrix_flags=struct.unpack_from('<I',data,link['matrix_offset']+64)[0],
                   orthogonality_error=float(np.max(np.abs(matrix[:3,:3]@matrix[:3,:3].T-np.eye(3)))),
                   world_bounds=[world.min(0).tolist(),world.max(0).tolist()], lighting=lighting,
                   mesh=link['mesh'], normal_array_present=bool(struct.unpack_from('<I',payload(link['mesh']),40)[0]) if layout['vertex_offset']==44 else None,
                   recorded_rgb_range=None if rli is None else [np.rint(rli.min(0)*255).astype(int).tolist(),np.rint(rli.max(0)*255).astype(int).tolist()],
                   color_offset=color_offset, color_groups=accepted.get('color_groups',[]))
        rows.append(row)
        if accepted.get('fog_states'): continue
        rgb = [(index*67)%220+30, (index*113)%220+30, (index*151)%220+30]
        row['identity_rgb'] = rgb
        pack = payload(link['material_pack'])
        keys = struct.unpack_from('<'+'I'*((len(pack)-12)//4),pack,12) if struct.unpack_from('<I',pack)[0]==4 else None
        mapped = []
        for slot, count in groups:
            leaf = f'0x{keys[slot]:08X}' if keys else link['material_pack']
            texture = np.array(Image.open(scene_dir/f'material-{materials[leaf]}.png').convert('RGBA'))
            texture[:,:,:3] = rgb
            target = len(textures); textures[target] = texture; mapped.append((target,count))
        objects.append(dict(vertices=world,uv=v[:,3:],triangles=tri,groups=mapped,colors=np.ones((len(v),3))))
    identity, _, _ = raster(objects,textures,np.array(camera['position']),basis,camera['vertical_fov'])
    pixels = np.array(identity); draw = ImageDraw.Draw(identity)
    for row in rows:
        if 'identity_rgb' not in row: continue
        yy,xx = np.where(np.all(pixels==row['identity_rgb'],axis=2))
        row['diagnostic_visible_pixels'] = len(xx)
        if len(xx):
            row['diagnostic_screen_bounds'] = [int(xx.min()),int(yy.min()),int(xx.max()),int(yy.max())]
            if len(xx)>600: draw.text((int(np.median(xx)),int(np.median(yy))),str(row['identity']),fill='white',stroke_width=1,stroke_fill='black')
    identity.save(output/'object-identities.png')
    report = dict(source_sha256=HASH,camera=camera,objects=rows,excluded=scene['excluded'],
                  limitations=['Identity rendering omits fog and retains diagnostic alpha threshold; bounds are not original-game visibility',
                               'Stored transforms are inspected, not validated as runtime world transforms; hierarchy/animation unresolved',
                               'One screenshot cannot independently determine camera, object placement and lighting',
                               'Static branch analysis is not a capture of runtime graphics state'])
    (output/'audit.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(len(rows),'objects audited')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('scene',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();audit(a.source,a.scene,a.output)
