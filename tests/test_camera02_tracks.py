"""Synthetic tests of native-derived Camera02 packed track boundaries."""
import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from decode_camera02_tracks import decode

def sample():
    d=bytearray(struct.pack('<2H',3,2))
    for flags,count,size,kind in ((0xbc04,4,48,0),(0xba04,32,512,1)):
        d+=struct.pack('<HHII',flags,0xffff,size,count)
        for i in range(count):
            d+=struct.pack('<B' if kind else '<H',0 if i==count-1 else 60)
            if i==0:d+=struct.pack('<3H',0x80 if kind else 0x84,16 if kind else 12,1 if kind else 0x1010)
            d+=struct.pack('<3f',i,0,-i) if kind else struct.pack('<4h',-10,20,0,32760)
    return d+bytes(128)
class TrackTests(unittest.TestCase):
    def test_offsets_and_duration(self):
        r=decode(sample());a,b=r['tracks']
        self.assertEqual((a['duration_seconds'],b['duration_seconds']),(3,31))
        self.assertEqual(a['keys'][0]['duration_offset'],16)
        self.assertEqual(a['keys'][0]['value_offset'],24)
        self.assertEqual(b['keys'][0]['duration_offset'],74)
        self.assertEqual(b['keys'][0]['value_offset'],81)
        self.assertEqual(b['keys'][1]['duration_offset'],93)
        self.assertEqual(a['keys'][0]['values'][0],-10)
    def test_reject_truncated_and_unknown(self):
        d=sample()
        for bad in (d[:-1],d+b'\0'):
            with self.assertRaises(ValueError):decode(bad)
        d[4]^=1
        with self.assertRaises(ValueError):decode(d)
    def test_reject_nonfinite(self):
        d=sample();struct.pack_into('<f',d,81,float('nan'))
        with self.assertRaises(ValueError):decode(d)
    def test_preserve_third_track(self):
        d=sample();d[496:]=bytes(range(128))
        self.assertEqual(decode(d)['remaining_hex'],bytes(range(128)).hex())
if __name__=='__main__':unittest.main()
