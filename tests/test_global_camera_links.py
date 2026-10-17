import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from inspect_global_camera_links import field_table,extract_value
class FieldTests(unittest.TestCase):
 def sample(self):return struct.pack('<10If',812,12,0,1,0x80022,7,123,4,0,0,1.)[:32]+struct.pack('<f',.5)
 def test_flags_and_nonzero_header(self):
  d=struct.pack('<8If',812,12,0,1,0x80022,7,123,4,.5)
  t=field_table(d);self.assertEqual(t['opaque_first_word'],812)
  self.assertEqual(extract_value(d,t,t['fields'][0])['floats'],[.5])
 def test_truncation(self):
  with self.assertRaises(ValueError):field_table(bytes(7))
 def test_value_overrun(self):
  d=struct.pack('<8If',812,12,0,1,0x25,7,123,4,.5);t=field_table(d)
  with self.assertRaises(ValueError):extract_value(d,t,t['fields'][0])
if __name__=='__main__':unittest.main()
