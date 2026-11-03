"""Synthetic checks for the measured current-frame blur reference."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from reconstruct_menu_blur import reconstruct,sample

class BlurTests(unittest.TestCase):
    def test_two_native_modulations_and_partial_writes(self):
        source=np.full((512,512,3),128,dtype=np.uint8)
        a,b,c,d=reconstruct(source)
        self.assertEqual(a[50,50,0],129)
        self.assertEqual(b[50,50,0],130)
        self.assertEqual(d[50,50,0],130)
        self.assertTrue(np.all(b[256:]==0))
        self.assertTrue(np.all(d[:,256:]==0))
        np.testing.assert_array_equal(c[128:],a[128:])
        self.assertTrue(np.all(source==128))
    def test_no_retained_working_image(self):
        reconstruct(np.full((512,512,3),255,dtype=np.uint8))
        for image in reconstruct(np.zeros((512,512,3),dtype=np.uint8)):
            self.assertFalse(np.any(image))
    def test_linear_centers_and_clamp(self):
        image=np.array([[[0]*3,[100]*3]],dtype=np.uint8)
        np.testing.assert_allclose(sample(image,4,1)[0,:,0],[0,25,75,100])
    def test_rejects_other_surface_shapes(self):
        with self.assertRaises(ValueError):reconstruct(np.zeros((256,256,3),dtype=np.uint8))
        with self.assertRaises(ValueError):reconstruct(np.zeros((512,512,3)))

if __name__ == "__main__":unittest.main()
