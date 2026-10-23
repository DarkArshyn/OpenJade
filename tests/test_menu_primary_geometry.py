import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_primary_geometry import primary_mesh,instance_colors

class PrimaryTests(unittest.TestCase):
 def fixture(self):
  header=struct.pack('<11I',1,7,16,0,3,0,0,3,1,0,0)
  return header+struct.pack('<9f',0,0,0,1,0,0,0,1,0)+struct.pack('<6f',0,0,1,0,0,1)+struct.pack('<2I8H',1,0,0,1,2,2,0,1,0,0)
 def test_separate_uv_indices(self):
  v,t,g,ids,n,c,layout=primary_mesh(self.fixture())
  self.assertEqual(v[:,3:].tolist(),[[0,1],[0,0],[1,0]])
  self.assertEqual(ids.tolist(),[0,1,2]);self.assertEqual(g,[(0,1)])
 def test_truncation_and_bad_indices(self):
  bad=bytearray(self.fixture());struct.pack_into('<H',bad,112,3)
  for d in (self.fixture()[:-1],bad):
   with self.assertRaises(ValueError):primary_mesh(d)
 def test_instance_specific_colors(self):
  a=b'\xff\xff'+struct.pack('<I',1)+bytes([12,34,56,254])+struct.pack('<I',1)
  b=b'\xff\xff'+struct.pack('<I',1)+bytes([90,80,70,254])+struct.pack('<I',1)
  ca,off=instance_colors(a,0,1);cb,_=instance_colors(b,0,1)
  self.assertEqual(off,6);self.assertNotEqual(ca.tolist(),cb.tolist())
  self.assertEqual(instance_colors(a[:-1],0,1),(None,None))
if __name__=='__main__':unittest.main()
