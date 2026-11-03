"""Synthetic coverage of alpha extraction and the additive pyramid."""
import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from reconstruct_menu_additive import reconstruct,composite
class AdditiveTests(unittest.TestCase):
    def test_zero_mask_preserves_scene(self):
        rgba=np.full((512,512,4),200,dtype=np.uint8);rgba[:,:,3]=0
        levels=reconstruct(rgba)
        self.assertTrue(all(not np.any(v) for v in levels))
        scene=np.full((37,51,3),123,dtype=np.uint8)
        np.testing.assert_array_equal(composite(scene,levels),scene)
    def test_mask_gain_and_sizes(self):
        rgba=np.full((512,512,4),100,dtype=np.uint8);rgba[:,:,3]=255
        levels=reconstruct(rgba)
        self.assertEqual([v.shape[0] for v in levels],[256,128,64,32,16,8])
        self.assertEqual(int(levels[0][0,0,0]),100)
        self.assertGreater(int(levels[-1][0,0,0]),100)
        self.assertTrue(np.all(composite(np.zeros((9,11,3),dtype=np.uint8),levels)==255))
if __name__=="__main__":unittest.main()
