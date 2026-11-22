"""Prepare the verified fixed-menu light terms from original scene resources.

The generated camera-dependent direction remains capture-derived. This is not a
general runtime light graph or automatic light selection.
"""
import struct
import numpy as np

LIGHTS = ((0x30000CE2, 0x30000CE6), (0x30000CF4, 0x30000D55),
          (0x30000D57, 0x30000D58), (0x30000CE4, 0x30000CE8))


def decode(resources):
    result = []
    for key, descriptor in LIGHTS:
        raw = resources.get(key)
        if len(raw) < 20 or raw[:4] != b'.gao':
            raise ValueError('Invalid light object')
        version, _, _, length = struct.unpack_from('<4I', raw, 4)
        if version != 10 or not 1 <= length <= 200 or len(raw) != length + 148:
            raise ValueError('Unsupported light object layout')
        if raw[20+length-1] != 0 or struct.unpack_from('<I', raw, len(raw)-4)[0] != descriptor:
            raise ValueError('Invalid light descriptor link')
        matrix = np.array(struct.unpack_from('<16f', raw, length+30)).reshape(4, 4)
        data = resources.get(descriptor)
        if len(data) != 36 or struct.unpack_from('<2I', data) != (2, 9):
            raise ValueError('Unsupported light descriptor')
        packed = struct.unpack_from('<I', data, 12)[0]
        inner, outer = struct.unpack_from('<2f', data, 16)
        if not np.isfinite(matrix).all() or not np.allclose(matrix[:, 3], [0, 0, 0, 1]):
            raise ValueError('Invalid light transform')
        if not np.isfinite([inner, outer]).all() or not 0 <= inner < outer:
            raise ValueError('Invalid light ranges')
        result.append(dict(key=f'{key:08X}', descriptor=f'{descriptor:08X}',
                           name=raw[20:19+length].decode('ascii'), matrix=matrix,
                           color=np.array([(packed >> s & 255)/255 for s in (0, 8, 16)]),
                           outer=outer, inverse_width=1/(outer-inner)))
    return result


def parameters(resources, placement, captured):
    placement = np.asarray(placement, dtype=float)
    values = np.asarray(captured, dtype=float).copy()
    if placement.shape != (4, 4) or values.shape != (31,) or not np.isfinite(values).all():
        raise ValueError('Invalid lighting inputs')
    if not np.isfinite(placement).all() or not np.allclose(placement[:, 3], [0, 0, 0, 1]):
        raise ValueError('Invalid actor placement')
    if not np.allclose(placement[:3, :3] @ placement[:3, :3].T, np.eye(3), atol=1e-6):
        raise ValueError('Non-rigid actor placement')
    inverse = np.linalg.inv(placement)
    moon, room, fire, ambient = decode(resources)
    values[:3] = ambient['color']
    direction = moon['matrix'][1, :3] @ inverse[:3, :3]
    if np.linalg.norm(direction) < 1e-8:
        raise ValueError('Invalid moon direction')
    values[3:6] = direction / np.linalg.norm(direction)
    values[6:9] = moon['color']
    # Slots 9..14 are the generated native direction and color, not scene data.
    for light, offset in ((room, 15), (fire, 23)):
        values[offset:offset+3] = (light['matrix'][3] @ inverse)[:3]
        values[offset+3:offset+6] = light['color']
        values[offset+6:offset+8] = light['outer'], light['inverse_width']
    return values
