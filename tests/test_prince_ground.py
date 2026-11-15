"""Synthetic support-plane tests; no game data required."""
import struct
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from prince_ground import grounded_placement

class GroundTests(unittest.TestCase):
    def setUp(self):
        name = b'Menu3D_FarahRoom_Balcony.gao\0'
        obj = bytearray(len(name)+98)
        obj[:4] = b'.gao'; struct.pack_into('<I',obj,16,len(name)); obj[20:20+len(name)]=name
        matrix=np.eye(4); matrix[3,2]=2
        struct.pack_into('<16f',obj,len(name)+30,*matrix.ravel()); struct.pack_into('<I',obj,len(obj)-4,0x30000D18)
        data=bytearray(4614);data[:6]=bytes.fromhex('280200cc0509');struct.pack_into('<I',data,6,84)
        struct.pack_into('<9f',data,10,-1,-1,0,1,-1,0,0,1,0)
        struct.pack_into('<I',data,1018,130);struct.pack_into('<3f',data,1022,0,0,1)
        struct.pack_into('<3I',data,2582,1,130,368);struct.pack_into('<3H',data,2594,0,1,2)
        self.data=data; self.obj=obj
        self.resources={0x30000CD9:obj,0x30000D18:struct.pack('<2I',0xff01,0x30000D19),0x30000D19:data}
        self.checkpoint=np.eye(4);self.checkpoint[3,2]=3
    def resolve(self):
        with patch('prince_ground.node',return_value=(self.checkpoint,None,'checkpoint')):
            return grounded_placement(self.resources)
    def test_source_plane_sets_height_and_preserves_other_coordinates(self):
        placement,report=self.resolve()
        self.assertEqual(placement[3,2],2)
        self.assertEqual(self.checkpoint[3,2],3)
        np.testing.assert_array_equal(placement[:3],self.checkpoint[:3])
        self.assertEqual(report['hits'][0]['indices'],[0,1,2])
    def test_plane_translation_is_not_a_captured_height_constant(self):
        n=struct.unpack_from('<I',self.obj,16)[0]
        struct.pack_into('<f',self.obj,n+30+56,1.25)
        self.assertEqual(self.resolve()[0][3,2],1.25)
    def test_missing_and_ambiguous_support_fail(self):
        self.checkpoint[3,0]=4
        with self.assertRaises(ValueError):self.resolve()
        self.checkpoint[3,0]=0;struct.pack_into('<3H',self.data,2600,0,1,2)
        with self.assertRaises(ValueError):self.resolve()
    def test_invalid_indices_and_truncation_fail(self):
        struct.pack_into('<H',self.data,2594,84)
        with self.assertRaises(ValueError):self.resolve()
        self.resources[0x30000D19]=self.data[:-1]
        with self.assertRaises(ValueError):self.resolve()
    def test_downward_normal_or_plane_above_spawn_fails(self):
        struct.pack_into('<f',self.data,1030,-1)
        with self.assertRaises(ValueError):self.resolve()
        struct.pack_into('<f',self.data,1030,1);self.checkpoint[3,2]=1
        with self.assertRaises(ValueError):self.resolve()

if __name__=='__main__':unittest.main()
