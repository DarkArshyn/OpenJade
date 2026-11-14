"""Compare independently evaluated source rotations with local GOG palette captures."""
import argparse
import json
from pathlib import Path
import struct
import numpy as np
from prince_resources import Resources, COMPONENTS
from prince_animation import Skeleton, sample
from sample_camera02_animation import quaternion_matrix
from export_prince_animation import influences


def verify(sources, capture, package, output):
    r=Resources(sources);s=Skeleton(r)
    components={c['mesh'][2:]:c for c in (r.component(k) for k in COMPONENTS)}
    bindings={int(o,16):k.upper() for o,k,n in (line.split() for line in (capture/(capture.name+'-bindings.txt')).read_text().splitlines())}
    raw=(capture/(capture.name+'-draws.bin')).read_bytes()
    if len(raw)%4116:raise ValueError('Truncated captured palettes')
    frames={};shared=0.
    for off in range(0,len(raw),4116):
        frame,obj,_,_,_=struct.unpack_from('<5I',raw,off);c=components[bindings[obj]]
        if not c['name'].startswith('M_Prince_'):continue
        const=np.frombuffer(raw,'<f4',count=1024,offset=off+20).reshape(256,4);obs=frames.setdefault(frame,{})
        for b,link in zip(c['geometry']['bones'],c['bindings']):
            key=int(link['key'],16);m=np.eye(4);m[:,:3]=const[42+3*b['index']:45+3*b['index']].T
            world=np.linalg.inv(b['inverse_bind'])@m
            if key in obs:shared=max(shared,float(abs(world-obs[key]).max()))
            obs[key]=world
    rot={t['target']:t for t in s.tracks if t['kind']=='rotation' and t['target']<34}
    targets=sorted(rot);ticks=np.linspace(0,20,2001)
    grid=np.array([[quaternion_matrix(sample(rot[i],t)) for i in targets] for t in ticks])
    clock=np.fromfile(capture/(capture.name+'-clock.bin'),'<f4');measurements=[]
    for frame,obs in sorted(frames.items()):
        matrices=[]
        for i in targets:
            key=s.keys[i];parent=s.nodes[i][1];m=obs[key]@np.linalg.inv(obs[parent]) if parent else obs[key]
            matrices.append(m[:3,:3])
        errors=np.mean((grid-np.array(matrices))**2,axis=(1,2,3));at=np.argmin(errors)
        measurements.append(dict(frame=frame,clock_seconds=float(sum(clock[:frame])),fitted_tick=float(ticks[at]),rotation_rms=float(errors[at]**.5)))
    assert len(measurements)>=3 and shared<1e-5
    assert max(m['rotation_rms'] for m in measurements)<0.0002
    times=[0.,0.5,1.,1.7,2.,3.,4.]
    report=json.loads((package/'manifest.json').read_text());pending={key:list(c['geometry']['groups']) for key,c in components.items()};links=[]
    for draw in report['draws']:
        key=draw['mesh'][2:];c=components[key];group=pending[key].pop(0)
        per_vertex=influences(r,s,c);ids=c['geometry']['faces'][group['first']:group['first']+group['count'],:3].ravel()
        links.extend(per_vertex[i] for i in ids)
    expected=bytearray(struct.pack('<I',len(times)))
    for time in times:
        expected+=struct.pack('<f',time);world=s.world((time*5)%20)
        for weights in links:
            p=sum(weight*(np.r_[point,1.]@world[bone])[:3] for bone,weight,point in weights)
            expected+=struct.pack('<3f',*p)
    (package/'prince.poses').write_bytes(expected)
    result=dict(shared_bone_matrix_max_error=shared,native_pose_samples=measurements,
                source_clip='2D000AD4',primary_bones_compared=34,python_reference_seconds=times,
                limitation='Phase fitted to rotations; this does not prove native action selection, looping or secondary controllers.')
    output.write_text(json.dumps(result,indent=2),encoding='utf-8');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('package',type=Path);p.add_argument('output',type=Path);p.add_argument('--sources',type=Path,nargs='+',required=True)
    a=p.parse_args();print(json.dumps(verify(a.sources,a.capture,a.package,a.output),indent=2))
