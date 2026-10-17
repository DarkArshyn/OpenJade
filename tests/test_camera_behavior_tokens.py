import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from inspect_camera_behavior_tokens import tokens,common_run
class TokenTests(unittest.TestCase):
 def test_extent_and_tail(self):
  r=tokens(struct.pack('<4I',12,8,1720,0x14000025)+b'end')
  self.assertEqual(r['tokens'][0]['category'],20)
  self.assertEqual(r['tokens'][0]['low24'],37)
  self.assertEqual(r['trailing_hex'],'656e64')
 def test_bad_extent(self):
  for d in [b'',struct.pack('<II',0,7),struct.pack('<II',0,16)]:
   with self.assertRaises(ValueError):tokens(d)
 def test_common_run(self):
  a=tokens(struct.pack('<8I',0,24,1,2,3,4,5,6))['tokens']
  self.assertEqual(common_run(a,a,1,1)['token_count'],3)
  b=[dict(t) for t in a];b[0]['operand']=99
  self.assertEqual(common_run(a,b,1,1)['token_count'],2)
if __name__=='__main__':unittest.main()
