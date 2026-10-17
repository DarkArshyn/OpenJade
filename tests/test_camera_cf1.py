import math,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from inspect_camera_cf1 import read_samples
class SequenceTests(unittest.TestCase):
 def test_unaligned_records(self):
  d=b'x'+struct.pack('<B3fB3f',4,1,2,3,0,-1,-2,-3)
  r=read_samples(d,1,2,27)
  self.assertEqual(r[1]['payload_offset'],14)
  self.assertEqual(r[1]['triplet'],[-1,-2,-3])
  self.assertEqual(r[0]['leading_byte'],4)
 def test_extents(self):
  for args in [(b'',0,1,13),(bytes(26),0,2,25),(bytes(26),-1,2,25)]:
   with self.assertRaises(ValueError):read_samples(*args)
 def test_nonfinite(self):
  with self.assertRaises(ValueError):read_samples(struct.pack('<B3f',0,math.nan,0,0),0,1,13)
if __name__=='__main__':unittest.main()
