"""Synthetic compact-descriptor boundary and field checks."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from inspect_camera_function_descriptors import parse_table

class DescriptorTests(unittest.TestCase):
    def test_fields_and_duplicate_ids_preserved(self):
        row = struct.pack('<22I', 614, 0x5b82, 0x263c, 0x5d, 1, 0x25, 0x25, *([0]*15))
        rows = parse_table(struct.pack('<I', 2)+row+row)
        self.assertEqual([r['payload_offset'] for r in rows], [4, 92])
        self.assertEqual(rows[0]['parameter_types'], [0x25])
        self.assertEqual(rows[1]['identifier'], 0x5b82)
    def test_extent(self):
        for data in [b'', b'\x01\0\0\0', struct.pack('<I',1)+bytes(100)]:
            with self.assertRaises(ValueError): parse_table(data)
        self.assertEqual(parse_table(bytes(4)), [])
    def test_parameter_bound(self):
        row=struct.pack('<22I',0,1,2,3,17,*([0]*17))
        with self.assertRaises(ValueError): parse_table(struct.pack('<I',1)+row)

if __name__ == '__main__': unittest.main()
