"""Bridge the existing common-space OBJ export to a bounded Vulkan research package.

No original data is bundled with this script. Output is local, unversioned data.
Only single-stage non-fog objects are supported. This is not a general OBJ importer.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from PIL import Image


def convert(source, camera, output):
    report = json.loads((source / 'scene.json').read_text(encoding='utf-8'))
    poses = json.loads(camera.read_text(encoding='utf-8'))
    if report['source_sha256'] != poses['source_sha256']:
        raise ValueError('Scene and camera must come from the same decoded source')
    materials = {row['key']: row for row in report['materials']}
    accepted, excluded = {}, []
    for row in report['accepted']:
        reason = ('fog' if row['fog_states'] else
                  'multi-stage or omitted material groups' if row['omitted_groups'] or
                  any(materials[g['material']]['stages'] for g in row['color_groups']) else None)
        if reason:
            excluded.append(dict(name=row['name'], reason=reason))
        else:
            if row['name'] in accepted:
                raise ValueError('Ambiguous object name')
            accepted[row['name']] = row
    vertices, uvs, faces, counts = [], [], [], {}
    name, slot = None, None
    for line in (source / 'scene.obj').read_text(encoding='utf-8').splitlines():
        parts = line.split()
        if not parts or parts[0].startswith('#'):
            continue
        tag = parts[0]
        if tag == 'v':
            if len(parts) != 7: raise ValueError('Expected XYZ and RGB')
            vertices.append(tuple(map(float, parts[1:])))
        elif tag == 'vt':
            if len(parts) != 3: raise ValueError('Expected UV')
            uvs.append(tuple(map(float, parts[1:])))
        elif tag == 'o': name = ' '.join(parts[1:])
        elif tag == 'usemtl': slot = int(parts[1].removeprefix('material-'))
        elif tag == 'f' and name in accepted:
            if len(parts) != 4 or slot is None: raise ValueError('Expected material and triangles')
            points = []
            for item in parts[1:]:
                pair = list(map(int, item.split('/')))
                if len(pair) != 2 or not (0 < pair[0] <= len(vertices) and 0 < pair[1] <= len(uvs)):
                    raise ValueError('Invalid OBJ index')
                v, uv = vertices[pair[0]-1], uvs[pair[1]-1]
                points.append((*v[:3], uv[0], 1-uv[1], *v[3:], slot))
            faces.extend(points)
            counts[name] = counts.get(name, 0) + 1
    if not faces: raise ValueError('Empty scene')
    for name, row in accepted.items():
        if counts.get(name, 0) != row['triangles']: raise ValueError('Triangle count mismatch: '+name)
    used = sorted({int(v[-1]) for v in faces})
    layers = {slot: i for i, slot in enumerate(used)}
    # Equal-size array layers simplify the first backend; report every resize.
    size = 512
    texture_data, texture_report = bytearray(), []
    for slot in used:
        path = source / f'material-{slot}.png'
        with Image.open(path) as image:
            image = image.convert('RGBA')
            original = image.size
            image = image.resize((size, size), Image.Resampling.NEAREST)
            texture_data.extend(image.tobytes())
        texture_report.append(dict(slot=slot, layer=layers[slot], original_size=original,
                                   sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    matrix = poses['poses'][0]['matrix']
    if poses['poses'][0]['time'] != 0: raise ValueError('Expected initial camera pose')
    # Row-basis convention validated by the existing diagnostic raster: -X, +Z, -Y.
    camera_values = matrix[3][:3] + [-v for v in matrix[0][:3]] + matrix[2][:3] + [-v for v in matrix[1][:3]] + [poses['vertical_fov']]
    all_values = camera_values + [value for v in faces for value in v]
    if not all(math.isfinite(x) for x in all_values): raise ValueError('Non-finite scene data')
    blob = bytearray(b'OJSCN001')
    blob.extend(struct.pack('<4I13f', len(faces), size, size, len(used), *camera_values))
    for v in faces:
        blob.extend(struct.pack('<9f', *v[:-1], layers[int(v[-1])]))
    blob.extend(texture_data)
    output.mkdir(parents=True, exist_ok=False)
    (output/'menu.ojscene').write_bytes(blob)
    evidence = dict(source_sha256=report['source_sha256'], obj_sha256=hashlib.sha256((source/'scene.obj').read_bytes()).hexdigest(),
        camera_sha256=hashlib.sha256(camera.read_bytes()).hexdigest(), package_sha256=hashlib.sha256(blob).hexdigest(),
        objects=counts, object_count=len(counts), triangles=len(faces)//3, textures=texture_report, excluded=excluded,
        vertical_fov=poses['vertical_fov'], limitations=['Fixed initial Camera02 candidate; no animation',
        'Textures resampled to 512x512 with nearest sampling; single base level',
        'Stored diagnostic vertex colors; no native dynamic lighting', 'Alpha cutout threshold 0.5; no blending',
        'Fog, multi-stage objects and partial objects excluded'])
    (output/'manifest.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    print(f"{len(counts)} objects; {len(faces)//3} triangles; {len(used)} texture layers -> {output/'menu.ojscene'}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Directory containing scene.obj, scene.json and material PNGs')
    parser.add_argument('camera', type=Path, help='Existing transition preview poses.json')
    parser.add_argument('output', type=Path, help='New local output directory (normally under reports/)')
    args = parser.parse_args()
    convert(args.source, args.camera, args.output)
