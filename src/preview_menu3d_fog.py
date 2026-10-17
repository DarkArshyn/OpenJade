"""Fixed-sample fog UV/translation experiment; no original camera assumed."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from probe_menu3d import records


def render(vertices,uv,triangles,texture,repeat,flip):
    # Orthographic YZ diagnostic view. X curvature is retained in the OBJ only.
    yz=vertices[:,1:3]
    low=yz.min(axis=0);span=np.ptp(yz,axis=0)
    scale=min(700/span[0],200/span[1])
    points=(yz-low)*scale
    points[:,0]+=30;points[:,1]=240-points[:,1]
    pixels=np.zeros((290,760,4),dtype=np.uint8)
    covered=np.zeros((290,760),dtype=bool)
    for tri in triangles:
        a,b,c=points[tri]
        x0=max(0,int(np.floor(min(a[0],b[0],c[0]))));x1=min(760,int(np.ceil(max(a[0],b[0],c[0])))+1)
        y0=max(0,int(np.floor(min(a[1],b[1],c[1]))));y1=min(290,int(np.ceil(max(a[1],b[1],c[1])))+1)
        xx,yy=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5)
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-8:raise ValueError('Degenerate diagnostic projection')
        w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
        w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den
        w2=1-w0-w1;mask=(w0>=-1e-8)&(w1>=-1e-8)&(w2>=-1e-8)
        coords=w0[...,None]*uv[tri[0]]+w1[...,None]*uv[tri[1]]+w2[...,None]*uv[tri[2]]
        if flip:coords[...,1]=1-coords[...,1]
        coords=coords%1 if repeat else np.clip(coords,0,1)
        # Nearest-neighbor sampling is a diagnostic choice, not inferred filtering.
        tx=np.minimum((coords[...,0]*texture.shape[1]).astype(int),texture.shape[1]-1)
        ty=np.minimum((coords[...,1]*texture.shape[0]).astype(int),texture.shape[0]-1)
        pixels[y0:y1,x0:x1][mask]=texture[ty,tx][mask]
        covered[y0:y1,x0:x1]|=mask
    if not covered.any():raise ValueError('Empty raster')
    foreground=Image.fromarray(pixels)
    image=Image.new('RGBA',foreground.size,'#202935');image.alpha_composite(foreground)
    draw=ImageDraw.Draw(image)
    for tri in triangles:draw.line([tuple(points[i]) for i in [*tri,tri[0]]],fill='#8e9ba8',width=1)
    draw.text((24,12),('Repeat' if repeat else 'Clamp')+(' / V flipped' if flip else ' / V unchanged'),fill='white',font_size=18)
    return image,int(covered.sum())


def export(source,texture_path,out):
    raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if digest!='96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb':raise ValueError('Unsupported source')
    by={r['key']:r for r in records(raw)}
    def payload(key):
        r=by[key];return raw[r['offset']+12:r['end']]
    mesh=payload('0x30000C7A');obj=payload('0x30000CC7')
    v=np.array([struct.unpack_from('<5f',mesh,416+i*20) for i in range(10)],dtype=np.float64)
    original_uv=np.array([struct.unpack_from('<2f',mesh,164+i*8) for i in range(10)])
    if not np.array_equal(v[:,3:],original_uv):raise ValueError('UV copies disagree')
    if not np.isfinite(v).all():raise ValueError('Nonfinite coordinates')
    triangles=np.array(struct.unpack_from('<24H',mesh,620)).reshape(-1,3)
    n=struct.unpack_from('<I',obj,16)[0];offset=30+n
    f=np.array(struct.unpack_from('<15f',obj,offset));basis=np.array([f[0:3],f[4:7],f[8:11]])
    if not np.array_equal(basis,np.eye(3)):raise ValueError('This sample expects identity basis')
    position=f[12:15];world=v[:,:3]@basis+position
    if not np.allclose(world-world[0],v[:,:3]-v[0,:3],rtol=0,atol=1e-12):raise ValueError('Translation changed relative geometry')
    texture=np.asarray(Image.open(texture_path).convert('RGBA'))
    rgba_hash=hashlib.sha256(texture.tobytes()).hexdigest()
    if rgba_hash!='506716bfadb7ebe329b84d90ae402cb774d970898394f609d1bb4432c596df50':raise ValueError('Unexpected texture pixels')
    out.mkdir(parents=True,exist_ok=False)
    sheet=Image.new('RGBA',(1520,580),'#202935');coverage=[]
    for i,(repeat,flip) in enumerate([(True,False),(True,True),(False,False),(False,True)]):
        image,count=render(v[:,:3],v[:,3:],triangles,texture,repeat,flip)
        transformed,_=render(world,v[:,3:],triangles,texture,repeat,flip)
        if image.tobytes()!=transformed.tobytes():raise ValueError('Centered translation raster mismatch')
        image.save(out/f'variant-{i}.png');sheet.paste(image,((i%2)*760,(i//2)*290));coverage.append(count)
    sheet.convert('RGB').save(out/'comparison.png')
    for label,vertices in [('local',v[:,:3]),('translated-candidate',world)]:
        lines=['# Fog geometry with candidate UVs; no texture sampler convention asserted']
        lines+=['v '+' '.join(format(x,'.12g') for x in row) for row in vertices]
        lines+=['vt '+' '.join(format(x,'.12g') for x in row) for row in v[:,3:]]
        lines+=['f '+' '.join(f'{i+1}/{i+1}' for i in tri) for tri in triangles]
        (out/(label+'.obj')).write_text('\n'.join(lines)+'\n',encoding='ascii')
    report=dict(source_sha256=digest,texture_rgba_sha256=rgba_hash,uv_payload_offset=164,interleaved_uv_offset=428,
                uv_copies_exact=True,uv_range=[v[:,3:].min(axis=0).tolist(),v[:,3:].max(axis=0).tolist()],
                transform_payload_offset=offset,basis=basis.tolist(),translation_candidate=position.tolist(),
                opaque_next_word=obj[offset+60:offset+64].hex(),local_bounds=[v[:,:3].min(axis=0).tolist(),v[:,:3].max(axis=0).tolist()],
                translated_bounds=[world.min(axis=0).tolist(),world.max(axis=0).tolist()],coverage=coverage,
                limitations=['UV role strongly supported, sampler mode and V direction unverified','Local versus global transform space unresolved',
                             'Identity basis cannot distinguish row/column conventions','Diagnostic orthographic YZ view; not original camera',
                             'No original blend mode, lighting, animation, depth or material modulation applied'])
    (out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','texture','output'):p.add_argument(name,type=Path)
    a=p.parse_args();export(a.source,a.texture,a.output)
