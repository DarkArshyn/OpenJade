"""Sample-specific landmark assembly and perspective-correct texture diagnostic."""
import argparse,hashlib,json,math,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from probe_menu3d import records

SOURCE_HASH='96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'
LANDMARKS=[('balcony','0x30000CD9','0x30000C8C',279420),
           ('tree','0x30000CC1','0x30000C74',14112),
           ('distant_tower','0x30000CD8','0x30000C8B',11492),
           ('fake_room','0x30000D41','0x30000D40',704)]


def mesh_groups(d,h):
    original_count=struct.unpack_from('<I',d,16)[0]
    group_count=struct.unpack_from('<I',d,32)[0]
    table=h-12-group_count*8
    if table<44 or struct.unpack_from('<I',d,table)[0]!=group_count:raise ValueError('Group count mismatch')
    groups=[struct.unpack_from('<II',d,table+4+i*8) for i in range(group_count)]
    n,stride=struct.unpack_from('<II',d,h)
    if stride!=20 or struct.unpack_from('<I',d,h-8)[0]!=8+n*stride:raise ValueError('Vertex extent mismatch')
    end=h+8+n*stride
    if end+4>len(d):raise ValueError('Truncated vertex data')
    size=struct.unpack_from('<I',d,end)[0]
    if end+4+size!=len(d) or size%6:raise ValueError('Index extent mismatch')
    indices=np.frombuffer(d,dtype='<u2',count=size//2,offset=end+4).reshape(-1,3).copy()
    if indices.max()>=n or sum(g[1] for g in groups)!=len(indices):raise ValueError('Group or index count mismatch')
    original={d[44+i*12:56+i*12] for i in range(original_count)}
    if any(d[h+8+i*20:h+20+i*20] not in original for i in range(n)):raise ValueError('Unmatched XYZ')
    vertices=np.frombuffer(d,dtype='<f4',count=n*5,offset=h+8).reshape(-1,5).astype(float)
    if not np.isfinite(vertices).all():raise ValueError('Nonfinite vertex')
    return vertices,indices,groups


def clip_polygon(poly,near=.1):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ia=a[2]>=near;ib=b[2]>=near
        if ia:result.append(a)
        if ia!=ib:result.append(a+(b-a)*((near-a[2])/(b[2]-a[2])))
    return result


def raster(objects,textures,position,basis,fov,flip=False):
    width,height=800,600
    rgb=np.zeros((height,width,3),dtype=np.uint8);rgb[:]=[24,28,36]
    depth=np.full((height,width),np.inf)
    focal=height/(2*math.tan(math.radians(fov)/2));drawn=0
    for obj in objects:
        local=(obj['vertices']-position)@basis.T
        view=np.column_stack((local[:,0],local[:,2],-local[:,1],obj['uv']))
        cursor=0
        for slot,count in obj['groups']:
            tex=textures[slot]
            for tri in obj['triangles'][cursor:cursor+count]:
                poly=clip_polygon([view[i].copy() for i in tri])
                for k in range(1,len(poly)-1):
                    t=np.array([poly[0],poly[k],poly[k+1]])
                    pts=np.column_stack((400+focal*t[:,0]/t[:,2],300-focal*t[:,1]/t[:,2]))
                    x0=max(0,int(np.floor(pts[:,0].min())));x1=min(width,int(np.ceil(pts[:,0].max()))+1)
                    y0=max(0,int(np.floor(pts[:,1].min())));y1=min(height,int(np.ceil(pts[:,1].max()))+1)
                    if x0>=x1 or y0>=y1:continue
                    a,b,c=pts;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
                    if abs(den)<1e-8:continue
                    xx,yy=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5)
                    w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
                    w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w2=1-w0-w1
                    inside=(w0>=-1e-8)&(w1>=-1e-8)&(w2>=-1e-8)
                    inverse=w0/t[0,2]+w1/t[1,2]+w2/t[2,2]
                    safe=np.where(inverse>0,inverse,1)
                    z=1/safe;mask=inside&(inverse>0)&(z<depth[y0:y1,x0:x1])
                    if not mask.any():continue
                    uv=(w0[...,None]*t[0,3:]/t[0,2]+w1[...,None]*t[1,3:]/t[1,2]+w2[...,None]*t[2,3:]/t[2,2])/safe[...,None]
                    if flip:uv[...,1]=1-uv[...,1]
                    uv%=1
                    tx=np.minimum((uv[...,0]*tex.shape[1]).astype(int),tex.shape[1]-1)
                    ty=np.minimum((uv[...,1]*tex.shape[0]).astype(int),tex.shape[0]-1)
                    samples=tex[ty,tx];mask&=samples[...,3]>=128
                    rgb[y0:y1,x0:x1][mask]=samples[...,:3][mask]
                    depth[y0:y1,x0:x1][mask]=z[mask];drawn+=1
            cursor+=count
    return Image.fromarray(rgb),int(np.isfinite(depth).sum()),drawn


def export(source,out):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_HASH:raise ValueError('Unsupported source')
    by={r['key']:r for r in records(raw)}
    def payload(key):
        r=by[key];return raw[r['offset']+12:r['end']]
    def transform(key):
        d=payload(key);n=struct.unpack_from('<I',d,16)[0];f=np.array(struct.unpack_from('<15f',d,30+n))
        return np.array([f[:3],f[4:7],f[8:11]]),f[12:15],f[[3,7,11]]
    objects=[];evidence=[]
    for name,key,mesh,h in LANDMARKS:
        v,tri,groups=mesh_groups(payload(mesh),h);basis,pos,extra=transform(key)
        if not np.array_equal(basis,np.eye(3)) or extra.any():raise ValueError('Unsupported object basis')
        objects.append(dict(name=name,vertices=v[:,:3]+pos,uv=v[:,3:],triangles=tri,groups=groups))
        evidence.append(dict(name=name,key=key,mesh=mesh,record_offset=by[mesh]['offset'],header_offset=h,
                             vertices=len(v),triangles=len(tri),groups=groups,translation=pos.tolist()))
    out.mkdir(parents=True,exist_ok=False)
    keys=struct.unpack_from('<35I',payload('0x30000CB3'),12);textures={};texture_info=[]
    for slot in sorted({g[0] for obj in objects for g in obj['groups']}):
        material_key=f'0x{keys[slot]:08X}';m=payload(material_key)
        if len(m)!=48:raise ValueError('Unsupported material candidate')
        key=f'0x{struct.unpack_from("<I",m,44)[0]:08X}';d=payload(key)
        fmt,w,h=struct.unpack_from('<III',d,40)
        supported=fmt in (5,7) and (w,h)==struct.unpack_from('<HH',d,12)
        if supported:
            codec,block=(1,8) if fmt==5 else (3,16);size=((w+3)//4)*((h+3)//4)*block
            offset=60 if fmt==5 else 56
            if fmt==5 and d[56:60]!=bytes.fromhex('000000c0'):raise ValueError('Unexpected BC1 prefix')
            if offset+size>len(d):raise ValueError('Truncated texture candidate')
            image=Image.frombytes('RGBA',(w,h),d[offset:offset+size],'bcn',codec)
            image.save(out/f'texture-slot-{slot}.png');textures[slot]=np.asarray(image)
            header=[124,0x81007,h,w,size,0,1]+[0]*11+[32,4,int.from_bytes(b'DXT1' if codec==1 else b'DXT5','little'),0,0,0,0,0]+[0x1000,0,0,0,0]
            (out/f'texture-slot-{slot}.dds').write_bytes(b'DDS '+struct.pack('<31I',*header)+d[offset:offset+size])
        else:textures[slot]=np.array([[[230,40,180,255]]],dtype=np.uint8)
        texture_info.append(dict(slot=slot,material=material_key,texture=key,format_word=fmt,width=w,height=h,supported_candidate=supported))
    lines=['# Candidate landmark assembly with local translations; UVs retained, materials unassigned'];base=1
    for obj in objects:
        lines+=['o '+obj['name']]+['v '+' '.join(map(str,v)) for v in obj['vertices']]
        lines+=['vt '+' '.join(map(str,v)) for v in obj['uv']]
        lines+=['f '+' '.join(f'{i+base}/{i+base}' for i in t) for t in obj['triangles']];base+=len(obj['vertices'])
    (out/'landmarks.obj').write_text('\n'.join(lines)+'\n',encoding='ascii')
    cameras=[];sheet=Image.new('RGB',(1600,1800))
    for row,(name,key) in enumerate([('Camera02','0x30000CF0'),('Balcony','0x30000D63'),('Alternate','0x3C00144D')]):
        basis,pos,_=transform(key)
        for col,flip in enumerate([False,True]):
            image,coverage,drawn=raster(objects,textures,pos,basis,60,flip)
            ImageDraw.Draw(image).text((15,12),f'{name} / V {"flipped" if flip else "unchanged"} / test FOV 60 / unlit',fill='white',font_size=18)
            filename=f'{name}-v{int(flip)}.png';image.save(out/filename);sheet.paste(image,(col*800,row*600))
            cameras.append(dict(name=name,key=key,flip_v=flip,fov=60,coverage=coverage,rasterized_triangles=drawn,image=filename))
    sheet.save(out/'camera-comparison.png')
    report=dict(source_sha256=SOURCE_HASH,objects=evidence,textures=texture_info,views=cameras,
                limitations=['Zero-based material selection inferred','Texture format words 5/7 interpreted as BC1/BC3 on this sample',
                'UV repeat, nearest sampling, alpha threshold 128 and no lighting are diagnostic choices',
                'Magenta marks unsupported texture formats','No fog, animation or original material modulation',
                'Basis rows, forward -Y, shared translation space and 60-degree vertical FOV are hypotheses'])
    (out/'landmarks.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)

