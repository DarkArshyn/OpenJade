"""Version-23 particle parameter mapping established from the PC GOG reader.

Offsets refer to the payload including its eight-byte type/version header.
This module decodes parameters; it does not simulate random spawning or rendering.
"""
import math,struct

def decode(data):
    if len(data)!=274 or struct.unpack_from('<2I',data)!=(11,23):
        raise ValueError('Expected bounded version-23 particle descriptor')
    fields={};cursor=8
    def take(destination,kind):
        nonlocal cursor
        value=struct.unpack_from('<'+kind,data,cursor)[0]
        if kind=='f' and not math.isfinite(value):raise ValueError('Nonfinite parameter')
        fields[f'{destination:03x}']=dict(file_offset=cursor,value=value,kind=kind)
        cursor+=struct.calcsize('<'+kind)
    for dest in [8,0x14,0x18]:take(dest,'I')
    for dest in [0x1c,0x1d]:take(dest,'B')
    for dest in [0x40,0x44,0x48,0x4c,0xdc,*range(0x50,0x88,4),0x8c,0x90,0x94,0x98,0x88]:take(dest,'f')
    for dest in [0xe8,0xe0,0xe4,0xec]:take(dest,'I')
    for dest in range(0x9c,0xbc,4):take(dest,'f')
    for dest in [0xf0,0xf1,0xf2]:take(dest,'B')
    take(0x20,'I');take(0x2c,'I');take(0x38,'H');take(0x30,'I');take(0x3a,'H');take(0x34,'I');take(0x3c,'H');take(0x24,'I')
    for dest in range(0xbc,0xdc,4):take(dest,'f')
    for dest in [0xf5,0xf6]:take(dest,'B')
    take(0x160,'I');take(0x10,'I');take(0x1e,'B')
    for dest in range(0x13c,0x160,4):take(dest,'f')
    if cursor!=len(data):raise ValueError('Unexpected cursor')
    return fields

def summary(fields):
    def v(n):return fields[f'{n:03x}']['value']
    return dict(stored_capacity=v(8),flags=f'0x{v(0x14):08X}',emission_rate=v(0xdc),
        spawn_mode=v(0x1c),velocity_mode=v(0x1d),rectangle_half_extents=[v(0x44),v(0x48)],
        initial_speed_range=[v(0x50),v(0x54)],phase1_range=[v(0x80),v(0x84)],
        main_phase_range=[v(0x70),v(0x74)],phase2_range=[v(0x78),v(0x7c)],
        acceleration=[v(0x8c),v(0x90),v(0x94)])


def f32(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]


def initial_sample(seed, matrix):
    """Independent rain-only creation reference; RNG state is supplied, not inferred.

    The native rain mode uses matrix rows 0 and 2. This does not resolve a GAO
    hierarchy or reproduce other consumers of the shared CRT random stream.
    """
    if len(matrix)!=16 or not all(math.isfinite(v) for v in matrix):
        raise ValueError('Expected finite 4x4 matrix')
    def random_unit():
        nonlocal seed
        seed=(seed*214013+2531011)&0xffffffff
        return f32(((seed>>16)&32767)/32767.)
    phase=f32(random_unit()*f32(.1));flag=1
    if phase==0:
        random_unit();phase=1.;flag=0
    size_x=f32((f32(.8)-f32(.1))*random_unit()+f32(.1))
    size_y=f32(random_unit()+1.)
    x=f32((2*random_unit()-1)*4)
    z=f32((2*random_unit()-1)*6)
    random_unit() # Zero speed still consumes a random number.
    position=[f32(f32(matrix[12+i]+matrix[i]*x)+matrix[8+i]*z) for i in range(3)]
    return dict(position=position,timer=phase,flags=flag,sizes=[size_x,size_y],next_seed=seed)
