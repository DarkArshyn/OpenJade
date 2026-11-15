"""Verify scene assembly preserves scenery and uses source collision grounding."""
import argparse,hashlib,json,struct
from pathlib import Path
import numpy as np
from assemble_prince_balcony import read_scene
from prince_resources import Resources
from prince_ground import grounded_placement

def verify(menu,actor,merged,source,capture):
    old=read_scene(menu);new=read_scene(merged);prince=read_scene(actor);placement,grounding=grounded_placement(Resources([source]))
    encoded=merged.with_suffix('.placement').read_bytes()
    assert encoded[:8]==b'OJAPL001' and len(encoded)==76
    assert struct.unpack_from('<I',encoded,8)[0]==old['nv']
    actual=np.frombuffer(encoded,'<f4',16,12).reshape(4,4)
    assert np.array_equal(actual,placement.astype('<f4'))
    assert new['nv']==old['nv']+prince['nv']
    assert np.array_equal(new['vertices'][:old['nv']],old['vertices'])
    assert new['draws'][:old['nd']]==old['draws'] and new['palms']==old['palms']
    assert new['rates'][:old['nd']*8]==old['rates']
    assert np.array_equal(new['pixels'][:old['nl'],:old['h'],:old['w']],old['pixels'])
    expected=(np.c_[prince['vertices'][:,:3],np.ones(prince['nv'])]@placement)[:,:3]
    error=float(abs(new['vertices'][old['nv']:,:3]-expected).max());assert error<1e-5
    for suffix in ['rain','splash','birds','fog','pollen','fixtures','flight','glow','leaf','trunk','rido1','rido2','rido3','rido4']:
        path=menu.with_suffix('.'+suffix)
        if path.exists():assert path.read_bytes()==merged.with_suffix('.'+suffix).read_bytes(),suffix
    mapping={int(o,16):key for o,key,_ in (line.split() for line in (capture/(capture.name+'-bindings.txt')).read_text().splitlines())}
    data=(capture/(capture.name+'-prepared.bin')).read_bytes();assert len(data)%88==0
    samples=[]
    for at in range(0,len(data),88):
        frame,obj,*_=struct.unpack_from('<6I',data,at)
        if mapping.get(obj)!='13008426':continue
        matrix=np.frombuffer(data,'<f4',16,at+24).reshape(4,4)
        assert abs(matrix[:3,:3]-placement[:3,:3]).max()<1e-6
        assert abs(matrix[3,:2]-placement[3,:2]).max()<1e-6
        samples.append(float(matrix[3,2]-placement[3,2]))
    assert len(samples)>=10
    assert max(abs(x) for x in samples)<1e-6
    return dict(scenery_preserved=True,source_grounded_vertex_error=error,collision=grounding,native_placement_samples=len(samples),native_z_difference_range=[min(samples),max(samples)],scene_sha256=hashlib.sha256(new['raw']).hexdigest(),scope='Checkpoint XY/orientation and source collision height validated against native placements; no continuous collision solver.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('menu','actor','merged','source','capture','output'):p.add_argument(key,type=Path)
    a=p.parse_args();result=verify(a.menu,a.actor,a.merged,a.source,a.capture);a.output.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
