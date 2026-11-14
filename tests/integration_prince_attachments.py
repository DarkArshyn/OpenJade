"""Validate source attachment transforms against independent native palette captures."""
import argparse
import json
from pathlib import Path
import struct
import numpy as np
from prince_resources import Resources
from prince_animation import node
from prince_attachments import holder_world, dagger_local


def bone_matrix(constants, component, key):
    index=next(i for i,b in enumerate(component['bindings']) if b['key']==key)
    bone=component['geometry']['bones'][index]
    palette=np.eye(4);palette[:,:3]=constants[42+3*bone['index']:45+3*bone['index']].T
    return np.linalg.inv(bone['inverse_bind'])@palette


def verify(sources,capture):
    resources=Resources(sources)
    body_source=resources.component(0x1300695C)
    legs_source=resources.component(0x1300695F)
    holder_source=resources.component(0x3F000E24)
    holder_bones=holder_world(resources)
    sword_local,_,_=node(resources,0x3F000E3C)
    dagger=dagger_local(resources)
    mapping={int(o,16):k.upper() for o,k,n in (line.split() for line in (capture/(capture.name+'-bindings.txt')).read_text().splitlines())}
    raw=(capture/(capture.name+'-draws.bin')).read_bytes()
    if len(raw)%4116:raise ValueError('Truncated native palettes')
    selected={'33001050','13008426','13008425','3F000E05','057CC7F4'};frames={}
    for off in range(0,len(raw),4116):
        frame,obj,_,_,_=struct.unpack_from('<5I',raw,off);key=mapping[obj]
        if key in selected:
            frames.setdefault(frame,{}).setdefault(key,np.frombuffer(raw,'<f4',count=1024,offset=off+20).astype(float).reshape(256,4))
    result=[]
    for frame,cs in sorted(frames.items()):
        if set(cs)!=selected:raise ValueError('Incomplete native frame')
        body=cs['13008426'];inverse_view=np.linalg.inv(body[4:8].T)
        spine=bone_matrix(body,body_source,'130035BE')
        sheath=bone_matrix(cs['13008425'],legs_source,'130035EE')
        sword_actual=cs['33001050'][4:8].T@inverse_view
        holder_actual=cs['3F000E05'][4:8].T@inverse_view
        dagger_actual=cs['057CC7F4'][4:8].T@inverse_view
        joint_error=0.
        for b,link in zip(holder_source['geometry']['bones'],holder_source['bindings']):
            expected=b['inverse_bind']@holder_bones[int(link['key'],16)]
            palette=np.eye(4);palette[:,:3]=cs['3F000E05'][42+3*b['index']:45+3*b['index']].T
            joint_error=max(joint_error,float(abs(expected-palette).max()))
        result.append(dict(frame=frame,sword_max_error=float(abs(sword_actual-sword_local@spine).max()),
                           holder_max_error=float(abs(holder_actual-spine).max()),holder_joints_max_error=joint_error,
                           dagger_with_native_sheath_max_error=float(abs(dagger_actual-dagger@sheath).max())))
    assert len(result)>=3
    for label in ('sword_max_error','holder_max_error','holder_joints_max_error'):
        assert max(row[label] for row in result)<1e-5,label
    assert max(row['dagger_with_native_sheath_max_error'] for row in result)<5e-5
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--sources',type=Path,nargs='+',required=True)
    a=p.parse_args();result=verify(a.sources,a.capture)
    a.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
