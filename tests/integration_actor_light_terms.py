"""Validate captured ambient and generated directional terms against native outputs."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np


def unpack(path, layout):
    data = path.read_bytes()
    assert data and len(data) % struct.calcsize(layout) == 0, path
    return list(struct.iter_unpack(layout, data))


def verify(captures):
    prefix = captures.name
    assert prefix == 'light-terms3', 'Expected the complete source-pointer capture'
    direction = unpack(captures/f'{prefix}-direction.bin', '<3I8f')
    transfer = unpack(captures/f'{prefix}-transfer.bin', '<2I35f')
    ambient = unpack(captures/f'{prefix}-ambient.bin', '<10I')
    registry = unpack(captures/f'{prefix}-registry.bin', '<5I')
    assert len(direction) == len(transfer) == len(ambient) == 121
    assert len({row[1] for row in direction}) == 11
    assert sorted({row[0] for row in direction}) == list(range(0, 121, 12))
    assert len({row[:2] for row in direction}) == 121
    assert [row[:2] for row in direction] == [row[:2] for row in transfer] == [row[:2] for row in ambient]
    mesh_keys = set()
    for pointer in {row[1] for row in direction}:
        text = (captures/f'{prefix}-object-{pointer:08x}.txt').read_text()
        mesh_pointer = int(next(line.split()[1] for line in text.splitlines() if line.startswith('mesh ')), 16)
        keys = {key for key, _, callback, _, value in registry if value == mesh_pointer and callback == 0x43f120}
        assert len(keys) == 1
        mesh_keys.update(keys)
    assert mesh_keys == {0x33001050, 0x057cc7f4, 0x3f000e05, 0x13008483, 0x13008426,
                         0x13008425, 0x1300842c, 0x13008427, 0x1300842a, 0x13008428, 0x1300842b}
    functions = {0x729630: math.atan, 0x729404: math.cos, 0x7294b4: math.sin, 0x729764: math.sqrt}
    math_rows = unpack(captures/f'{prefix}-math.bin', '<Idd')
    assert len(math_rows) == 16
    assert {(address, value) for address, value, _ in math_rows} == {(address, value) for address in functions for value in (0., .25, .5, 1.)}
    math_error = max(abs(output-functions[address](value)) for address, value, output in math_rows)
    assert math_error < 1e-14
    raw = (captures/f'{prefix}-draws.bin').read_bytes()
    stride = 5*4+256*16
    assert len(raw) % stride == 0
    draws = {}
    for offset in range(0, len(raw), stride):
        header = struct.unpack_from('<5I', raw, offset)
        constants = np.frombuffer(raw, '<f4', 1024, offset+20).reshape(256, 4)
        draws.setdefault(header[:2], []).append((header, constants))
    assert set(draws) == {row[:2] for row in direction}
    errors = dict(direction=0., local_transform=0., gpu_direction=0., ambient=0.)
    output_rows = []
    for native, matrices, cache in zip(direction, transfer, ambient):
        frame, receiver, packed, x, y, z, dx, dy, dz, azimuth_offset, polar = native
        assert packed == 0x40404040
        assert abs(azimuth_offset-math.pi) < 1e-7 and abs(polar-.3) < 2e-8
        # This closed form tests the measured default positive polar angle.
        # The native sequence uses intermediate float stores; this is not bit-exact emulation.
        azimuth = math.atan(y/(x if x else 1e-7)) + (math.pi if x < 0 else 0) + azimuth_offset
        expected = np.array([math.sin(polar)*math.cos(azimuth), math.sin(polar)*math.sin(azimuth), math.cos(polar)])
        world = np.array([dx, dy, dz])
        errors['direction'] = max(errors['direction'], float(np.max(np.abs(world-expected))))
        local = np.array(matrices[2:5])
        inverse = np.array(matrices[5:21]).reshape(4, 4)
        gpu_matrix = np.array(matrices[21:37]).reshape(4, 4)
        errors['local_transform'] = max(errors['local_transform'], float(np.max(np.abs(world@inverse[:3, :3]-local))))
        gpu = local@gpu_matrix[:3, :3]
        gpu /= np.linalg.norm(gpu)
        assert cache[3] == cache[4] == 0xff3b2e25 and cache[5] & 2
        # The direct source pointer is null: matching a scene color is not a causal binding.
        assert cache[6:9] == (0, 0, 0)
        for header, constants in draws[(frame, receiver)]:
            assert header[4] == cache[4]
            errors['ambient'] = max(errors['ambient'], float(np.max(np.abs(constants[25]-[37/255, 46/255, 59/255, 1]))))
            errors['gpu_direction'] = max(errors['gpu_direction'], float(np.max(np.abs(constants[39, :3]-gpu))))
            assert constants[39, 3] == 0
            assert np.allclose(constants[40], [64/255, 64/255, 64/255, 1], rtol=0, atol=1e-7)
        output_rows.append(dict(frame=frame, receiver=f'0x{receiver:08X}', world_direction=world.tolist(), gpu_direction=gpu.tolist()))
    assert errors['direction'] < 3e-7
    assert errors['local_transform'] < 1e-7
    assert errors['gpu_direction'] < 2e-7
    assert errors['ambient'] < 1e-7
    evidence = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(captures.glob(f'{prefix}-*.bin'))}
    return dict(samples=len(direction), components=11, draws=sum(map(len, draws.values())),
                math_samples=len(math_rows), math_max_error=math_error, max_errors=errors,
                owner_cached_color_nonzero=sum(row[9] != 0 for row in ambient),
                direct_ambient_sources=0, evidence_sha256=evidence, samples_detail=output_rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path)
    print(json.dumps(verify(parser.parse_args().captures), indent=2))
