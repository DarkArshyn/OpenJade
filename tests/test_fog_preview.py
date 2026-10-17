import sys,unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from preview_menu3d_fog import render


class FogTests(unittest.TestCase):
    def setUp(self):
        self.v=np.array([[0,0,0],[0,2,0],[0,0,1],[0,2,1]],dtype=float)
        self.uv=np.array([[0,0],[2,0],[0,1],[2,1]],dtype=float)
        self.tri=np.array([[0,1,2],[2,1,3]])
        self.tex=np.array([[[255,0,0,255],[0,255,0,255]],[[0,0,255,255],[255,255,255,255]]],dtype=np.uint8)
    def test_translation_preserves_centered_raster(self):
        a,n=render(self.v,self.uv,self.tri,self.tex,True,False)
        b,m=render(self.v+[5,7,9],self.uv,self.tri,self.tex,True,False)
        self.assertEqual(a.tobytes(),b.tobytes());self.assertEqual(n,m);self.assertGreater(n,0)
    def test_sampling_modes_differ_inside_mesh(self):
        a,_=render(self.v,self.uv,self.tri,self.tex,True,False)
        b,_=render(self.v,self.uv,self.tri,self.tex,False,False)
        c,_=render(self.v,self.uv,self.tri,self.tex,True,True)
        box=(40,45,400,230)
        self.assertNotEqual(a.crop(box).tobytes(),b.crop(box).tobytes())
        self.assertNotEqual(a.crop(box).tobytes(),c.crop(box).tobytes())
    def test_degenerate_projection_rejected(self):
        with self.assertRaises(ValueError):render(self.v,self.uv,np.array([[0,0,1]]),self.tex,True,False)


if __name__=='__main__':unittest.main()
