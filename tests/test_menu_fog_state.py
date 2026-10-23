"""Native-derived fog state and transform regression checks."""
import struct
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from menu_fog_state import fog_state, transform_fog_points, sample_fog


class FogStateTests(unittest.TestCase):
    def test_stage_and_color(self):
        data = bytearray(48)
        struct.pack_into('<3I', data, 0, 5, 6, 0x6668543a)
        struct.pack_into('<I', data, 28, 0x40014205)
        state = fog_state(data)
        self.assertEqual(state['constant_rgb'], [58, 84, 104])
        self.assertEqual(state['rgb_gain'], 2)
        self.assertEqual(state['blend_mode'], 1)
        self.assertFalse(state['alpha_test'])
        self.assertFalse(state['depth_write'])
        self.assertTrue(state['wrap_u'])
        self.assertFalse(state['wrap_v'])
        self.assertTrue(state['dynamic_u'])
        for invalid in (data[:-1], data + b'\0'):
            with self.assertRaises(ValueError): fog_state(invalid)
        struct.pack_into('<I', data, 28, 0x40024205)
        with self.assertRaises(ValueError): fog_state(data)

    def test_local_scale_before_rotation_translation(self):
        matrix = np.array([[0, 1, 0, 2], [-1, 0, 0, 3], [0, 0, 1, .5], [10, 20, 30, 9e33]])
        np.testing.assert_allclose(transform_fog_points(np.array([[1, 2, 4]]), matrix), [[4, 22, 32]])
        matrix[:3, 3] = 0
        np.testing.assert_allclose(transform_fog_points(np.array([[1, 2, 4]]), matrix), [[8, 21, 34]])
        matrix[0, 3] = np.nan
        with self.assertRaises(ValueError): transform_fog_points(np.zeros((1, 3)), matrix)

    def test_linear_wrap_u_clamp_v(self):
        texture = np.array([[[0, 0, 0, 0], [100, 0, 0, 100]],
                            [[0, 100, 0, 200], [100, 100, 0, 240]]], dtype=np.uint8)
        values = sample_fog(texture, np.array([[.5, .5], [.25, -1], [1.25, 2]]))
        np.testing.assert_allclose(values, [[50, 50, 0, 135], [0, 0, 0, 0], [0, 100, 0, 200]])
        np.testing.assert_allclose(sample_fog(texture, np.array([[0., .25]])), [[50, 0, 0, 50]])


if __name__ == '__main__':
    unittest.main()
