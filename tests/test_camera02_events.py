"""Synthetic boundary and corruption tests for the stripped-PC event track."""
import struct, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from decode_camera02_events import decode_events


def sample():
    d = bytearray(624)
    struct.pack_into('<HHIII', d, 496, 0x14, 0xffff, 104, 0, 2)
    for offset, duration in ((512, 540), (568, 0)):
        struct.pack_into('<HHI', d, offset, duration, 0x41, 6)
        for i in range(6): struct.pack_into('<II', d, offset+8+i*8, i, 0x01000021)
    return d


class EventTests(unittest.TestCase):
    def test_offsets_and_timing(self):
        r=decode_events(sample())
        self.assertEqual([k['start_seconds'] for k in r['keys']], [0,9])
        self.assertEqual(r['keys'][-1]['nodes'][-1]['offset'],616)
        self.assertTrue(r['identical_instructions'])
    def test_preserves_unknown_nodes(self):
        d=sample();struct.pack_into('<I',d,620,0xdeadbeef)
        r=decode_events(d)
        self.assertEqual(r['keys'][1]['nodes'][-1]['tag'],0xdeadbeef)
        self.assertFalse(r['identical_instructions'])
    def test_truncation(self):
        with self.assertRaises(ValueError): decode_events(sample()[:-1])
    def test_header_and_count(self):
        for offset in (496,516):
            d=sample();d[offset]^=1
            with self.assertRaises(ValueError): decode_events(d)


if __name__=='__main__': unittest.main()
