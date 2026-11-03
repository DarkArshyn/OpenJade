import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_rain_appearance import packed_lerp,appearance,UVS
class AppearanceTests(unittest.TestCase):
    def test_packed_endpoints(self):
        self.assertEqual(packed_lerp(0x11223344,0xffeeddcc,0),0x11223344)
        self.assertEqual(packed_lerp(0x11223344,0xffeeddcc,1),0xffeeddcc)
    def test_midpoint_is_native_approximation(self):
        self.assertEqual(packed_lerp(0,0xffffffff,.5),0x7f7f7f7f)
        self.assertEqual(packed_lerp(0xffffffff,0xffffffff,.5),0xf7f7f7f7)
    def test_initial_phase_scales_both_axes(self):
        matrix=[1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1]
        particle=[1,10,20,30,0,0,0,0,1,.5,2,4]
        vertices=appearance(particle,matrix,[0,0xffffffff,0xffffffff,0])
        self.assertEqual(vertices[0][0],(9,20,32))
        self.assertEqual(vertices[2][0],(11,20,28))
        self.assertEqual(tuple(v[1] for v in vertices),UVS)
    def test_rejects_unknown_flags(self):
        with self.assertRaises(ValueError):appearance([8]+[0]*11,[0]*16,[0]*4)
if __name__=='__main__':unittest.main()
