"""Export verified fog/fixture passes from existing research exports to OJSCN003/004.

Effective time is a chosen sample, not a captured original-game animation phase.
Original inputs are read only. Lighting selectors 0/3 remain explicitly diagnostic.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from PIL import Image


def pass_parameters(stage, time):
    """Preserve static offsets; advance only native dynamic U/V flags."""
    flags = stage['flags']
    mode = stage['blend']
    if (mode, stage['depth_write']) not in ((0, True), (1, False), (6, False)):
        raise ValueError('Unsupported blend/depth combination')
    offset = [(r * (time if flags & bit else 1)) % 1
              for r, bit in zip(stage['rate'], (0x40000000, 0x80000000))]
    return mode, [*stage['scale'], *offset, stage['alpha'], 2., 0., 1.]


BALCONY = 'Menu3D_FarahRoom_Balcony.gao'


# Opaque draws matched by native index signature in the fixed GOG menu.
TRUNK_FOG_MATERIALS = {'0x30000C95', '0x30000CA9'}
MENU_FOG_MATERIALS = {
    '0x30000CBA': {'0x30000CB0', '0x30000CB1'},
    '0x30000CBC': TRUNK_FOG_MATERIALS,
    '0x30000CBF': TRUNK_FOG_MATERIALS,
    '0x30000CC8': TRUNK_FOG_MATERIALS,
    '0x30000CCA': TRUNK_FOG_MATERIALS,
    '0x30000CD0': TRUNK_FOG_MATERIALS,
    '0x30000CD6': TRUNK_FOG_MATERIALS,
    '0x30000CD9': {'0x30000C93', '0x30000C94', '0x30000C9A', '0x30000C9B', '0x30000C9D', '0x30000C9F', '0x30000CA0', '0x30000CA1', '0x30000CA2', '0x30000CA3', '0x30000CA4', '0x30000CA5', '0x30000CAD', '0x30000CAE', '0x30000D43', '0x3000FCCD'},
    '0x30000CDB': TRUNK_FOG_MATERIALS,
    '0x30000CDD': TRUNK_FOG_MATERIALS,
}


def balcony_gain(name, mode, stages, enabled):
    """Isolate the unverified direct-color MODULATE2X hypothesis."""
    return 2. if enabled and name == BALCONY and mode == 0 and not stages else 1.


def convert(source, camera, output, time=0., balcony_modulate2x=False, animate_uv=False, palm_source=None, masonry_fog="normal"):
    fog_flags = {"off": 0, "normal": 2, "inverted": 4}[masonry_fog]
    animate_uv = animate_uv or palm_source is not None
    if not math.isfinite(time) or time < 0: raise ValueError('Invalid effective time')
    if output.exists(): raise FileExistsError(output)
    report = json.loads((source/'scene.json').read_text(encoding='utf-8'))
    poses = json.loads(camera.read_text(encoding='utf-8'))
    if report['source_sha256'] != poses['source_sha256']: raise ValueError('Scene/camera source mismatch')
    accepted = {o['name']: o for o in report['accepted']}
    if len(accepted) != len(report['accepted']) or any(o['omitted_groups'] for o in accepted.values()):
        raise ValueError('Ambiguous or incomplete object export')
    if balcony_modulate2x:
        target = accepted.get(BALCONY, {})
        if (report['source_sha256'] != '96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'
                or target.get('key') != '0x30000CD9'
                or target.get('triangles') != 8898):
            raise ValueError('Unsupported balcony diagnostic source')
    materials = {m['slot']: m for m in report['materials']}
    matrix = poses['poses'][0]['matrix']
    if poses['poses'][0]['time'] != 0: raise ValueError('Expected initial Camera02')
    eye = matrix[3][:3]; forward = [-v for v in matrix[1][:3]]
    camera_values = eye + [-v for v in matrix[0][:3]] + matrix[2][:3] + forward + [poses['vertical_fov']]
    vertices, uvs, groups = [], [], []
    name, current = None, None
    for line in (source/'scene.obj').read_text(encoding='utf-8').splitlines():
        p=line.split()
        if not p or p[0].startswith('#'): continue
        if p[0]=='o': name=' '.join(p[1:]); current=None
        elif p[0]=='v':
            if len(p)!=7: raise ValueError('Expected XYZ RGB')
            vertices.append(list(map(float,p[1:])))
        elif p[0]=='vt':
            if len(p)!=3: raise ValueError('Expected UV')
            uvs.append(list(map(float,p[1:])))
        elif p[0]=='usemtl':
            if name not in accepted: raise ValueError('Unknown OBJ object')
            slot=int(p[1].removeprefix('material-'))
            if slot not in materials: raise ValueError('Unknown material slot')
            current=dict(name=name,slot=slot,vertices=[]);groups.append(current)
        elif p[0]=='f':
            if current is None or len(p)!=4: raise ValueError('Expected grouped triangle')
            for item in p[1:]:
                pair=list(map(int,item.split('/')))
                if len(pair)!=2 or not(0<pair[0]<=len(vertices) and 0<pair[1]<=len(uvs)): raise ValueError('Invalid OBJ index')
                v=vertices[pair[0]-1];uv=uvs[pair[1]-1]
                current['vertices'].append([*v[:3],uv[0],1-uv[1],*v[3:]])
    if palm_source is not None:
        from menu_flies import append_flies
        append_flies(palm_source,source,materials,accepted,groups)
    counts={name:sum(len(g['vertices'])//3 for g in groups if g['name']==name) for name in accepted}
    if any(counts[name]!=row['triangles'] for name,row in accepted.items()): raise ValueError('Triangle count mismatch')
    # Keep object/group pass order. Fog is deferred and sorted by object-center view depth.
    solid=[g for g in groups if not accepted[g['name']]['fog_states']]
    fog=[g for g in groups if accepted[g['name']]['fog_states']]
    def distance(g):
        center=[sum(v[i] for v in g['vertices'])/len(g['vertices']) for i in range(3)]
        return sum((center[i]-eye[i])*forward[i] for i in range(3))
    fog.sort(key=distance,reverse=True)
    image_names=[];expanded=[];draws=[];audit=[]
    for g in solid+fog:
        row=accepted[g['name']];slot=g['slot'];material=materials[slot]
        color_groups=[x for x in row['color_groups'] if x['material']==material['key']]
        if len(color_groups)!=1: raise ValueError('Ambiguous material color state')
        color=color_groups[0]
        verified_masonry = (row.get('key') == '0x30000CD9' and g['name'] == BALCONY
                            and material['key'] == '0x30000CA0' and color['mode'] == 0
                            and not material['stages'] and not row['fog_states'])
        verified_fog = (report['source_sha256'] == '96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'
                        and material['key'] in MENU_FOG_MATERIALS.get(row.get('key'), ()))
        verified_leaf = (report['source_sha256'] == '96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'
                         and row.get('key') == '0x30000CCF' and material['key'] == '0x30000CB0'
                         and color['mode'] == 0 and not material['stages'])
        verified_trunk = (report['source_sha256'] == '96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'
                          and row.get('key') == '0x30000CBF' and material['key'] == '0x30000C95'
                          and color['mode'] == 0 and not material['stages'])
        verified_fog = verified_fog or verified_leaf
        rates=[]
        if 'fly_uv' in row:
            scale,rate=row['fly_uv'];rates=[rate]
            passes=[(f'material-{slot}.png',1,[*scale,*[(time*r)%1 for r in rate],1.,1.,0.,1.])]
        elif row['fog_states']:
            if len(row['fog_states'])!=1: raise ValueError('Ambiguous fog state')
            state=row['fog_states'][0]
            if state['flags']!='0x40014205': raise ValueError('Unsupported fog flags')
            # OBJ UVs already include the export's sampled fog motion.
            motion=state['motion'];du=motion['rate_u']*(time-report['fog_time'])
            passes=[(f'material-{slot}.png',1,[1.,1.,du%1,0.,1.,1.,0.,2.])]
            rates=[[motion['rate_u'],0.]]
        elif material.get('sky_state') and g['name'] in ('Menu3D_sky.gao','2100_ciel_nuit_lune.gao'):
            state=material['sky_state']
            expected=0x00014607 if material['key']=='0x30000D1B' else 0x00006007
            if material['key'] not in ('0x30000D1B','0x30000CAC') or state['flags']!=expected:
                raise ValueError('Unsupported sky state')
            passes=[(f'material-{slot}.png',state['blend'],[1.,1.,0.,0.,state['alpha'],state['rgb_gain'],0.,1.])]
        elif material['stages']:
            passes=[]
            for i,stage in enumerate(material['stages']):
                rates.append([r if stage['flags'] & bit else 0. for r,bit in zip(stage['rate'],(0x40000000,0x80000000))])
                mode,params=pass_parameters(stage,time)
                passes.append((f'material-{slot}-stage-{i}.png',mode,params))
        else:
            passes=[(f'material-{slot}.png',0,[1.,1.,0.,0.,1.,2. if verified_leaf or verified_trunk else balcony_gain(g['name'],color['mode'],material['stages'],balcony_modulate2x or verified_masonry),.5,0.])]
        if not rates: rates=[[0.,0.] for _ in passes]
        for (image,mode,params),rate in zip(passes,rates):
            if image not in image_names: image_names.append(image)
            layer=image_names.index(image);first=len(expanded)
            for vertex in g['vertices']:
                vertex=vertex.copy()
                if color['mode']==2:
                    # Reconstruct the verified constant explicitly, avoiding a second x2.
                    vertex[5:8]=[c*2/255 for c in color['constant_rgb']]
                expanded.append([*vertex,float(layer)])
            leaf_alpha = verified_leaf and palm_source is not None
            if leaf_alpha:
                params[6:8] = [150 / 255, 1.]
            if verified_trunk and palm_source is not None:
                params[7] = 1.
            flags = (0 if mode or leaf_alpha else 1) | (fog_flags if (verified_fog and mode == 0) or "fly_uv" in row else 0)
            draws.append((first,len(g['vertices']),7 if leaf_alpha else mode,flags,params))
            audit.append(dict(object=g['name'],material=material['key'],texture=image,blend=7 if leaf_alpha else mode,depth_write=mode==0 and not leaf_alpha,vertex_fog=masonry_fog if (verified_fog and mode == 0) or 'fly_uv' in row else 'off',
                              uv_rate=rate if animate_uv else [0.,0.],parameters=params,color_mode=color['mode'],color_status='GOG D3D9 texture x diffuse x2' if verified_masonry or verified_leaf or verified_trunk else 'verified constant x2' if color['mode']==2 else ('balcony direct-color x2 hypothesis; runtime path unverified' if balcony_gain(g['name'],color['mode'],material['stages'],balcony_modulate2x)==2 else 'exported vertex colors; active runtime lighting unresolved')))
    # Opaque passes establish depth first. Sort transparent passes back to front;
    # stable ordering keeps the stages of a single fixture in their original order.
    def draw_distance(draw):
        first,count=draw[:2]
        center=[sum(v[i] for v in expanded[first:first+count])/count for i in range(3)]
        return sum((center[i]-eye[i])*forward[i] for i in range(3))
    order=sorted(range(len(draws)),key=lambda i:(0 if draws[i][2] == 0 else 1 if draws[i][2] == 7 else 2,-draw_distance(draws[i]) if draws[i][2] not in (0,7) else 0))
    reordered=[];sorted_draws=[]
    for i in order:
        first,count,blend,write,params=draws[i]
        sorted_draws.append((len(reordered),count,blend,write,params))
        reordered.extend(expanded[first:first+count])
    expanded=reordered;draws=sorted_draws;audit=[audit[i] for i in order]
    size=512;pixels=bytearray();textures=[]
    for name in image_names:
        path=source/name
        with Image.open(path) as image:
            original=image.size
            if not (0 < image.width <= size and 0 < image.height <= size):
                raise ValueError('Texture exceeds bounded 512x512 storage slot')
            padded=Image.new('RGBA',(size,size))
            padded.paste(image.convert('RGBA'),(0,0))
            pixels.extend(padded.tobytes())
        textures.append(dict(file=name,original_size=original,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    values=camera_values+[f for v in expanded for f in v]+[f for d in draws for f in d[4]]
    if not all(math.isfinite(x) for x in values): raise ValueError('Non-finite export')
    blob=bytearray(b'OJSCN004' if animate_uv else b'OJSCN003');blob.extend(struct.pack('<4I13f',len(expanded),size,size,len(image_names),*camera_values))
    for v in expanded: blob.extend(struct.pack('<9f',*v))
    blob.extend(pixels);blob.extend(struct.pack('<I',len(draws)))
    for first,count,mode,write,params in draws: blob.extend(struct.pack('<4I8f',first,count,mode,write,*params))
    for texture in textures: blob.extend(struct.pack('<2I',*texture['original_size']))
    if animate_uv:
        for row in audit:
            if not all(math.isfinite(r) and abs(r)<=1024 for r in row['uv_rate']): raise ValueError('Invalid UV rate')
            blob.extend(struct.pack('<2f',*row['uv_rate']))
    palm_counts = {}
    if palm_source is not None:
        from export_palm_controls import append_palms
        palm_counts = append_palms(blob, palm_source, expanded, draws, audit)
        blob[:8] = b'OJSCN005'
    if len(blob)>256*1024*1024: raise ValueError('Package too large')
    output.mkdir(parents=True,exist_ok=False)
    if palm_source is not None:
        from export_rain_controls import export_rain
        (output/'menu.rain').write_bytes(export_rain(palm_source))
        (output/'menu.splash').write_bytes(export_rain(palm_source,splashes=True))
        (output/'menu.pollen').write_bytes(export_rain(palm_source,pollen=True))
        (output/'menu.birds').write_bytes(export_rain(palm_source,birds=True))
        from export_mesh_flight import export_mesh_flight
        (output/'menu.flight').write_bytes(export_mesh_flight(palm_source))
        from export_rido2 import export_rido2
        for draw, entry in zip(draws, audit):
            if draw[2] == 7:
                from export_leaf import export_leaf
                (output/'menu.leaf').write_bytes(export_leaf(palm_source, expanded, draw))

        for draw, entry in zip(draws, audit):
            if entry['material'] == '0x30000C95' and draw[4][7] == 1.:
                from export_leaf import export_trunk
                layer = int(expanded[draw[0]][8])
                with Image.open(source / image_names[layer]) as image:
                    base = image.convert('RGBA').tobytes()
                (output/'menu.trunk').write_bytes(export_trunk(palm_source, layer, base))
        for draw, entry in zip(draws, audit):
            if entry['object'] == 'Menu3D_FarahRoom_Balcony.gao' and entry['material'] == '0x30000D43':
                from inspect_menu_palms import HASH, records
                native = palm_source.read_bytes()
                if hashlib.sha256(native).hexdigest() != HASH or draw[1] != 72:
                    raise ValueError('Unsupported native glow mask')
                record = next(r for r in records(native) if r['key'] == '0x30000D43')
                alpha = native[record['offset'] + 12 + 27]
                (output/'menu.glow').write_bytes(b'OJGLOW01' + struct.pack('<III', draw[0], draw[1], alpha))
        for instance in (1, 2, 3, 4):
            control = export_rido2(palm_source, expanded, draws, audit, instance=instance)
            (output/f'menu.rido{instance}').write_bytes(control)
    (output/'menu.ojscene').write_bytes(blob)
    manifest=dict(pollen_sidecar="menu.pollen" if palm_source is not None else None, pollen_runtime_reserved_triangles=40 if palm_source is not None else 0, flight_sidecar="menu.flight" if palm_source is not None else None, flight_runtime_triangles=66 if palm_source is not None else 0, bird_sidecar="menu.birds" if palm_source is not None else None, bird_runtime_reserved_triangles=30 if palm_source is not None else 0, splash_runtime_reserved_triangles=320 if palm_source is not None else 0, rain_sidecar="menu.rain" if palm_source is not None else None, rain_runtime_reserved_triangles=600 if palm_source is not None else 0, rain_runtime_extra_texture_layers=1 if palm_source is not None else 0, palm_vertices=palm_counts,version=5 if palm_source is not None else 4 if animate_uv else 3,animate_uv=animate_uv,source_sha256=report['source_sha256'],source_obj_sha256=hashlib.sha256((source/'scene.obj').read_bytes()).hexdigest(),
        source_report_sha256=hashlib.sha256((source/'scene.json').read_bytes()).hexdigest(),camera_sha256=hashlib.sha256(camera.read_bytes()).hexdigest(),
        balcony_modulate2x_diagnostic=balcony_modulate2x,package_sha256=hashlib.sha256(blob).hexdigest(),object_count=len(counts),objects=counts,geometry_triangles=sum(counts.values()),
        submitted_triangles=len(expanded)//3,texture_layers=len(image_names),textures=textures,draws=audit,effective_time=time,
        limitations=['Initial phase is chosen, not captured; OJSCN004 advances dynamic UV rates with runtime elapsed seconds' if animate_uv else 'Fixed exported phase; no wall-clock animation',
                    'Runtime sorts transparent group centers per camera pose; native sorting and intersecting triangles remain unresolved',
                    'Mode 0/3 colors and sRGB/linear behavior remain diagnostic; faithful scene lighting is not established',
                    'Native base-level dimensions and pixels preserved in padded transport slots; native leaf/trunk mip chains supplied by sidecars when a frozen source is provided; other runtime mipmaps are generated diagnostics',
                    'No fire particles or actual light emission from the fixtures'])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f"{len(counts)} objects; {sum(counts.values())} geometry triangles; {len(expanded)//3} submitted triangles; {len(draws)} passes; {len(image_names)} textures")

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('camera',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--time',type=float,default=0.,help='Effective animation time in seconds (fixed sample)')
    p.add_argument('--balcony-modulate2x',action='store_true',help='Diagnostic only: double mode-0 balcony modulation; not a verified lighting fix')
    p.add_argument('--animate-uv',action='store_true',help='Export OJSCN004 dynamic UV rates; --time is the initial phase')
    p.add_argument('--palm-source',type=Path,help='Frozen decoded menu for OJSCN005 vertex deformation')
    p.add_argument('--masonry-fog', choices=['off','normal','inverted'], default='normal', help='Measured GOG balcony vertex fog; normal corresponds to InvertFogRange=0')
    a=p.parse_args();convert(a.source,a.camera,a.output,a.time,a.balcony_modulate2x,a.animate_uv,a.palm_source,a.masonry_fog)
