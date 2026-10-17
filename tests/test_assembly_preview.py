import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from preview_menu3d_assembly import clip_near


class ClippingTests(unittest.TestCase):
    def test_hidden(self):self.assertIsNone(clip_near([0,0,-1],[1,1,0]))
    def test_visible(self):
        a,b=clip_near([0,0,1],[1,1,2]);np.testing.assert_array_equal(a,[0,0,1]);np.testing.assert_array_equal(b,[1,1,2])
    def test_crossing_and_reversal(self):
        a,b=clip_near([0,0,-1],[2,4,1]);self.assertAlmostEqual(a[2],.1)
        np.testing.assert_allclose(a,[1.1,2.2,.1])
        c,d=clip_near([2,4,1],[0,0,-1]);np.testing.assert_allclose(c,b);np.testing.assert_allclose(d,a)


if __name__=='__main__':unittest.main()
