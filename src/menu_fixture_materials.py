"""Bounded two-pass fixture materials from the frozen PC GOG menu."""
import struct
import numpy as np

SUPPORTED = {
    '0x2E00541D': (0xC0066207, 0xC0066207),
    '0x3000FCCE': (0x00200407, 0x00010207),
}

def decode_fixture(data, key):
    if key not in SUPPORTED or len(data) != 72 or struct.unpack_from('<2I', data) != (5, 6):
        raise ValueError('Unsupported fixture material')
    if struct.unpack_from('<H', data, 24)[0] != 1 or struct.unpack_from('<H', data, 48)[0] != 0:
        raise ValueError('Invalid two-pass continuation')
    stages=[]
    for i, offset in enumerate((24,48)):
        flags,u,v,rotation,texture=struct.unpack_from('<5I',data,offset+4)
        if flags != SUPPORTED[key][i] or rotation & 0xffff:
            raise ValueError('Unverified fixture flags or rotation')
        # These resources encode no discrete UV rotation.
        if ((u >> 13) & 8) or ((u & 1) << 2) or ((v >> 15) & 2) or (v & 1):
            raise ValueError('Unverified discrete UV rotation')
        as_float=lambda w: struct.unpack('<f',struct.pack('<I',w & 0xffffffff))[0]
        scale=[as_float(w & 0xfffe0000) for w in (u,v)]
        rate=[as_float(w << 16)*s for w,s in zip((u,v),scale)]
        if u == 0 or v == 0 or (u,v)==(0x3f800000,0x3f800000):
            scale=[1.0,1.0];rate=[0.0,0.0]
        alpha=(rotation >> 24)/255 if flags & 0x400 else 1.0
        stages.append(dict(flags=flags,texture=f'0x{texture:08X}',scale=scale,rate=rate,
                           alpha=alpha,blend=(flags>>16)&15,depth_write=not bool(flags&0x200)))
    return stages

def sample_stage(image, uv, stage, time):
    if not np.isfinite(time) or time < 0:raise ValueError('Invalid fixture time')
    flags=stage['flags'];dynamic=np.array([bool(flags&0x40000000),bool(flags&0x80000000)])
    shift=np.array(stage['rate'])*np.where(dynamic,time,1.0)
    coords=np.asarray(uv)*stage['scale']+shift%1
    # Base-level bilinear wrap, matching the supported stages' address flags.
    h,w=image.shape[:2];xy=coords*np.array([w,h])-.5
    lo=np.floor(xy).astype(int);f=xy-lo;x=lo[...,0]%w;y=lo[...,1]%h
    fx=f[...,0,None];fy=f[...,1,None]
    return ((image[y,x]*(1-fx)+image[y,(x+1)%w]*fx)*(1-fy)+
            (image[(y+1)%h,x]*(1-fx)+image[(y+1)%h,(x+1)%w]*fx)*fy)

def composite_fixture(destination, uv, lighting, descriptor):
    result=np.asarray(destination,dtype=float).copy()
    for stage in descriptor['stages']:
        sample=sample_stage(stage['image'],uv,stage,descriptor['time'])
        source=np.clip(sample[...,:3]*lighting*2,0,255)
        alpha=sample[...,3,None]/255*stage['alpha']
        if stage['blend']==0:result=source
        elif stage['blend']==1:result=source*alpha+result*(1-alpha)
        elif stage['blend']==6:result=source*alpha+result
        else:raise ValueError('Unsupported fixture blend')
        result=np.clip(result,0,255)
    return result.astype(np.uint8)
