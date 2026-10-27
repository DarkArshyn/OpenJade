"""Projection-axis checks independent of visual camera fitting."""
import sys,math,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_native_camera_math import projection_angles
class ProjectionAnglesTests(unittest.TestCase):
    def test_horizontal_edge_geometry(self):
        r=projection_angles(math.pi/2,800,600)
        self.assertAlmostEqual(r['horizontal_degrees'],90)
        self.assertAlmostEqual(math.tan(math.radians(r['vertical_degrees']/2)),.75)
    def test_vertical_selector_mask(self):
        r=projection_angles(math.pi/2,800,600,4)
        self.assertAlmostEqual(r['vertical_degrees'],90)
        self.assertAlmostEqual(math.tan(math.radians(r['horizontal_degrees']/2)),4/3)
        self.assertEqual(projection_angles(1.3,800,600,16)['axis'],'horizontal')
    def test_ratio_source(self):
        for mode in (1,6):self.assertEqual(projection_angles(1.3,800,600,ratio_mode=mode,custom_ratio=2)['ratio'],.75)
        for mode in (0,7):self.assertEqual(projection_angles(1.3,800,600,ratio_mode=mode,custom_ratio=2)['ratio'],2)
    def test_invalid_dimensions(self):
        for w in (0,-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):projection_angles(1.3,w,600)
if __name__=='__main__':unittest.main()
