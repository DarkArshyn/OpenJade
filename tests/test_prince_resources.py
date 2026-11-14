"""Synthetic bounds and packed-weight regression checks; no game data required."""
import struct
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from prince_resources import Resources, geometry


def record(key,data):return struct.pack('<3I',len(data),0xEEFFC099,key)+data

def mesh():
    h=struct.pack('<10I',1,7,0,0,3,0,1,3,1,0xC0DE2002)
    matrix=np.eye(4,dtype='<f4').tobytes()
    skin=struct.pack('<4H',0,1,0,3)+matrix+struct.pack('<4I',6,0x3f800000,0x3f800001,0x3f800002)
    return h+skin+struct.pack('<I',1)+struct.pack('<18f',0,0,0,1,0,0,0,1,0,0,0,1,0,0,1,0,0,1)+struct.pack('<6f',0,0,1,0,0,1)+struct.pack('<Ii8H',1,0,0,1,2,0,1,2,0,0)

class Bounds(unittest.TestCase):
    def test_keeps_native_weight_index_bits_and_empty_colors(self):
        g=geometry(mesh())
        self.assertIsNone(g['colors'])
        self.assertEqual(g['weights'][2,0],struct.unpack('<f',struct.pack('<I',0x3f800002))[0])
        self.assertGreater(g['weights'][2,0],1.)
        self.assertEqual(g['faces'][0,:3].tolist(),[0,1,2])
    def test_rejects_truncation_and_bad_weight_index(self):
        with self.assertRaises(ValueError):geometry(mesh()[:-1])
        b=bytearray(mesh());struct.pack_into('<I',b,116,0x3f800003)
        with self.assertRaises(ValueError):geometry(b)
    def test_palette_and_duplicate_declarations(self):
        header=bytearray(60);struct.pack_into('<I',header,0,1);struct.pack_into('<2H',header,12,8,8);struct.pack_into('<5I',header,40,1,8,8,0,2)
        palette=struct.pack('<I',2)+bytes([5,10,15,255])*256
        data=record(1,header)+record(1,header+bytes(64))+record(2,palette)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'records.bin';p.write_bytes(data)
            r=Resources([p,p]);levels,_=r.texture(1)
            self.assertEqual(levels[0][0,0].tolist(),[15,10,5,255])
            self.assertEqual(levels[0].shape,(8,8,4))
            altered=bytearray(palette);altered[4]=9;p.write_bytes(data+record(2,altered))
            with self.assertRaises(ValueError):Resources([p]).texture(1)
    def test_rejects_truncated_texture(self):
        header=bytearray(60);struct.pack_into('<I',header,0,1);struct.pack_into('<2H',header,12,8,8);struct.pack_into('<5I',header,40,1,8,8,0,2)
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'bad.bin';p.write_bytes(record(1,header+bytes(63))+record(2,struct.pack('<I',2)+bytes(1024)))
            with self.assertRaises(ValueError):Resources([p]).texture(1)

if __name__=='__main__':unittest.main()
