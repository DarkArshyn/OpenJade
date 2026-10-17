import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from probe_menu3d import records


class RecordTests(unittest.TestCase):
    def test_empty_payload_and_absolute_offsets(self):
        data=struct.pack('<III',0,0xEEFFC099,1)+struct.pack('<III',7,0xEEFFC099,2)+b'abc.gao'
        r=records(data)
        self.assertEqual(r[1]['names'][0]['offset'],24)
        self.assertEqual(r[1]['end'],len(data))
    def test_truncated_header(self):
        with self.assertRaises(ValueError):records(b'abc')
    def test_truncated_payload(self):
        with self.assertRaises(ValueError):records(struct.pack('<III',100,0xEEFFC099,1))
    def test_wrong_marker(self):
        with self.assertRaises(ValueError):records(struct.pack('<III',0,123,1))


if __name__=='__main__':unittest.main()
