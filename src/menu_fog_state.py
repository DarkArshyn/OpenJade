"""Bounded fog-state decoding supported by the frozen TSoT native analysis."""
import struct
import numpy as np


def fog_uv_motion(data):
    """Decode the verified stage's packed scale/rate words without numeric casts."""
    fog_state(data)
    u, v, rotation = struct.unpack_from('<3I', data, 32)
    if (u, v, rotation) != (0x3F803DA2, 0x3F800000, 0x80000000):
        raise ValueError('Unverified fog UV layout')
    as_float = lambda bits: struct.unpack('<f', struct.pack('<I', bits))[0]
    scale = [as_float(word & 0xFFFE0000) for word in (u, v)]
    return dict(scale=scale, rate_u=as_float((u << 16) & 0xFFFFFFFF) * scale[0],
                rate_v=0.0, phase_origin=0.0, time_unit='effective engine seconds')


def animate_fog_uv(uv, motion, time):
    """Sample forward effective time; do not emulate frame counters or rewind."""
    if not np.isfinite(time) or time < 0:
        raise ValueError('Fog time must be finite and nonnegative')
    result = np.asarray(uv, dtype=float) * motion['scale']
    result[..., 0] += (motion['phase_origin'] + motion['rate_u'] * time) % 1
    return result


def fog_state(data):
    if len(data) != 48 or struct.unpack_from('<2I', data) != (5, 6):
        raise ValueError('Unsupported single-stage material')
    flags = struct.unpack_from('<I', data, 28)[0]
    # Keep this implementation restricted to the verified fog state combination.
    if flags != 0x40014205:
        raise ValueError('Unverified fog stage flags')
    color = struct.unpack_from('<I', data, 8)[0]
    return dict(flags=f'0x{flags:08X}', constant_rgb=[(color >> shift) & 255 for shift in (0, 8, 16)],
                rgb_gain=2, blend_mode=(flags >> 16) & 15,
                source_factor='SRCALPHA', destination_factor='INVSRCALPHA',
                alpha_test=bool(flags & 0x10), depth_write=not bool(flags & 0x200),
                wrap_u=bool(flags & 1), wrap_v=bool(flags & 2),
                linear=bool(flags & 4), color_mode=(flags >> 13) & 7,
                dynamic_u=bool(flags & 0x40000000))


def transform_fog_points(vertices, matrix):
    """Apply local-axis scale, row-basis rotation and existing translation."""
    matrix = np.asarray(matrix)
    scale = matrix[:3, 3]
    if not np.isfinite(matrix[:, :3]).all() or not np.isfinite(scale).all():
        raise ValueError('Nonfinite fog transform')
    # The native loader clears scale when the entire triplet is zero or one.
    if np.allclose(scale, 0, rtol=0, atol=1e-4) or np.allclose(scale, 1, rtol=0, atol=1e-4):
        scale = np.ones(3)
    return (vertices * scale) @ matrix[:3, :3] + matrix[3, :3]


def sample_fog(texture, uv):
    """Bilinear base-level sampling, wrapping U and clamping V at texel edges."""
    height, width = texture.shape[:2]
    x = (uv[..., 0] % 1) * width - .5
    y = np.clip(uv[..., 1] * height - .5, 0, height - 1)
    ix = np.floor(x).astype(int)
    iy = np.floor(y).astype(int)
    fx = (x - ix)[..., None]
    fy = (y - iy)[..., None]
    a = texture[iy, ix % width].astype(float)
    b = texture[iy, (ix + 1) % width].astype(float)
    c = texture[np.minimum(iy + 1, height - 1), ix % width].astype(float)
    d = texture[np.minimum(iy + 1, height - 1), (ix + 1) % width].astype(float)
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy
