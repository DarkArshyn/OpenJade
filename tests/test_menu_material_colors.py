"""Per-group color dispatch regressions for expanded primary geometry."""
import struct
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from menu_material_colors import color_state, apply_material_colors


class MaterialColorTests(unittest.TestCase):
    def test_version_and_selector(self):
        data = bytearray(48)
        struct.pack_into('<3I', data, 0, 5, 6, 0x66736247)
        struct.pack_into('<I', data, 28, 0x14017)
        state = color_state(data)
        self.assertEqual(state['mode'], 2)
        self.assertEqual(state['constant_rgb'], [71, 98, 115])
        for invalid in (data[:-1], data + b'\0'):
            with self.assertRaises(ValueError): color_state(invalid)
        struct.pack_into('<I', data, 4, 4)
        with self.assertRaises(ValueError): color_state(data)

    def test_mixed_groups_do_not_bleed(self):
        colors = np.full((6, 3), .1)
        triangles = np.arange(6).reshape(2, 3)
        states = [dict(mode=0), dict(mode=2, constant_rgb=[64, 128, 255])]
        result = apply_material_colors(colors, triangles, [(0, 1), (1, 1)], states)
        np.testing.assert_array_equal(result[:3], colors[:3])
        np.testing.assert_allclose(result[3:], np.tile(np.array([64, 128, 255])*2/255, (3, 1)))
        np.testing.assert_array_equal(colors, np.full((6, 3), .1))
        # Values above one remain until texture modulation and final saturation.
        self.assertEqual(result[3, 2], 2)

    def test_unresolved_mode_and_extent(self):
        colors = np.full((3, 3), .25)
        triangles = np.array([[0, 1, 2]])
        np.testing.assert_array_equal(apply_material_colors(colors, triangles, [(0, 1)], [dict(mode=3)]), colors)
        with self.assertRaises(ValueError): apply_material_colors(colors, triangles, [(0, 2)], [dict(mode=2)])


if __name__ == '__main__': unittest.main()
