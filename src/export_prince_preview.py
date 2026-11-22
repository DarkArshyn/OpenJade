"""Rebuild the captured Prince pose using original geometry, UVs, weights and textures.

Capture metadata and shader constants still supply pose and lighting. Captured vertex,
index and texture buffers are never used to generate the scene.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np
from PIL import Image
from prince_resources import Resources, COMPONENTS, material_slot
from replay_actor_vertex_shader import formula


def capture_draws(folder):
    mapping={}
    for line in (folder/(folder.name+'-bindings.txt')).read_text().splitlines():
        obj,key,_=line.split()
        if obj in mapping and mapping[obj]!=key.upper():raise ValueError('Ambiguous captured object binding')
        mapping[obj]=key.upper()
    rows=[]
    for path in sorted(folder.glob(folder.name+'-draw-*.txt')):
        lines=path.read_text().splitlines()
        if 'target 800 600 21' not in lines:continue
        h=lines[0].split();states={};tss={}
        for line in lines:
            a=line.split()
            if a[0]=='state':states[int(a[1])]=int(a[2])
            elif a[0]=='tss':tss[int(a[1]),int(a[2])]=int(a[3])
        if int(h[11])!=1:raise ValueError('Unsupported non-indexed actor draw')
        constants=np.frombuffer(path.with_suffix('.constants').read_bytes(),dtype='<f4').astype(float).reshape(256,4)
        if not np.isfinite(constants).all():raise ValueError('Invalid captured constants')
        rows.append(dict(path=path,mesh=mapping[h[1]],count=int(h[3]),constants=constants,states=states,tss=tss))
    return rows


def deform(mesh, constants):
    positions=[];colors=[]
    for i,p in enumerate(mesh['position']):
        point=np.r_[p,1.];normal=np.r_[mesh['normals'][i],1.]
        inputs=dict(v0=point,v2=normal)
        if mesh['weights'] is not None:
            ids=np.flatnonzero(mesh['weights'][i]);weights=mesh['weights'][i,ids]
            indices=np.zeros(4);ww=np.zeros(4);indices[:len(ids)]=ids*3;ww[:len(ids)]=weights
            inputs.update(v1=ww,v7=indices)
            bone=sum(w*constants[42+3*j:45+3*j] for j,w in zip(ids,weights))
            posed=np.r_[bone@point,1.]
        else:posed=point
        positions.append((constants[4:8]@posed)[:3])
        color,_=formula(inputs,constants);colors.append(np.clip(color,0,1))
    return np.array(positions),np.array(colors)


def export(sources,capture,output,yaw=0.):
    if output.resolve().is_relative_to(Path(__file__).resolve().parents[1]/'game'):
        raise ValueError('The original game directory is read-only')
    if not math.isfinite(yaw):raise ValueError('Camera yaw must be finite')
    if output.exists():raise FileExistsError(output)
    resources=Resources(sources)
    components=[resources.component(key) for key in COMPONENTS]
    by={c['mesh'][2:]:c for c in components};rows=capture_draws(capture)
    if not rows:raise ValueError('No main-target actor draws')
    # Use the body frame as a shared model coordinate system; do not move pieces by eye.
    body=next(r for r in rows if r['mesh']=='13008426')
    inverse_view=np.linalg.inv(body['constants'][4:8])
    pending={key:list(c['geometry']['groups']) for key,c in by.items()}
    textures={};texture_info=[];vertices=[];draws=[];evidence=[];warnings=[];reflection=None
    texture_cache={}
    for row in rows:
        c=by[row['mesh']];mesh=c['geometry'];groups=pending[row['mesh']]
        if not groups or groups[0]['count']!=row['count']:raise ValueError('Capture order/count differs from original face groups')
        group=groups.pop(0);slot=group['slot']
        resolved_slot=material_slot(c['materials'],slot)
        material_key=c['materials'][resolved_slot]
        material=resources.get(material_key)
        if len(material) not in (48,72) or struct.unpack_from('<2I',material)!=(5,6):raise ValueError('Unsupported actor material')
        tk=struct.unpack_from('<I',material,44)[0]
        if tk not in textures:
            levels,info=resources.texture(tk);textures[tk]=len(textures);texture_cache[tk]=levels[0];texture_info.append(info)
        pos,color=deform(mesh,row['constants'])
        pos=(np.c_[pos,np.ones(len(pos))]@inverse_view.T)[:,:3]
        tss=row['tss'];state=row['states'];gain=2. if tss[0,1]==5 else 1.
        if tss[0,1] not in (4,5):raise ValueError('Unsupported color operation')
        if tss[0,3]==3:
            color[:]=[(state[60]>>s&255)/255 for s in (16,8,0)]
        elif tss[0,3]!=0:raise ValueError('Unsupported color source')
        alpha=1.
        if tss[0,4]==4 and tss[0,6]==3:alpha=(state[60]>>24)/255
        elif tss[0,4] not in (2,4):raise ValueError('Unsupported alpha operation')
        if row['path'].with_suffix('.ps').exists():
            reflection_key=struct.unpack_from('<I',material,68)[0]
            if reflection_key not in textures:
                levels,info=resources.texture(reflection_key)
                textures[reflection_key]=len(textures);texture_cache[reflection_key]=levels[0];texture_info.append(info)
            # Packed material color is independently matched to native pixel constant K.
            packed=struct.unpack_from('<I',material,8)[0]
            tint=[(packed>>shift&255)/255 for shift in (0,8,16)]
            reflection=(len(vertices),group['count']*3,textures[reflection_key],*tint)
        blend=0
        if state[27]:
            if (state[19],state[20])!=(5,6):raise ValueError('Unsupported blend factors')
            blend=8 if state[14] else 1
        elif not state[14]:raise ValueError('Unsupported opaque depth state')
        face=mesh['faces'][group['first']:group['first']+group['count']]
        vi=face[:,:3].ravel();ui=face[:,3:6].ravel();uv=mesh['uv'][ui]
        first=len(vertices)
        vertices.extend(np.c_[pos[vi],uv,color[vi],np.full(len(vi),textures[tk])].tolist())
        draws.append((first,len(vi),blend,1 if state[14] else 0,[1.,1.,0.,0.,alpha,gain,0.,1.]))
        evidence.append(dict(component=c['name'],mesh=c['mesh'],source_slot=slot,resolved_slot=resolved_slot,triangles=group['count'],
                             material=f'{material_key:08X}',texture=f'{tk:08X}',native_depth_write=state[14],
                             blend=blend,alpha=alpha,capture=row['path'].name,
                             metadata_sha256=hashlib.sha256(row['path'].read_bytes()).hexdigest(),
                             constants_sha256=hashlib.sha256(row['path'].with_suffix('.constants').read_bytes()).hexdigest()))
    array=np.asarray(vertices,dtype='<f4');lo=array[:,:3].min(0);hi=array[:,:3].max(0);center=(lo+hi)/2
    # Diagnostic camera framing is separate from all original geometry and pose data.
    angle=math.radians(yaw);forward=np.array([math.sin(angle),math.cos(angle),0.]);right=np.cross(forward,[0,0,1.]);up=np.array([0.,0.,1.])
    radius=float(np.linalg.norm(hi-lo)/2);distance=radius/math.sin(math.radians(22.5))*1.12
    eye=center-forward*distance;camera=[*eye,*right,*up,*forward,45.]
    width=max(a.shape[1] for a in texture_cache.values());height=max(a.shape[0] for a in texture_cache.values())
    pixels=np.zeros((len(textures),height,width,4),dtype=np.uint8);sizes=[]
    for key,layer in textures.items():
        image=texture_cache[key];h,w=image.shape[:2];pixels[layer,:h,:w]=image;sizes.append((w,h))
    blob=bytearray(b'OJSCN003')+struct.pack('<4I13f',len(vertices),width,height,len(textures),*camera)
    blob+=array.tobytes()+pixels.tobytes()+struct.pack('<I',len(draws))
    for first,count,blend,write,params in draws:blob+=struct.pack('<4I8f',first,count,blend,write,*params)
    for w,h in sizes:blob+=struct.pack('<2I',w,h)
    excluded=[dict(component=by[key]['name'],groups=groups,reason='No draw observed in the captured initial main-target frame') for key,groups in pending.items() if groups]
    report=dict(reflection=reflection,capture_bindings_sha256=hashlib.sha256((capture/(capture.name+'-bindings.txt')).read_bytes()).hexdigest(),
                sources=resources.sources,resource_records=resources.used,texture_info=texture_info,
                components_rendered=len({e['component'] for e in evidence}),triangles=len(vertices)//3,draws=evidence,
                excluded=excluded,bounds=[lo.tolist(),hi.tolist()],camera=camera,
                scene_sha256=hashlib.sha256(blob).hexdigest(),
                limitations=list(dict.fromkeys(warnings))+[
                    'Frozen native pose and lighting constants; runtime skeletal animation is not implemented.',
                    'Geometry, UVs, normals, packed skin weights and texture pixels are loaded only from original resources.',
                    'Base texture levels only; no menu fog, scene integration or native camera in this close-up.',
                    'No full-character native pixel comparison yet; alpha-test state and reflection fidelity remain to be verified.'])
    output.mkdir(parents=True)
    (output/'prince.ojscene').write_bytes(blob)
    for k,a in texture_cache.items():Image.fromarray(a).save(output/f'texture-{k:08X}.png')
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--sources',type=Path,nargs='+',required=True);p.add_argument('--yaw',type=float,default=0.)
    a=p.parse_args();r=export(a.sources,a.capture,a.output,a.yaw)
    print(json.dumps({k:r[k] for k in ('components_rendered','triangles','excluded','limitations')},indent=2))

