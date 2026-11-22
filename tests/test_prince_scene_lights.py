"""Synthetic checks for fixed-menu light conversion without game data."""
import unittest, struct, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from prince_scene_lights import LIGHTS, parameters

class Fixture:
    def __init__(self):
        self.data = {}
        for key, descriptor in LIGHTS:
            name = b'light.gao\0'; raw = bytearray(len(name)+148)
            raw[:4] = b'.gao'; struct.pack_into('<4I',raw,4,10,8,8208,len(name))
            raw[20:20+len(name)] = name
            matrix = np.eye(4); matrix[3,:3] = [10,20,30]
            struct.pack_into('<16f',raw,len(name)+30,*matrix.ravel())
            struct.pack_into('<I',raw,len(raw)-4,descriptor)
            self.data[key] = bytes(raw)
            self.data[descriptor] = struct.pack('<4I5f',2,9,0,0x00332211,2,6,.1,.2,1)
    def get(self,key):return self.data[key]

class Lights(unittest.TestCase):
    def test_coordinate_conversion_and_preserved_generated_term(self):
        pose=np.eye(4);pose[3,:3]=[1,2,3];capture=np.arange(31,dtype=float)
        result=parameters(Fixture(),pose,capture)
        np.testing.assert_allclose(result[15:18],[9,18,27])
        np.testing.assert_allclose(result[3:6],[0,1,0])
        np.testing.assert_allclose(result[:3],np.array([17,34,51])/255)
        np.testing.assert_array_equal(result[9:15],capture[9:15])
        np.testing.assert_allclose(result[21:23],[6,.25])
        np.testing.assert_array_equal(capture,np.arange(31))
    def test_resource_changes_drive_result(self):
        r=Fixture();key=LIGHTS[1][1];d=bytearray(r.data[key]);struct.pack_into('<2f',d,16,3,11);r.data[key]=bytes(d)
        np.testing.assert_allclose(parameters(r,np.eye(4),np.zeros(31))[21:23],[11,.125])
    def test_reject_bad_ranges_link_and_placement(self):
        for mode in ('range','link','scale'):
            r=Fixture();pose=np.eye(4)
            if mode=='scale':pose[0,0]=2
            else:
                key=LIGHTS[0][1 if mode=='range' else 0];d=bytearray(r.data[key])
                if mode=='range':struct.pack_into('<2f',d,16,6,2)
                else:struct.pack_into('<I',d,len(d)-4,0)
                r.data[key]=bytes(d)
            with self.assertRaises(ValueError):parameters(r,pose,np.zeros(31))

if __name__=='__main__':unittest.main()
