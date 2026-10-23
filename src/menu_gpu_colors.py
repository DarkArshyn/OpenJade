"""Observed dynamic-upload color packing, independently expressed."""
import numpy as np


def pack_color(word, or_mask=0, xor_mask=0):
    """Convert a stored low-byte-red word to the observed Direct3D byte order."""
    value = ((int(word) | int(or_mask)) ^ int(xor_mask)) & 0xffffffff
    return ((value & 255) << 16) | ((value >> 16) & 255) | (value & 0xff00ff00)


def direct_tree_colors(colors, instance_flags, states):
    """Bounded tronc4 experiment: direct recorded RGB with texture MODULATE2X."""
    if instance_flags != 0x0D2255FF or [s['material'] for s in states] != ['0x30000C95', '0x30000CA9'] or any(s['mode'] != 0 for s in states):
        raise ValueError('Unsupported tree upload case')
    return np.asarray(colors, dtype=float) * 2
