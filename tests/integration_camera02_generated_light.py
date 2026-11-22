"""Verify a complete native Camera02 generated-light capture; read-only inputs."""
from pathlib import Path
import struct,json,math,hashlib
import numpy as np

def verify(capture):
    p=capture;prefix=p.name
    def rows(suffix,fmt):
     raw=(p/f'{prefix}-{suffix}').read_bytes();assert len(raw)%struct.calcsize(fmt)==0
     return list(struct.iter_unpack(fmt,raw))
    direction=rows('direction.bin','<3I8f');transfer=rows('transfer.bin','<2I35f');reference=rows('reference.bin','<2I6f')
    assert [r[:2] for r in direction]==[r[:2] for r in transfer]==[r[:2] for r in reference]
    raw=(p/f'{prefix}-draws.bin').read_bytes();assert len(raw)%4116==0
    draws={}
    for at in range(0,len(raw),4116):
     h=struct.unpack_from('<5I',raw,at);c=np.frombuffer(raw,'<f4',1024,at+20).reshape(256,4)
     draws.setdefault(h[:2],[]).append(c)
    clock=np.frombuffer((p/f'{prefix}-clock.bin').read_bytes(),'<f4');times=np.r_[0,np.cumsum(clock.astype(float))]
    errors={k:0. for k in ['input','formula','local','gpu','color','camera_reference']};details=[]
    for d,t,ref in zip(direction,transfer,reference):
     frame,obj,color,*v=d;input=np.array(v[:3]);native=np.array(v[3:6]);azimuth,polar=v[6:]
     owner=np.array(ref[2:5]);camera=np.array(ref[5:8]);delta=owner-camera;delta/=np.linalg.norm(delta)
     inv=np.array(t[5:21]).reshape(4,4);inv[3,3]=1;gpu=np.array(t[21:37]).reshape(4,4)
     view=inv@gpu;derived_camera=np.linalg.inv(view)[3,:3]
     x,y=delta[:2];a=math.atan(y/(x if x else 1e-7))+(math.pi if x<0 else 0)+azimuth
     expected=np.array([math.sin(polar)*math.cos(a),math.sin(polar)*math.sin(a),math.cos(polar)])
     errors['input']=max(errors['input'],float(abs(delta-input).max()))
     errors['formula']=max(errors['formula'],float(abs(expected-native).max()))
     errors['camera_reference']=max(errors['camera_reference'],float(abs(derived_camera-camera).max()))
     local=native@inv[:3,:3]
     errors['local']=max(errors['local'],float(abs(local-np.array(t[2:5])).max()))
     projected=local@gpu[:3,:3];projected/=np.linalg.norm(projected)
     assert color==0x40404040
     for c in draws[(frame,obj)]:
      errors['gpu']=max(errors['gpu'],float(abs(projected-c[39,:3]).max()))
      errors['color']=max(errors['color'],float(abs(c[40]-([64/255]*3+[1])).max()))
     details.append(dict(frame=frame,time=float(times[frame]),object=f'{obj:08X}',owner=owner.tolist(),camera=camera.tolist(),world=native.tolist(),local=local.tolist()))
    
    first=details[0]['camera'];moving=[r for r in details if np.linalg.norm(np.array(r['camera'])-first)>1e-4]
    
    result=dict(errors=errors,samples=len(details),draws=sum(map(len,draws.values())),details=details)
    assert len(details) == 3025 and len(draws) == 3025
    assert sum(map(len, draws.values())) == 12626
    assert len({x['object'] for x in details}) == 11
    for key, limit in dict(input=2e-7, formula=3e-7, local=1e-7, gpu=2e-7, color=1e-7).items():
     assert errors[key] < limit, (key, errors[key])
    registry=rows('registry.bin','<5I')
    selected={};current=None
    for line in (p/f'{prefix}-selected.txt').read_text().splitlines():
     fields=line.split()
     if fields[0]=='receiver':
      assert fields[-2:]==['count','3'];current=(int(fields[1]),int(fields[2],16));assert current not in selected;selected[current]=[]
     elif fields[0]=='light':
      pointer=int(fields[2],16)
      keys={k for k,_,cb,_,value in registry if value==pointer and cb==0x67df50}
      assert len(keys)==1
      selected[current].append(keys.pop())
     else:raise AssertionError('Unexpected selection record')
    assert set(selected)==set(draws)
    assert all(x==[0x30000ce2,0x30000cf4,0x30000d57] for x in selected.values())
    # Use one receiver throughout; never compare local vectors belonging to different meshes.
    track=[x for x in details if x['object']==details[-1]['object']]
    initial=np.array(track[0]['camera']);distances=[np.linalg.norm(np.array(x['camera'])-initial) for x in track]
    endpoint=track[int(np.argmax(distances))]
    assert max(distances)>10, 'No full camera movement captured'
    before=np.array(track[0]['world']);after=np.array(endpoint['world'])
    angle=float(np.degrees(np.arccos(np.clip(np.dot(before,after)/np.linalg.norm(before)/np.linalg.norm(after),-1,1))))
    assert .7<angle<.9
    result.update(selected_lights=['30000CE2','30000CF4','30000D57'],
     world_direction_before=before.tolist(),world_direction_endpoint=after.tolist(),
     tracked_receiver=track[0]['object'],direction_change_degrees=angle,
     diffuse_channel_error_bound=float(np.linalg.norm(after-before)*64/255),
     evidence_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in p.glob(prefix+'-*') if f.is_file()},
     limitations=['Captured context reference is used directly. Inversion of the approximate captured view matrices differs by up to 0.00794 scene unit.',
     'Shader constants verified; no isolated final-pixel ablation during Camera02.',
     'The last capture samples return to the initial camera reference; the cause was not traced.'])
    return result

if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    result=verify(args.capture)
    args.output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='details'},indent=2))
