"""Synthetic fixture pass, UV and composition regressions."""
import sys,struct,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_fixture_materials import decode_fixture, sample_stage, composite_fixture

def material(key):
    data=bytearray(72);struct.pack_into('<2I',data,0,5,6)
    struct.pack_into('<H',data,24,1)
    flags=(0xc0066207,0xc0066207) if key=='0x2E00541D' else (0x200407,0x10207)
    for offset,flag in zip((24,48),flags):
        struct.pack_into('<5I',data,offset+4,flag,0x3f800000,0x3f800000,0,123)
    return data

class FixtureTests(unittest.TestCase):
    def test_decode_and_reject(self):
        d=material('0x2E00541D');s=decode_fixture(d,'0x2E00541D')
        self.assertEqual([x['blend'] for x in s],[6,6])
        self.assertFalse(any(x['depth_write'] for x in s))
        for bad in (d[:-1],d+b'\0'):
            with self.assertRaises(ValueError):decode_fixture(bad,'0x2E00541D')
        d[48]=1
        with self.assertRaises(ValueError):decode_fixture(d,'0x2E00541D')
    def test_native_zero_word_bypasses_uv_transform(self):
        d=material('0x3000FCCE');struct.pack_into('<I',d,32,0)
        s=decode_fixture(d,'0x3000FCCE')[0]
        self.assertEqual(s['scale'],[1,1]);self.assertEqual(s['rate'],[0,0])
    def test_static_and_dynamic_offsets(self):
        image=np.array([[[0,0,0,255],[100,0,0,255]]],float)
        uv=np.array([[.25,.5]]);s=dict(flags=3,scale=[1,1],rate=[.5,0])
        self.assertEqual(sample_stage(image,uv,s,0)[0,0],100)
        s['flags']|=0x40000000
        self.assertEqual(sample_stage(image,uv,s,0)[0,0],0)
        self.assertEqual(sample_stage(image,uv,s,1)[0,0],100)
    def test_additive_alpha_and_saturation(self):
        s=dict(flags=3,scale=[1,1],rate=[0,0],alpha=1,blend=6,
               image=np.array([[[100,50,0,127.5]]]))
        result=composite_fixture(np.array([[100,100,100]]),np.array([[0,0]]),np.ones((1,3)),dict(stages=[s,s],time=0))
        np.testing.assert_array_equal(result,[[255,200,100]])
    def test_opaque_then_alpha_overlay(self):
        base=dict(flags=3,scale=[1,1],rate=[0,0],alpha=1,blend=0,image=np.array([[[50,0,0,255]]]))
        overlay=dict(base,blend=1,image=np.array([[[0,50,0,127.5]]]))
        result=composite_fixture(np.array([[200,200,200]]),np.array([[0,0]]),np.ones((1,3)),dict(stages=[base,overlay],time=0))
        np.testing.assert_array_equal(result,[[50,50,0]])

    def test_raster_second_pass_survives_equal_depth(self):
        from menu_colored_raster import raster
        base=dict(flags=3,scale=[1,1],rate=[0,0],alpha=1,blend=0,depth_write=True,image=np.array([[[50,0,0,255]]]))
        overlay=dict(base,blend=1,depth_write=False,image=np.array([[[0,50,0,127.5]]]))
        obj=dict(vertices=np.array([[-1,-5,-1],[1,-5,-1],[0,-5,1]]),uv=np.zeros((3,2)),colors=np.ones((3,3)),triangles=np.array([[0,1,2]]),groups=[(0,1)])
        image,_,_=raster([obj],{0:dict(stages=[base,overlay],time=0)},np.zeros(3),np.eye(3),60)
        np.testing.assert_array_equal(np.array(image)[300,400],[50,50,0])

if __name__=='__main__':unittest.main()
