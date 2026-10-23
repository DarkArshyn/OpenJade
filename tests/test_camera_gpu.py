"""Camera recovery and packed-color regressions without game assets."""
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from fit_menu_camera import fit, project_pixels
from menu_gpu_colors import pack_color, direct_tree_colors


class CameraGpuTests(unittest.TestCase):
    def test_camera_recovers_known_projection(self):
        pixels=np.array([[100,120],[700,110],[200,480],[650,520],[370,210]])
        previous=[12,-1,50]; expected=[14,.4,58]
        target=project_pixels(pixels,previous,expected)
        np.testing.assert_allclose(fit(pixels,target,np.ones(5),previous),expected,atol=1e-5)
        np.testing.assert_allclose(project_pixels(pixels,previous,previous),pixels,atol=1e-10)

    def test_degenerate_camera_rejected(self):
        with self.assertRaises(ValueError):fit(np.tile([400,300],(4,1)),np.tile([400,300],(4,1)),np.ones(4),[12,-1,50])

    def test_packing_preserves_channels_and_masks(self):
        self.assertEqual(pack_color(0xFE6D4827),0xFE27486D)
        self.assertEqual(pack_color(0x00112233,0xff000000,0x000000ff),0xffcc2211)
        for channel in range(256):
            self.assertEqual(pack_color(channel)&0xffffff,channel<<16)

    def test_scoped_tree_and_late_saturation(self):
        states=[dict(material=k,mode=0) for k in ['0x30000C95','0x30000CA9']]
        colors=np.array([[.1,.3,.8]])
        result=direct_tree_colors(colors,0x0D2255FF,states)
        np.testing.assert_allclose(result,[[.2,.6,1.6]])
        np.testing.assert_allclose(colors,[[.1,.3,.8]])
        with self.assertRaises(ValueError):direct_tree_colors(colors,0,states)


if __name__=='__main__':unittest.main()
