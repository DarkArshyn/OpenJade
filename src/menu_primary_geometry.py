"""Bounded primary geometry and per-instance color readers for Menu3D."""
import struct
import numpy as np


def primary_mesh(data):
    if len(data)<44:raise ValueError('Short geometry')
    h=struct.unpack_from('<10I',data)
    if h[:2] not in ((1,7),(1,8)):raise ValueError('Unsupported geometry')
    nv,nc,has_colors,nu,ng=h[4:9]
    if not 0<nv<=500000 or not 0<=nu<=1000000 or not 0<ng<=4096:raise ValueError('Invalid counts')
    pos=40
    def take(fmt):
        nonlocal pos
        size=struct.calcsize(fmt)
        if pos+size>len(data):raise ValueError('Truncated primary geometry')
        result=struct.unpack_from(fmt,data,pos);pos+=size;return result
    if h[9]==0xc0de2002:
        _,bones=take('<HH')
        if bones>4096:raise ValueError('Bone count')
        for _ in range(bones):
            _,count=take('<HH');take('<16fI');take('<'+'I'*count)
    elif h[9]!=0:raise ValueError('Unknown geometry metadata')
    else:bones=0
    normals=take('<I')[0]
    if normals not in (0,1):raise ValueError('Normals flag')
    vertex_offset=pos
    vertices=np.array(take('<'+'f'*(nv*3))).reshape(-1,3)
    if normals:take('<'+'f'*(nv*3))
    colors=None
    if has_colors:
        if nc!=nv:raise ValueError('Partial color array')
        colors=np.array(take('<'+'B'*(nv*4)),dtype=np.uint8).reshape(-1,4)[:,:3]/255
    uv=np.array(take('<'+'f'*(nu*2))).reshape(-1,2)
    groups=[]
    for _ in range(ng):
        count,slot=take('<Ii')
        if count>2000000 or slot<0:raise ValueError('Invalid face group')
        groups.append((slot,count))
    nf=sum(c for _,c in groups)
    if not nf or nf>2000000:raise ValueError('Invalid faces')
    faces=np.array(take('<'+'H'*(nf*8))).reshape(-1,8)
    vi=faces[:,:3];ui=faces[:,3:6]
    if vi.max()>=nv or (nu>0 and ui.max()>=nu):raise ValueError('Primary index out of bounds')
    if not np.isfinite(vertices).all() or not np.isfinite(uv).all():raise ValueError('Nonfinite geometry')
    # Expand corners so distinct UV indices remain attached to the correct vertex.
    mapped_uv=uv[ui.ravel()] if nu else np.zeros((nf*3,2))
    expanded=np.column_stack((vertices[vi.ravel()],mapped_uv))
    triangles=np.arange(nf*3).reshape(-1,3)
    return expanded,triangles,groups,vi.ravel(),nv,colors,dict(vertex_offset=vertex_offset,primary_end=pos,bones=bones)


def instance_colors(data,link_offset,count):
    marker=b'\xff\xff'+struct.pack('<I',count)
    candidates=[]
    for pos in range(link_offset,min(link_offset+69,len(data)-5)):
        if data[pos:pos+6]!=marker:continue
        start=pos+6;end=start+4*count
        if end+4>len(data) or struct.unpack_from('<I',data,end)[0]!=1:continue
        values=np.frombuffer(data,dtype=np.uint8,count=4*count,offset=start).reshape(-1,4)
        if not np.isin(values[:,3],[253,254,255]).all():continue
        candidates.append((values[:,:3].astype(float)/255,start))
    if len(candidates)>1:raise ValueError('Ambiguous instance colors')
    return candidates[0] if candidates else (None,None)

