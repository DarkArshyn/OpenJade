import math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from preview_menu3d_camera import vertical_fov

class ProjectionTests(unittest.TestCase):
    def test_vertical_angle(self):
        self.assertAlmostEqual(vertical_fov(math.pi/3,4/3,False),60)
    def test_horizontal_conversion(self):
        result=vertical_fov(math.pi/2,4/3,True)
        self.assertAlmostEqual(result,73.73979529168804)
        self.assertAlmostEqual(math.tan(math.radians(result)/2)*(4/3),1)
    def test_invalid_parameters(self):
        for angle,aspect in [(0,1),(math.pi,1),(float('nan'),1),(1,0),(1,-1),(1,float('inf'))]:
            with self.assertRaises(ValueError):vertical_fov(angle,aspect,True)

if __name__=='__main__':unittest.main()
