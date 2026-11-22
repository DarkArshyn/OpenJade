"""Check receiver mapping independently of game assets and fixed bone indices."""
import sys,struct,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from prince_light_origins import encode

class Origins(unittest.TestCase):
    def test_source_indices_and_root_equipment(self):
        report={'triangles':4,'draws':[{'mesh':k,'triangles':1} for k in ['0x3F000E05','0x13008483','0x33001050','0x057CC7F4']]}
        with patch('prince_light_origins.Skeleton',return_value=SimpleNamespace(index={0x130035BE:11,0x130035C0:14})):
            data=encode(None,report)
        self.assertEqual(data[:8],b'OJAORG01')
        self.assertEqual(struct.unpack_from('<13I',data,8),(12,11,11,11,14,14,14,*([0xffffffff]*6)))
    def test_unknown_receiver_and_wrong_extent(self):
        with patch('prince_light_origins.Skeleton',return_value=SimpleNamespace(index={0x130035BE:3,0x130035C0:5})):
            for report in [{'triangles':1,'draws':[{'mesh':'0x12345678','triangles':1}]},
                           {'triangles':2,'draws':[{'mesh':'0x33001050','triangles':1}]}]:
                with self.assertRaises(ValueError):encode(None,report)

if __name__=='__main__':unittest.main()
