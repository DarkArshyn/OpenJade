import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from inspect_balcony_bounds import value
class BoundsTests(unittest.TestCase):
    def test_flagged_vector(self):
        d=struct.pack('<3f',1,-2,3)
        self.assertEqual(value(d,dict(values_start=0,values_length=12),dict(offset=0,count=1,tag=0x90025))['value'],[1,-2,3])
    def test_overrun_and_array(self):
        for offset,count in [(1,1),(0,2)]:
            with self.assertRaises(ValueError):value(bytes(12),dict(values_start=0,values_length=12),dict(offset=offset,count=count,tag=0x25))
if __name__=='__main__':unittest.main()
