"""Regression checks for packed fog UV rates and deterministic time samples."""
import struct
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from menu_fog_state import fog_uv_motion, animate_fog_uv, sample_fog


class FogMotionTests(unittest.TestCase):
    def motion(self):
        data = bytearray(48)
        struct.pack_into('<2I', data, 0, 5, 6)
        struct.pack_into('<4I', data, 28, 0x40014205, 0x3f803da2, 0x3f800000, 0x80000000)
        return data

    def test_packed_rate(self):
        data = self.motion()
        state = fog_uv_motion(data)
        self.assertEqual(state['rate_u'], .0791015625)
        self.assertEqual(state['scale'], [1, 1])
        self.assertEqual(state['rate_v'], 0)
        data[32] ^= 1
        with self.assertRaises(ValueError): fog_uv_motion(data)

    def test_time_samples_and_input_preservation(self):
        state = fog_uv_motion(self.motion())
        uv = np.array([[0., .2], [1., .8]])
        np.testing.assert_array_equal(animate_fog_uv(uv, state, 0), uv)
        result = animate_fog_uv(uv, state, 4)
        np.testing.assert_allclose(result, [[.31640625, .2], [1.31640625, .8]])
        np.testing.assert_array_equal(uv, [[0, .2], [1, .8]])
        for invalid in (-1, np.inf, np.nan):
            with self.assertRaises(ValueError): animate_fog_uv(uv, state, invalid)

    def test_repeat_period_and_visible_shift(self):
        state = fog_uv_motion(self.motion())
        uv = np.array([[.25, .5]])
        texture = np.array([[[0, 0, 0, 0], [255, 255, 255, 255]]], dtype=np.uint8)
        start = sample_fog(texture, animate_fog_uv(uv, state, 0))
        end = sample_fog(texture, animate_fog_uv(uv, state, 1 / state['rate_u']))
        np.testing.assert_allclose(start, end)
        self.assertFalse(np.array_equal(start, sample_fog(texture, animate_fog_uv(uv, state, 4))))


if __name__ == '__main__': unittest.main()
