"""Independent reference for the observed PC GOG rain quad and packed colors."""
import math,struct
from menu_rain_parameters import f32
UVS=((0.,1.),(0.,0.),(1.,0.),(1.,0.),(1.,1.),(0.,1.))
ORDER=(0,1,2,2,3,0)

def packed_lerp(a,b,t):
    """Native seven-term packed-byte interpolation, including endpoint thresholds."""
    t=f32(t)
    if not math.isfinite(t):raise ValueError('Nonfinite interpolation')
    if t>=f32(.98):return b
    if t<=f32(.02):return a
    bits=struct.unpack('<I',struct.pack('<f',f32(t+49152.)))[0]
    result=0
    for shift in range(1,8):
        value=b if bits&(1<<(8-shift)) else a
        mask=sum(((1<<(8-shift))-1)<<(8*i) for i in range(4))
        result+=(value>>shift)&mask
    return result

def appearance(particle,matrix,colors):
    """Return six (position, UV, ARGB) vertices for the verified rain flags.

    particle is flags followed by eleven native floats. Matrix is the effective
    4x4 emitter matrix; colors are initial, main-start, main-end, end entries.
    This excludes other particle modes, material modulation and blending.
    """
    if len(particle)!=12 or len(matrix)!=16 or len(colors)!=4:raise ValueError('Invalid extent')
    flag,*v=particle
    if flag not in (0,1,2) or not all(math.isfinite(x) for x in [*v,*matrix]):raise ValueError('Unsupported particle')
    ratio=f32(v[7]*v[8]);sx,sy=v[9:11]
    if flag==1:
        ratio=f32(1-ratio);color=packed_lerp(colors[0],colors[1],ratio)
        sx=f32(sx*ratio);sy=f32(sy*ratio)
    elif flag==2:color=packed_lerp(colors[3],colors[2],ratio)
    else:color=packed_lerp(colors[2],colors[1],ratio)
    # Native packed color is converted to D3DCOLOR by swapping red and blue.
    argb=(color&0xff00ff00)|((color&255)<<16)|((color>>16)&255)
    u=[f32(sx*matrix[i]) for i in range(3)];w=[f32(sy*matrix[4+i]) for i in range(3)]
    corners=[tuple(f32(f32(v[i]+sign_u*u[i])+sign_w*w[i]) for i in range(3)) for sign_u,sign_w in [(-1,-1),(-1,1),(1,1),(1,-1)]]
    return [(corners[idx],uv,argb) for idx,uv in zip(ORDER,UVS)]
