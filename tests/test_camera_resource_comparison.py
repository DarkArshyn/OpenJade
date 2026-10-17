import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from compare_camera_resources import inspect
class Sample:
 def __init__(self,data):self.data=data
 def read_bytes(self):return self.data
 def resolve(self):return 'synthetic-memory-input'
class AuditTests(unittest.TestCase):
 def test_duplicate_keys_preserved(self):
  result=inspect(Sample(struct.pack('<3I',0,0xEEFFC099,123)*2))
  self.assertEqual(result['record_count'],2)
  self.assertEqual(result['duplicate_keys'],{'0x0000007B':2})
 def test_truncated_record_rejected(self):
  with self.assertRaises(ValueError):inspect(Sample(struct.pack('<3I',4,0xEEFFC099,123)))
if __name__=='__main__':unittest.main()
