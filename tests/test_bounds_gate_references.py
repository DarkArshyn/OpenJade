import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from inspect_bounds_gate_references import find_hits, IDENTIFIER


def record(key, payload):
    return struct.pack('<III', len(payload), 0xEEFFC099, key) + payload


class GateReferenceTests(unittest.TestCase):
    def test_header_is_not_a_payload_match(self):
        needle = struct.pack('<I', IDENTIFIER)
        data = record(IDENTIFIER, b'x'+needle+needle)
        self.assertEqual([r['payload_offset'] for r in find_hits(data)], [1, 5])
        self.assertEqual([r['absolute_offset'] for r in find_hits(data)], [13, 17])

    def test_truncated_record_rejected(self):
        with self.assertRaises(ValueError):
            find_hits(record(1, b'abcd')[:-1])


if __name__ == '__main__':
    unittest.main()
