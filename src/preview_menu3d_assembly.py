"""Three-object wireframe assembly and candidate cameras; no game rendering."""
import argparse,hashlib,json,struct,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from probe_menu3d import records


def clip_near(a,b,near=.1):
    a=np.array(a,dtype=float);b=np.array(b,dtype=float)
    if a[2]<near and b[2]<near:return None
    if a[2]<near:a=a+(b-a)*((near-a[2])/(b[2]-a[2]))
    if b[2]<near:b=b+(a-b)*((near-b[2])/(a[2]-b[2]))
    return a,b


def export(source,out):
    raw=source.read_bytes();digest=hashlib.sha256(raw).hexdigest()
    if digest!='96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb':raise ValueError('Unsupported sample')
    by={r['key']:r for r in records(raw)}
    def payload(key):
        r=by[key];return raw[r['offset']+12:r['end']]
    def transform(key):
        d=payload(key);n=struct.unpack_from('<I',d,16)[0]
        f=np.array(struct.unpack_from('<15f',d,30+n))
        return np.array([f[:3],f[4:7],f[8:11]]),f[12:15],f[[3,7,11]]
    objects=[]
    for name,obj,mesh,h,color in [('ground','0x30000CCD','0x30000C80',176,'#bca07a'),
            ('fog','0x30000CC7','0x30000C7A',408,'#84cad9'),('fog2','0x30000CC3','0x30000C76',264,'#b6d477')]:
        d=payload(mesh);n,stride=struct.unpack_from('<II',d,h)
        if stride!=20:raise ValueError('Unsupported stride')
        v=np.array([struct.unpack_from('<5f',d,h+8+i*stride) for i in range(n)])
        if not np.array_equal(v[:,:3],np.array([struct.unpack_from('<3f',d,44+i*12) for i in range(n)])):raise ValueError('XYZ mismatch')
        pos=h+8+n*stride;size=struct.unpack_from('<I',d,pos)[0]
        if pos+4+size!=len(d) or size%6:raise ValueError('Index extent mismatch')
        tris=np.array(struct.unpack_from('<'+'H'*(size//2),d,pos+4)).reshape(-1,3)
        if tris.max()>=n:raise ValueError('Invalid index')
        basis,translation,padding=transform(obj)
        if not np.array_equal(basis,np.eye(3)) or np.any(padding):raise ValueError('Nontrivial transform excluded')
        world=v[:,:3]+translation
        if not np.allclose(world-world[0],v[:,:3]-v[0,:3],atol=1e-12,rtol=0):raise ValueError('Transform mismatch')
        objects.append(dict(name=name,key=obj,mesh=mesh,color=color,vertices=world.tolist(),uv=v[:,3:].tolist(),triangles=tris.tolist()))
    cams=[]
    for name,key,target in [('Camera02','0x30000CF0',None),('Balcony','0x30000D63','0x30000D65'),('Alternate','0x3C00144D','0x3C00144E')]:
        basis,position,_=transform(key)
        if not np.allclose(basis@basis.T,np.eye(3),atol=1e-5):raise ValueError('Nonorthonormal camera')
        cam=dict(name=name,key=key,position=position.tolist(),basis=basis.tolist())
        if target:
            direction=transform(target)[1]-position;direction/=np.linalg.norm(direction)
            cam['target_direction_row_dots']=(basis@direction).tolist()
            cam['negative_y_angle_degrees']=math.degrees(math.acos(np.clip(-basis[1]@direction,-1,1)))
        cams.append(cam)
    out.mkdir(parents=True,exist_ok=False)
    # No material is assigned: transparent ground would otherwise hide evidence.
    lines=['# Candidate translated assembly; local/global hierarchy unverified'];base=1
    for obj in objects:
        lines+=['o '+obj['name']]+['v '+' '.join(map(str,v)) for v in obj['vertices']]
        lines+=['f '+' '.join(str(i+base) for i in tri) for tri in obj['triangles']];base+=len(obj['vertices'])
    (out/'assembly-candidate.obj').write_text('\n'.join(lines)+'\n',encoding='ascii')
    sheet=Image.new('RGB',(1500,900),'#181c24');points=np.concatenate([o['vertices'] for o in objects])
    for j,(a,b,label) in enumerate([(0,1,'XY'),(0,2,'XZ'),(1,2,'YZ')]):
        image=Image.new('RGB',(500,450),'#181c24');draw=ImageDraw.Draw(image)
        low=points[:,[a,b]].min(axis=0);span=np.ptp(points[:,[a,b]],axis=0);scale=min(440/span[0],330/span[1])
        def xy(p):return (30+(p[a]-low[0])*scale,390-(p[b]-low[1])*scale)
        for obj in objects:
            v=obj['vertices']
            for t in obj['triangles']:draw.line([xy(v[i]) for i in [*t,t[0]]],fill=obj['color'],width=2)
        for c in cams:
            x,y=xy(c['position']);draw.ellipse((x-3,y-3,x+3,y+3),fill='white');draw.text((x+5,y),c['name'],fill='white')
        draw.text((20,15),'Candidate placement / '+label,fill='white',font_size=18)
        sheet.paste(image,(j*500,0))
    for j,cam in enumerate(cams):
        image=Image.new('RGB',(500,450),'#181c24');draw=ImageDraw.Draw(image)
        basis=np.array(cam['basis']);position=np.array(cam['position']);depths=[]
        # Diagnostic 60-degree vertical FOV, not a recovered camera parameter.
        focal=400/(2*math.tan(math.radians(60)/2))
        for obj in objects:
            local=(np.array(obj['vertices'])-position)@basis.T
            projected=np.column_stack((local[:,0],local[:,2],-local[:,1]));depths+=projected[:,2].tolist()
            for tri in obj['triangles']:
                for a,b in zip(tri,tri[1:]+tri[:1]):
                    segment=clip_near(projected[a],projected[b])
                    if segment:
                        coords=[(250+focal*p[0]/p[2],240-focal*p[1]/p[2]) for p in segment]
                        draw.line(coords,fill=obj['color'],width=2)
        cam['candidate_depth_range']=[min(depths),max(depths)]
        draw.rectangle((0,0,500,47),fill='#181c24')
        draw.text((20,10),cam['name']+' / forward -Y',fill='white',font_size=18)
        draw.text((20,31),'60 deg vertical FOV is a diagnostic choice',fill='#bca07a')
        image.save(out/(cam['name']+'.png'));sheet.paste(image,(j*500,450))
    sheet.save(out/'assembly-comparison.png')
    report=dict(source_sha256=digest,objects=objects,cameras=cams,excluded=['fake_fog3: nonzero auxiliary transform words'],
                limitations=['Translations treated as common space for this experiment only','No textures or occlusion; wireframe diagnostic',
                'Camera basis rows and forward -Y are hypotheses','FOV 60 degrees and near plane 0.1 are chosen test values','Active game camera unknown'])
    (out/'assembly.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
