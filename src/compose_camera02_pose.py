"""Compose decoded Camera02 deltas with its captured pose (row vectors).

This is a bounded numerical model of the non-hierarchical path in 00648DB0.
It does not implement controller scheduling, quaternion decoding or track 3.
"""
import numpy as np


def compose_pose(captured, translation, rotation):
    """Return a 4x4 row-vector affine pose; rotation is an already decoded delta."""
    captured = np.asarray(captured, dtype=float)
    translation = np.asarray(translation, dtype=float)
    rotation = np.asarray(rotation, dtype=float)
    if captured.shape != (4, 4) or translation.shape != (3,) or rotation.shape != (3, 3):
        raise ValueError('Unexpected pose dimensions')
    if not all(np.isfinite(a).all() for a in (captured, translation, rotation)):
        raise ValueError('Nonfinite pose')
    if not np.allclose(captured[:, 3], [0, 0, 0, 1]):
        raise ValueError('Expected a row-vector affine matrix')
    result = captured.copy()
    result[:3, :3] = rotation @ captured[:3, :3]
    result[3, :3] = translation @ captured[:3, :3] + captured[3, :3]
    return result
