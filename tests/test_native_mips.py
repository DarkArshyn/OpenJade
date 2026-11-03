"""Synthetic native texture tests; no game resources are included."""
import hashlib
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from export_leaf import export_trunk

class NativeMipTests(unittest.TestCase):
    def test_full_record_and_all_six_levels(self):
        # Identical key in a short metadata record and a complete texture record.
        data = bytes(60) + bytes(sum(s*s//2 for s in (256,128,64,32,16,8)))
        raw = bytes(84) + data
        records = [dict(key="0x30000C5C", offset=0, end=72, size=60),
                   dict(key="0x30000C5C", offset=72, end=len(raw), size=len(data))]
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"synthetic.bin"
            source.write_bytes(raw)
            with patch("export_leaf.HASH", hashlib.sha256(raw).hexdigest()), patch("export_leaf.records", return_value=records):
                base = bytes([0,0,0,255]) * (256*256)
                result = export_trunk(source, 3, base)
                self.assertEqual(result[:16], b"OJTRNK01" + struct.pack("<II",3,6))
                self.assertEqual(len(result), 349456)
                self.assertEqual(result[16:], bytes([0,0,0,255])*87360)
                with self.assertRaisesRegex(ValueError, "base does not match"):
                    export_trunk(source, 3, bytes(len(base)))

if __name__ == "__main__": unittest.main()
