"""Bounded sky/moon states from the frozen PC GOG menu."""
import struct

SKY_KEYS = {'0x30000CAC': 0x00006007, '0x30000D1B': 0x00014607}
SCALED_SKY_OBJECTS = {'0x30000CC4', '0x30000D1D'}


def decode_sky(data, key):
    if key not in SKY_KEYS or len(data) != 48 or struct.unpack_from('<2I',data) != (5,6):
        raise ValueError('Unsupported sky material')
    flags,u,v,rotation,texture=struct.unpack_from('<5I',data,28)
    expected_rotation=0x80000000 if key=='0x30000D1B' else 0
    if flags != SKY_KEYS[key] or (u,v,rotation)!=(0,0x3F800000,expected_rotation):
        raise ValueError('Unverified sky material state')
    # A zero U word selects the native identity UV fallback; rotation low bits are zero.
    return dict(flags=flags,texture=f'0x{texture:08X}',scale=[1.,1.],rate=[0.,0.],
                alpha=(rotation>>24)/255 if flags&0x400 else 1.,
                blend=(flags>>16)&15,depth_write=not bool(flags&0x200),
                rgb_gain=1. if key=='0x30000D1B' else 2.)
