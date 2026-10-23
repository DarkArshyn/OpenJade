"""Decode single-stage color selectors; only constant mode is reconstructed."""
import struct
import numpy as np


def color_state(data):
    if len(data) != 48 or struct.unpack_from('<2I', data) != (5, 6):
        raise ValueError('Unsupported material color layout')
    packed = struct.unpack_from('<I', data, 8)[0]
    flags = struct.unpack_from('<I', data, 28)[0]
    mode = (flags >> 13) & 7
    return dict(mode=mode, flags=f'0x{flags:08X}',
                constant_rgb=[(packed >> shift) & 255 for shift in (0, 8, 16)],
                status='native constant x2' if mode == 2 else 'existing vertex approximation; lighting unresolved')


def apply_material_colors(colors, triangles, groups, states):
    """Assign only verified constant groups; preserve other groups and inputs."""
    if len(groups) != len(states) or sum(count for _, count in groups) != len(triangles):
        raise ValueError('Material group extent mismatch')
    result = np.array(colors, dtype=float, copy=True)
    cursor = 0
    for (_, count), state in zip(groups, states):
        if state['mode'] == 2:
            # Primary mesh corners are expanded, so groups cannot share vertices.
            indices = triangles[cursor:cursor + count].ravel()
            result[indices] = np.array(state['constant_rgb'], dtype=float) * (2 / 255)
        cursor += count
    return result
