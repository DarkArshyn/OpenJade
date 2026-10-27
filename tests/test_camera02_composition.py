"""Synthetic checks of the native Camera02 composition convention."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from compose_camera02_pose import compose_pose


class CompositionTests(unittest.TestCase):
    def test_zero_delta_preserves_capture(self):
        m = np.eye(4); m[3, :3] = [10, 20, 30]
        np.testing.assert_array_equal(compose_pose(m, [0, 0, 0], np.eye(3)), m)

    def test_translation_uses_captured_axes(self):
        m = np.eye(4); m[:3, :3] = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
        m[3, :3] = [10, 20, 30]
        np.testing.assert_array_equal(compose_pose(m, [2, 0, 0], np.eye(3))[3, :3], [10, 22, 30])

    def test_rotation_order_and_position_independence(self):
        m = np.eye(4); m[:3, :3] = [[0, 1, 0], [-1, 0, 0], [0, 0, 1]]
        delta = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]])
        got = compose_pose(m, [2, 0, 0], delta)
        np.testing.assert_array_equal(got[:3, :3], [[0, 1, 0], [0, 0, 1], [1, 0, 0]])
        np.testing.assert_array_equal(got[3, :3], [0, 2, 0])

    def test_rejects_invalid_inputs(self):
        for t in ([0, 0], [0, float('nan'), 0]):
            with self.assertRaises(ValueError): compose_pose(np.eye(4), t, np.eye(3))


if __name__ == '__main__': unittest.main()
