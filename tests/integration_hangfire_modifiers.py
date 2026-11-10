"""Replay the two hangfire modifiers from local native observations (read-only)."""
import argparse
import hashlib
from pathlib import Path
import struct
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from probe_menu3d import records
from inspect_menu_scene_links import static_links
from menu_primary_geometry import primary_mesh


def wave(angle, shift=0):
    index = (np.rint(np.asarray(angle) * float(np.float32(1024 / (2*np.pi)))).astype('i8') + shift) % 1024
    return np.sin(index * float(np.float32(2*np.pi / 1024))).astype('f4')


def verify(capture, source):
    raw = source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == '96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'
    by = {r['key']: raw[r['offset']+12:r['end']] for r in records(raw)}
    obj = by['0x30000D53']
    link = static_links(obj)
    mesh = by[link['mesh']]
    _, _, groups, indices, count, _, meta = primary_mesh(mesh)
    assert groups == [(0, 56), (1, 2), (2, 2)] and count == 49
    assert indices[0] == 0 and indices[168] == 41
    first = struct.unpack_from('<4I4fI', obj, 435)
    second = struct.unpack_from('<4I4fI', obj, 471)
    assert first[:4] == (1, 0, 25, 21) and second[:4] == (1, 0, 25, 4)
    assert first[-1] == second[-1] == 0
    assert obj[435:] == by['0x30000F45'][435:]
    base = np.frombuffer(mesh, '<f4', count*3, meta['vertex_offset']).reshape(count, 3)
    # Modifier weights belong to the primary mesh, not the GAO instance colors.
    assert struct.unpack_from('<I', mesh, 24)[0] == 1
    normals = struct.unpack_from('<I', mesh, 40)[0]
    color_start = meta['vertex_offset'] + count*12*(1+normals)
    mesh_colors = np.frombuffer(mesh, 'u1', count*4, color_start).reshape(count, 4)
    alpha = mesh_colors[:, 3]
    assert color_start == 632
    data = capture.read_bytes()
    size = 16 + count*16
    assert data and len(data) % size == 0, 'Missing or truncated capture'
    previous = None
    errors = {21: [], 4: []}
    for offset in range(0, len(data), size):
        frame, flags, phase, n = struct.unpack_from('<IIfI', data, offset)
        assert n == count and flags in errors and np.isfinite(phase)
        runtime_colors = np.frombuffer(data, 'u1', count*4, offset+16).reshape(count, 4)
        assert np.array_equal(runtime_colors, mesh_colors), 'Mesh colors changed at runtime'
        actual = np.frombuffer(data, '<f4', count*3, offset+16+count*4).reshape(count, 3)
        if flags == 21:
            predicted = base.copy()
            angle = first[6]*predicted[:41, 0]+phase
            amplitude = alpha[:41].astype(float)*first[5]/256
            predicted[:41, 1] += amplitude*wave(angle)
            predicted[:41, 2] += amplitude*wave(angle, 256)
        else:
            assert previous is not None and previous[0] == frame and previous[1] == 21
            predicted = previous[2].copy()
            angle = second[6]*predicted[:41, 2]+phase
            predicted[:41, 0] += second[5]*wave(angle)
            predicted[:41, 1] += second[5]*wave(angle, 256)
        error = float(abs(predicted-actual).max())
        assert error < 1e-6, (frame, flags, error)
        assert np.array_equal(actual[41:], base[41:]), 'Excluded groups moved'
        errors[flags].append(error)
        previous = frame, flags, predicted
    assert len(errors[21]) == len(errors[4]) and len(errors[21]) >= 60
    print(f'Exact stored/runtime match: {len(data)//size} buffers of {count} RGBA words')
    print({flag: {'observations': len(values), 'max_error': max(values)} for flag, values in errors.items()})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path)
    parser.add_argument('menu', type=Path)
    args = parser.parse_args()
    verify(args.capture, args.menu)
