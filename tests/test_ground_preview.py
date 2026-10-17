import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from preview_menu3d_ground import ground


def fixture():
    b=bytearray(280)
    for i,v in enumerate([(0,0,0),(1,0,0),(0,1,0),(1,1,0)]):
        struct.pack_into('<3f',b,44+12*i,*v);struct.pack_into('<3f',b,184+20*i,*v)
    struct.pack_into('<II',b,176,4,20);struct.pack_into('<I6H',b,264,12,2,0,3,1,3,0)
    return b


class Tests(unittest.TestCase):
    def test_area(self):self.assertEqual(ground(fixture())['rectangle_xy_area'],1)
    def test_bad_index(self):
        b=fixture();struct.pack_into('<H',b,268,4)
        with self.assertRaises(ValueError):ground(b)
    def test_mismatched_arrays(self):
        b=fixture();struct.pack_into('<f',b,184,3)
        with self.assertRaises(ValueError):ground(b)
    def test_degenerate(self):
        b=fixture();struct.pack_into('<3H',b,268,0,0,1)
        with self.assertRaises(ValueError):ground(b)
    def test_truncated(self):
        with self.assertRaises(ValueError):ground(fixture()[:-1])


if __name__=='__main__':unittest.main()
