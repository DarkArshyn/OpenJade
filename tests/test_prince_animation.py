import struct
import unittest
import numpy as np
from prince_animation import decode_tracks, sample

class Tracks(unittest.TestCase):
    def fixture(self):
        return struct.pack('<2H',1,2)+struct.pack('<HHII',0x8200,0,32,2)+struct.pack('<B3H3f',10,0x80,16,1,0,0,0)+struct.pack('<B3f',0,10,20,30)
    def test_translation_uses_key_time(self):
        t=decode_tracks(self.fixture())[0]
        np.testing.assert_array_equal(sample(t,5),[5,10,15])
        np.testing.assert_array_equal(sample(t,100),[10,20,30])
    def test_rejects_every_truncation_and_tail(self):
        d=self.fixture()
        for i in range(len(d)):
            with self.assertRaises(ValueError):decode_tracks(d[:i])
        with self.assertRaises(ValueError):decode_tracks(d+b'\0')
    def test_rejects_bad_allocation_and_duration(self):
        d=bytearray(self.fixture());struct.pack_into('<I',d,8,31)
        with self.assertRaises(ValueError):decode_tracks(d)
        d=bytearray(self.fixture());d[16]=0
        with self.assertRaises(ValueError):decode_tracks(d)
    def test_invalid_sample_time(self):
        t=decode_tracks(self.fixture())[0]
        for value in (-1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):sample(t,value)

if __name__=='__main__':unittest.main()
