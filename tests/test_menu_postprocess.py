"""Synthetic framebuffer tests with no original game data."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from compare_menu_postprocess import composite

class CompositeTests(unittest.TestCase):
    def test_captured_alpha_arithmetic(self):
        before=np.full((2,2,3),100,dtype=np.uint8)
        texture=np.full((4,4,3),200,dtype=np.uint8)
        np.testing.assert_allclose(composite(before,texture,104),100+100*104/255)
        np.testing.assert_array_equal(composite(before,texture,0),before)
    def test_texel_centers_and_bilinear_upsampling(self):
        texture=np.zeros((4,4,3),dtype=np.uint8)
        texture[:2,1,:]=100
        # Half the texture covers four screen pixels: clamp, 25%, 75%, 75%.
        actual=composite(np.zeros((1,4,3),dtype=np.uint8),texture,255)
        np.testing.assert_allclose(actual[0,:,0],[0,25,75,75])
    def test_rejects_invalid_alpha(self):
        with self.assertRaises(ValueError):composite(np.zeros((1,1,3)),np.zeros((1,1,3)),256)

if __name__ == "__main__":unittest.main()
