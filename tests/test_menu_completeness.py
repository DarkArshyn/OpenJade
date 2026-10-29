"""Synthetic checks for cached color correspondence; no game assets."""
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from audit_menu_completeness import compare_cached


class CachedColorTests(unittest.TestCase):
    def setUp(self):
        self.vertices=np.array([[1,2,3,.2,.3],[4,5,6,.7,.8]])
        self.indices=np.array([1,0,1])
        self.primary=self.vertices[self.indices].copy()
        self.rgb=np.array([[10,20,30],[40,50,60]])/255
        self.bgra=np.array([[30,20,10,253],[60,50,40,254]],dtype=np.uint8)

    def check(self):
        return compare_cached(self.primary,self.indices,self.rgb,self.vertices,self.indices,self.bgra)

    def test_channel_order_and_reused_indices(self):
        self.assertEqual(self.check(),dict(corners=3,position_max_error=0.,uv_max_error=0.,rgb_mismatches=0))

    def test_half_colors_do_not_match(self):
        self.bgra[:,:3]//=2
        self.assertEqual(self.check()['rgb_mismatches'],3)

    def test_geometry_and_uv_mismatch_are_separate(self):
        self.primary[0,0]+=2
        self.primary[1,3]+=.25
        r=self.check()
        self.assertEqual(r['position_max_error'],2)
        self.assertAlmostEqual(r['uv_max_error'],.25)
        self.assertEqual(r['rgb_mismatches'],0)

    def test_out_of_range_indices_rejected(self):
        self.indices[0]=2
        with self.assertRaises(ValueError):self.check()


if __name__=='__main__':unittest.main()
