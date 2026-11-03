"""Synthetic checks for the native version-23 cursor and field mapping."""
import math,struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_rain_parameters import decode,summary,initial_sample
class RainTests(unittest.TestCase):
    def source(self):
        d=bytearray(274);struct.pack_into('<3I',d,0,11,23,150)
        struct.pack_into('<f',d,38,50);struct.pack_into('<f',d,106,-70)
        return d
    def test_cursor_unaligned_fields_and_tail(self):
        d=self.source();struct.pack_into('<f',d,270,7.5)
        fields=decode(d)
        self.assertEqual(len(fields),74)
        self.assertEqual(fields['15c']['file_offset'],270)
        self.assertEqual(fields['15c']['value'],7.5)
        s=summary(fields);self.assertEqual(s['emission_rate'],50)
        self.assertEqual(s['acceleration'],[0,0,-70])
    def test_rejects_extent_and_version(self):
        d=self.source()
        for bad in [d[:-1],d+b'\0',bytes(274)]:
            with self.assertRaises(ValueError):decode(bad)
    def test_native_seed_samples(self):
        identity=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
        for seed,x,z,t in [(1,2.469923973,1.020112038,.000125125895),(42,3.338114738,-.110049605,.000534073915),(12345,1.401776314,-3.865657568,.02314523794)]:
            p=initial_sample(seed,identity)
            self.assertAlmostEqual(p['position'][0],x,places=6)
            self.assertAlmostEqual(p['position'][2],z,places=6)
            self.assertAlmostEqual(p['timer'],t,places=7)
    def test_emitter_axes(self):
        matrix=[1,0,0,0,0,0,-1,0,0,1,0,0,10,20,30,1]
        p=initial_sample(42,matrix)
        self.assertAlmostEqual(p['position'][2],30)
        self.assertAlmostEqual(p['position'][1],19.889950395,places=5)
    def test_invalid_matrix(self):
        with self.assertRaises(ValueError):initial_sample(1,[0]*15)
    def test_rejects_nonfinite(self):
        d=self.source();struct.pack_into('<f',d,38,math.nan)
        with self.assertRaises(ValueError):decode(d)
if __name__=='__main__':unittest.main()
