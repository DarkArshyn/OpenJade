"""Compare raster landmark centroids with the independently traced native matrices."""
import sys,unittest,math
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_colored_raster import raster
from preview_menu3d_landmarks import raster as landmark_raster
from menu_native_camera_math import converted_basis,view_matrix,projection_matrix
class ProjectionTests(unittest.TestCase):
 def test_landmarks_match_native_chain(self):
  self.check_projection(raster)
 def test_legacy_landmarks_match_native_chain(self):
  self.check_projection(landmark_raster)
 def check_projection(self,renderer):
  angle=.4;b=np.array([[math.cos(angle),math.sin(angle),0],[-math.sin(angle),math.cos(angle),0],[0,0,1]])
  eye=np.array([11.,-7.,3.]);fov=60
  for center in ([1.,-5.,.5],[-1.,-5.,-.5],[0.,-5.,0.]):
   with self.subTest(center=center):
    local=np.array(center)+np.array([[-.08,0,-.06],[.08,0,-.06],[0,0,.12]])
    world=local@b+eye
    obj=dict(vertices=world,uv=np.zeros((3,2)),colors=np.ones((3,3)),triangles=np.array([[0,1,2]]),groups=[(0,1)])
    im,coverage,_=renderer([obj],{0:np.array([[[255,255,255,255]]],dtype=np.uint8)},eye,b,fov)
    yy,xx=np.where(np.asarray(im)[:,:,0]==255);self.assertGreater(coverage,0)
    point=np.r_[np.array(center)@b+eye,1]
    clip=point@view_matrix(converted_basis(b),eye)@projection_matrix(math.radians(fov),.75,1,1000,True)
    ndc=clip[:2]/clip[3];expected=[400+400*ndc[0],300-300*ndc[1]]
    np.testing.assert_allclose([xx.mean()+.5,yy.mean()+.5],expected,atol=1)
if __name__=='__main__':unittest.main()
