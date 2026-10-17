import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from prepare_camera_native_followup import pe_sections
class PETests(unittest.TestCase):
 def fixture(self):
  d=bytearray(512);d[:2]=b'MZ';struct.pack_into('<I',d,60,64);d[64:68]=b'PE\0\0'
  struct.pack_into('<HH',d,68,0x14c,1);struct.pack_into('<H',d,84,32);struct.pack_into('<H',d,88,0x10b);struct.pack_into('<I',d,116,0x400000)
  d[120:128]=b'.text\0\0\0';struct.pack_into('<4I',d,128,16,0x1000,16,256);struct.pack_into('<I',d,156,0x20000000)
  return d
 def test_sections(self):
  base,sections=pe_sections(self.fixture());self.assertEqual(base,0x400000);self.assertTrue(sections[0]['executable']);self.assertEqual(sections[0]['offset'],256)
 def test_bad_inputs(self):
  with self.assertRaises(ValueError):pe_sections(b'MZ')
  d=self.fixture();struct.pack_into('<I',d,140,510)
  with self.assertRaises(ValueError):pe_sections(d)
if __name__=='__main__':unittest.main()
