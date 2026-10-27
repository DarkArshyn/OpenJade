"""Tests of quaternion convention, shortest path and timeline boundaries."""
import sys,unittest,math
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from sample_camera02_animation import quaternion_matrix,native_slerp,sample_track,sample_pose

class AnimationTests(unittest.TestCase):
    def test_row_rotation(self):
        q=[0,0,math.sqrt(.5),math.sqrt(.5)]
        np.testing.assert_allclose(np.array([1,0,0])@quaternion_matrix(q),[0,1,0],atol=1e-14)
    def test_shortest_path(self):
        q=np.array([0,0,0,1.])
        np.testing.assert_array_equal(native_slerp(q,-q,.5),q)
    def test_half_angle(self):
        q=native_slerp([0,0,0,1],[0,0,1,0],.5)
        np.testing.assert_allclose(q,[0,0,math.sqrt(.5),math.sqrt(.5)])
    def test_segment_and_final_key(self):
        track=dict(kind='vector',keys=[dict(values=[0,0,0],start_seconds=0,duration_seconds=2),dict(values=[4,0,0],start_seconds=2,duration_seconds=0)])
        np.testing.assert_array_equal(sample_track(track,1),[2,0,0])
        np.testing.assert_array_equal(sample_track(track,2),[4,0,0])
    def test_bounds(self):
        for t in (-1,10,float('nan')):
            with self.assertRaises(ValueError):sample_pose(np.eye(4),{},t)

if __name__=='__main__':unittest.main()
