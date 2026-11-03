import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from probe_menu_effects import particle_record,inspect
class EffectTests(unittest.TestCase):
    def test_preserves_unknown_data(self):
        d=bytearray(274);struct.pack_into('<4I',d,0,11,23,150,0x08020241);d[-1]=127
        r=particle_record(d)
        self.assertEqual(bytes.fromhex(r['payload_hex']),d)
        self.assertEqual(r['word_08'],150)
    def test_rejects_extent_and_header(self):
        for d in [bytes(273),bytes(275),bytes(274)]:
            with self.assertRaises(ValueError):particle_record(d)
    def test_rejects_unverified_source(self):
        with self.assertRaises(ValueError):inspect(b'unknown')
if __name__=='__main__':unittest.main()
