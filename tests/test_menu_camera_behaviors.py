"""Synthetic checks for ambiguity and binding-column interpretation."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from link_menu_camera_behaviors import binding, unique_record


class CameraBehaviorTests(unittest.TestCase):
    def test_key_precedes_pointer(self):
        table = struct.pack('<4I', 0x3200043d, 0x51dfa0, 0x3200043e, 0x5e3240)
        self.assertEqual(binding(table, 0x3200043d)['pointer'], '0x0051DFA0')
        with self.assertRaises(ValueError):
            binding(table, 0x51dfa0)

    def test_duplicate_or_truncated_binding_is_rejected(self):
        row = struct.pack('<II', 3, 4)
        for table in (row + row, row[:-1]):
            with self.assertRaises(ValueError):
                binding(table, 3)

    def test_duplicate_record_is_not_silently_selected(self):
        row = dict(key='0x00000003', offset=0, end=12)
        with self.assertRaises(ValueError):
            unique_record(bytes(12), [row, row], 3)


if __name__ == '__main__':
    unittest.main()
