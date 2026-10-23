"""Synthetic instance descriptor checks; no game assets are required."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from audit_menu_scene import instance_lighting


class InstanceLightingTests(unittest.TestCase):
    def descriptor(self, flags=0x0D2255FF, count=2):
        data = bytearray(22 + count * 4)
        struct.pack_into('<I', data, 8, flags)
        struct.pack_into('<I', data, 18, count)
        return data

    def test_direct_branch_and_offset(self):
        data = self.descriptor()
        result = instance_lighting(b'prefix' + data, 6, 2)
        self.assertTrue(result['direct_recorded_colors'])
        self.assertEqual(result['flags'], '0x0D2255FF')
        self.assertEqual(result['color_count'], 2)

    def test_no_direct_branch(self):
        self.assertFalse(instance_lighting(self.descriptor(0), 0, 2)['direct_recorded_colors'])
        self.assertFalse(instance_lighting(self.descriptor(count=0), 0, 0)['direct_recorded_colors'])

    def test_bad_extents(self):
        for data, offset, count in [(b'', 0, 2), (self.descriptor(), -1, 2),
                                    (self.descriptor()[:-1], 0, 2), (self.descriptor(), 0, 3)]:
            with self.assertRaises(ValueError):
                instance_lighting(data, offset, count)


if __name__ == '__main__':
    unittest.main()
