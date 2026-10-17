import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from inspect_camera_controllers import parse_block

def sample():
    return struct.pack('<2I6II2IIIf',0,24,0,1,40,4,1,34,99,0x1234,0x5678,8,0x30000D63,1.3)+bytes(20)

class ControllerTests(unittest.TestCase):
    def test_fields(self):
        b=parse_block(sample())
        self.assertEqual(b['values_start'],48)
        self.assertEqual(b['fields'][0]['uint32'],0x30000D63)
        self.assertEqual(b['fields'][1]['identifier'],'0x00005678')
        self.assertAlmostEqual(b['fields'][1]['float32'],1.3,places=6)
        self.assertEqual(b['trailing_hex'],'00'*20)
    def test_truncated(self):
        for size in [0,7,30,47,50]:
            with self.assertRaises(ValueError):parse_block(sample()[:size])
    def test_bad_extent(self):
        d=bytearray(sample());struct.pack_into('<I',d,20,9)
        with self.assertRaises(ValueError):parse_block(d)

if __name__=='__main__':unittest.main()
