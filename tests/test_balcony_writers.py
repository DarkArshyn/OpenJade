import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from inspect_balcony_writers import callback_tail
class CallbackTests(unittest.TestCase):
    def test_index_is_not_compacted(self):
        d=struct.pack('<12I',0,0,12,0,0,6,0,0,0,0,123,456)
        self.assertEqual(callback_tail(d)['indexed'][5],456)
    def test_extent(self):
        for d in (bytes(20),struct.pack('<6I',0,0,0,0,0,1),bytes(25)):
            with self.assertRaises(ValueError):callback_tail(d)
if __name__=='__main__':unittest.main()
