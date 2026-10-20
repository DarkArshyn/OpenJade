import struct
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from inspect_balcony_geometry import inspect_payload


class GeometryTests(unittest.TestCase):
    def fixture(self):
        name = b'test.gao\0'
        data = bytearray(len(name)+148)
        data[:16] = bytes.fromhex('2e67616f0a0000000800000020a00000')
        struct.pack_into('<I', data, 16, len(name))
        data[20:20+len(name)] = name
        struct.pack_into('<6f', data, 98+len(name), -3, -2, -1, 4, 5, 6)
        return data

    def test_bounds_are_not_tail_or_matrix(self):
        result = inspect_payload(self.fixture())
        self.assertEqual(result['lower'], [-3, -2, -1])
        self.assertEqual(result['upper'], [4, 5, 6])
        self.assertEqual(result['bounds_offset'], 107)
        self.assertEqual(len(bytes.fromhex(result['tail_raw_hex'])), 26)

    def test_rejects_other_layouts(self):
        data = self.fixture()
        bad = bytearray(data)
        bad[12] ^= 1
        for candidate in (data[:-1], data+b'\0', bad):
            with self.assertRaises(ValueError):
                inspect_payload(candidate)

    def test_rejects_invalid_limits(self):
        for value in (float('nan'), 7):
            data = self.fixture()
            struct.pack_into('<f', data, 107, value)
            with self.assertRaises(ValueError):
                inspect_payload(data)


if __name__ == '__main__':
    unittest.main()
