"""Export the verified, ordered hangfire modifiers without altering native assets."""
import hashlib
import struct
import numpy as np
from inspect_menu_palms import HASH
from inspect_menu_scene_links import static_links
from menu_primary_geometry import primary_mesh
from menu_fog_state import transform_fog_points
from probe_menu3d import records


def export_fixtures(source, vertices, draws, audit):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASH:
        raise ValueError('Unsupported fixture source')
    by = {r['key']: raw[r['offset']+12:r['end']] for r in records(raw)}
    controls = {}
    parameters = None
    for key in ('0x30000D53', '0x30000F45'):
        obj = by[key]
        link = static_links(obj)
        mesh = by[link['mesh']]
        _, _, groups, indices, count, _, layout = primary_mesh(mesh)
        if groups != [(0, 56), (1, 2), (2, 2)] or count != 49 or indices[168] != 41:
            raise ValueError('Unsupported fixture geometry')
        chain = [struct.unpack_from('<4I4fI', obj, at) for at in (435, 471)]
        if [c[:4] for c in chain] != [(1, 0, 25, 21), (1, 0, 25, 4)] or any(c[-1] != 0 for c in chain):
            raise ValueError('Unsupported fixture modifier chain')
        params = [v for c in chain for v in (c[5], c[6], c[7], c[4])]
        if parameters is not None and parameters != params:
            raise ValueError('Fixture parameters differ')
        parameters = params
        local = np.frombuffer(mesh, '<f4', count*3, layout['vertex_offset']).reshape(count, 3).astype(float)
        normals = struct.unpack_from('<I', mesh, 40)[0]
        color_start = layout['vertex_offset'] + count*12*(1+normals)
        alpha = np.frombuffer(mesh, 'u1', count*4, color_start).reshape(count, 4)[:, 3]
        matrix = np.frombuffer(obj, '<f4', 16, link['matrix_offset']).astype(float).reshape(4, 4)
        world = transform_fog_points(local, matrix)
        basis = matrix[:3, :3] * matrix[:3, 3, None]
        controls[link['name']] = local, world, alpha, basis
    output = bytearray()
    counts = {name: 0 for name in controls}
    for draw, entry in zip(draws, audit, strict=True):
        if entry['object'] not in controls or entry['material'] != '0x2E00541D':
            continue
        local, world, alpha, basis = controls[entry['object']]
        first, count = draw[:2]
        if count != 168:
            raise ValueError('Unexpected selected fixture draw size')
        for index in range(first, first+count):
            distance = np.max(abs(world - np.asarray(vertices[index][:3])), axis=1)
            matches = np.flatnonzero(distance < 2e-5)
            if len(matches) != 1 or matches[0] >= 41:
                raise ValueError('Ambiguous or excluded fixture vertex')
            vertex = matches[0]
            output.extend(struct.pack('<I13f', index, *local[vertex], float(alpha[vertex])/256, *basis.ravel()))
            counts[entry['object']] += 1
    if set(counts.values()) != {336}:
        raise ValueError('Incomplete fixture passes')
    return b'OJFIX001' + struct.pack('<I8f', sum(counts.values()), *parameters) + output
