"""Synthetic palm suffix guards; no original game content."""
import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from inspect_menu_palms import suffix_candidate,inspect,decode_compact_palm

class PalmTests(unittest.TestCase):
    def test_offsets_and_signed_float_candidates(self):
        data=b'prefix'+struct.pack('<5I3f2I',1,0,25,7,0,.15,1.,-.05,0xffffffff,0xffffffff)
        result=suffix_candidate(data)
        self.assertEqual(result['payload_offset'],6)
        self.assertAlmostEqual(result['float_candidates'][2],-.05)
    def test_rejects_different_suffix_and_truncation(self):
        data=struct.pack('<5I3f2I',1,0,25,15,0,.1,1.,.05,0xffffffff,0xffffffff)
        self.assertIsNotNone(suffix_candidate(data))
        for bad in (data[:-1],data+b'X',bytes(40),b''):
            self.assertIsNone(suffix_candidate(bad))
    def test_compact_cursor_and_type(self):
        prefix=struct.pack('<6I',1,0xffffffff,0x30000CE4,0x30000CE9,0,0xffffffff)
        meta=struct.pack('<I',1)+bytes(14)
        block=struct.pack('<4I4f2I',1,0,25,7,0,.1,1.,-.05,0xffffffff,0xffffffff)
        data=b'colors'+prefix+meta+block
        result=decode_compact_palm(data,6)
        self.assertEqual((result['payload_offset'],result['type'],result['version']),(48,1,25))
        self.assertAlmostEqual(result['phase_rate_factor'],-.05)
        for bad in (data[:-1],data+b'X',data[:48]+struct.pack('<I',25)+data[52:]):
            with self.assertRaises(ValueError):decode_compact_palm(bad,6)
        bad=bytearray(data);struct.pack_into('<f',bad,48+20,float('nan'))
        with self.assertRaises(ValueError):decode_compact_palm(bad,6)

    def test_rejects_other_scene(self):
        with self.assertRaises(ValueError):inspect(b'other')

if __name__=='__main__':unittest.main()
