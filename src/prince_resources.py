"""Bounded readers for the original PC Prince character resources."""
import hashlib
import struct
from pathlib import Path
import numpy as np
from PIL import Image
from probe_menu3d import records
from inspect_menu_scene_links import static_links

COMPONENTS=(0x057CC7FF,0x057CC800,0x3F000E24,0x13005EEA,0x1300695C,
            0x1300695F,0x13006962,0x13006955,0x1300695D,0x13006959,0x1300695E,0x130033F7)

def material_slot(materials, requested):
    """Resolve a nonnegative index in a nonempty decoded PC material pack."""
    if not materials or not isinstance(requested, int) or requested < 0:
        raise ValueError('Unsupported empty material pack or negative index')
    # Native selection is independently observed to retain the last available entry.
    return min(requested, len(materials) - 1)


class Resources:
    def __init__(self, paths):
        self.by={};self.sources=[];self.used={}
        for path in paths:
            path=Path(path);data=path.read_bytes()
            self.sources.append(dict(path=str(path.resolve()),sha256=hashlib.sha256(data).hexdigest()))
            for r in records(data):
                key=int(r['key'],16);payload=data[r['offset']+12:r['end']]
                self.by.setdefault(key,{}).setdefault(payload,[]).append(dict(source=len(self.sources)-1,offset=r['offset'],size=r['size']))
    def get(self,key,full_texture=False):
        candidates=self.by.get(key,{})
        # Texture declarations contain no pixel data. Distinct full payloads remain ambiguous.
        if full_texture:candidates={d:r for d,r in candidates.items() if len(d)>60}
        if len(candidates)!=1:raise ValueError(f'Missing or ambiguous resource {key:08X}: {len(candidates)}')
        data,locations=next(iter(candidates.items()))
        self.used[f'{key:08X}']=dict(sha256=hashlib.sha256(data).hexdigest(),locations=locations)
        return data
    def texture(self,key):
        d=self.get(key,True)
        if len(d)<56 or struct.unpack_from('<I',d)[0]!=key:raise ValueError('Invalid texture identity')
        fmt,w,h,last=struct.unpack_from('<4I',d,40)
        if (w,h)!=struct.unpack_from('<HH',d,12) or not 0<w<=2048 or not 0<h<=2048 or last>12:
            raise ValueError('Unsupported texture dimensions')
        offset=60 if fmt in (1,5) else 56
        palette=None
        if fmt==1:
            pk=struct.unpack_from('<I',d,56)[0];p=self.get(pk)
            if len(p)!=1028 or struct.unpack_from('<I',p)[0]!=pk:raise ValueError('Invalid indexed palette')
            palette=np.frombuffer(p,dtype=np.uint8,offset=4).reshape(256,4)[:,[2,1,0,3]]
        elif fmt==5 and d[56:60]!=bytes.fromhex('000000c0'):raise ValueError('Unknown BC1 prefix')
        elif fmt not in (0,5,7):raise ValueError(f'Unsupported texture format {fmt}')
        levels=[]
        for i in range(last+1):
            x,y=max(8,w>>i),max(8,h>>i)
            size=x*y*(1 if fmt==1 else 4) if fmt in (0,1) else ((x+3)//4)*((y+3)//4)*(8 if fmt==5 else 16)
            if offset+size>len(d):raise ValueError('Truncated mip data')
            block=d[offset:offset+size];offset+=size
            if fmt==1:image=palette[np.frombuffer(block,np.uint8)].reshape(y,x,4)
            elif fmt==0:image=np.frombuffer(block,np.uint8).reshape(y,x,4)[:,:,[2,1,0,3]]
            else:image=np.array(Image.frombytes('RGBA',(x,y),block,'bcn',1 if fmt==5 else 3))
            levels.append(image)
        if offset!=len(d):raise ValueError(f'Unexpected mip extent {key:08X}: {offset}/{len(d)}')
        return levels,dict(key=f'{key:08X}',format=fmt,sizes=[[a.shape[1],a.shape[0]] for a in levels])
    def component(self,key):
        d=self.get(key);links=static_links(d);meshkey=int(links['mesh'],16)
        mesh=geometry(self.get(meshkey));pack=self.get(int(links['material_pack'],16))
        kind=struct.unpack_from('<I',pack)[0]
        if kind==4:
            count=struct.unpack_from('<I',pack,8)[0]
            if len(pack)!=12+4*count:raise ValueError('Material pack extent')
            materials=list(struct.unpack_from('<'+'I'*count,pack,12))
        elif kind==5:materials=[int(links['material_pack'],16)]
        else:raise ValueError('Unsupported material pack')
        n=struct.unpack_from('<I',d,16)[0]
        bindings=[]
        if mesh['bones']:
            at=links['link_offset']+42
            count=struct.unpack_from('<I',d,at)[0]
            if count!=len(mesh['bones']):raise ValueError('Bone binding count mismatch')
            for i in range(count):
                bone_key,global_id=struct.unpack_from('<2I',d,at+4+i*8)
                b=self.get(bone_key);bn=struct.unpack_from('<I',b,16)[0]
                if b[:4]!=b'.gao':raise ValueError('Bone binding is not a GAO')
                bindings.append(dict(key=f'{bone_key:08X}',global_id=global_id,name=b[20:20+bn-1].decode('ascii')))
        return dict(key=f'{key:08X}',**links,geometry=mesh,materials=materials,bindings=bindings)

def geometry(data):
    if len(data)<44:raise ValueError('Truncated geometry')
    h=struct.unpack_from('<10I',data)
    if h[:2] not in ((1,7),(1,8)):raise ValueError('Unsupported geometry header')
    nv,nc,has_colors,nu,ng=h[4:9]
    if not 0<nv<=65535 or nc not in (0,nv) or has_colors not in (0,1) or not 0<=nu<=65535 or not 0<ng<=256:
        raise ValueError('Unsupported geometry counts')
    offset=40
    def take(fmt):
        nonlocal offset
        size=struct.calcsize(fmt)
        if offset+size>len(data):raise ValueError('Truncated geometry block')
        value=struct.unpack_from(fmt,data,offset);offset+=size;return value
    bones=[];weights=None
    if h[9]==0xC0DE2002:
        _,nb=take('<2H')
        if not 0<nb<=64:raise ValueError('Bone count out of bounds')
        weights=np.zeros((nv,nb));seen=set()
        for i in range(nb):
            index,count=take('<2H')
            if index>=nb or index in seen or count>nv:raise ValueError('Invalid bone record')
            seen.add(index);matrix=np.array(take('<16f')).reshape(4,4);flags=take('<I')[0]
            words=np.array(take('<'+'I'*count),dtype='<u4');ids=words&65535
            if len(set(ids.tolist()))!=count or np.any(ids>=nv):raise ValueError('Invalid weighted vertex')
            # Native upload retains the low index bits in the floating-point weight.
            values=words.view('<f4').astype(float)
            if not np.isfinite(matrix).all() or not np.isfinite(values).all() or np.any(values<0) or np.any(values>1.01):raise ValueError('Invalid skin data')
            weights[ids,index]=values
            bones.append(dict(index=index,inverse_bind=matrix,flags=flags))
        bones.sort(key=lambda b:b['index'])
    elif h[9]!=0:raise ValueError('Unsupported geometry metadata')
    normal_flag=take('<I')[0]
    if normal_flag not in (0,1):raise ValueError('Invalid normals flag')
    position=np.array(take('<'+'f'*(nv*3))).reshape(nv,3)
    normals=np.array(take('<'+'f'*(nv*3))).reshape(nv,3) if normal_flag else None
    colors=np.array(take('<'+'B'*(nc*4)),dtype=np.uint8).reshape(nc,4) if has_colors and nc else None
    uv=np.array(take('<'+'f'*(nu*2))).reshape(nu,2)
    groups=[];total=0
    for _ in range(ng):
        count,slot=take('<Ii')
        if count>1000000 or slot<0:raise ValueError('Invalid face group')
        groups.append(dict(slot=slot,count=count,first=total));total+=count
    if not 0<total<=1000000:raise ValueError('Invalid face count')
    faces=np.array(take('<'+'H'*(total*8))).reshape(-1,8)
    if np.any(faces[:,:3]>=nv) or (nu and np.any(faces[:,3:6]>=nu)):raise ValueError('Face index out of bounds')
    if not np.isfinite(position).all() or not np.isfinite(uv).all() or (normals is not None and not np.isfinite(normals).all()):raise ValueError('Nonfinite geometry')
    if weights is not None and (np.any(weights.sum(1)<=0) or np.any((weights>0).sum(1)>3)):raise ValueError('Unsupported influence count')
    return dict(position=position,normals=normals,colors=colors,uv=uv,faces=faces,groups=groups,bones=bones,weights=weights,primary_end=offset)
