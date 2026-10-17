import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from inspect_camera_cf1_prefix import rotations
class PrefixTests(unittest.TestCase):
 def test_identity_and_signed(self):
  d=struct.pack('<H4hH4h',0,0,0,0,32767,130,-32767,0,0,0)
  r=rotations(d,0,2,20)
  self.assertEqual(r[0]['scaled_components'],[0,0,0,1])
  self.assertEqual(r[1]['scaled_components'],[-1,0,0,0])
  self.assertEqual(r[1]['opaque_leading_word'],130)
 def test_truncation(self):
  with self.assertRaises(ValueError):rotations(bytes(9),0,1,10)
 def test_nonunit(self):
  with self.assertRaises(ValueError):rotations(bytes(10),0,1,10)
if __name__=='__main__':unittest.main()
