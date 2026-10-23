"""Geometric invariants for the bounded native camera reconstruction."""
import sys,unittest,math
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_native_camera_math import converted_basis,view_matrix,projection_matrix

class NativeCameraTests(unittest.TestCase):
    def test_view_is_rigid_inverse(self):
        a=.7;b=np.array([[math.cos(a),math.sin(a),0],[-math.sin(a),math.cos(a),0],[0,0,1]])
        p=np.array([4.,-2.,8.]);world=np.eye(4);world[:3,:3]=b;world[3,:3]=p
        np.testing.assert_allclose(world@view_matrix(b,p),np.eye(4),atol=1e-12)
        np.testing.assert_allclose(np.r_[p,1]@view_matrix(b,p),[0,0,0,1],atol=1e-12)

    def test_axis_conversion(self):
        np.testing.assert_array_equal(converted_basis(np.eye(3)),[[-1,0,0],[0,0,-1],[0,-1,0]])

    def test_projection_edge_and_depth(self):
        p=projection_matrix(math.pi/2,.75,1,1000)
        clip=np.array([2.,0.,2.,1.])@p
        self.assertAlmostEqual(clip[0]/clip[3],1)
        self.assertLess(p[1,1],0)
        self.assertAlmostEqual(p[3,2],-.05,places=7)
        q=projection_matrix(math.pi/2,.75,1,1000,True)
        self.assertAlmostEqual(q[0,0],.75);self.assertAlmostEqual(q[1,1],-1)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):projection_matrix(1,0,1,1000)
        with self.assertRaises(ValueError):projection_matrix(1,1,1,1)
        with self.assertRaises(ValueError):view_matrix(np.eye(3)*2,[0,0,0])

if __name__=='__main__':unittest.main()
