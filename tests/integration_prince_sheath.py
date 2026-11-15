"""Validate original sheath parameters and independent dynamics against native updates."""
import argparse,json,struct,hashlib
from pathlib import Path
import numpy as np
from prince_resources import Resources
from prince_sheath import configuration,advance,matrix

def verify(sources,capture):
    config=configuration(Resources(sources));data=capture.read_bytes()
    if len(data)%552:raise ValueError('Truncated sheath capture')
    errors=[];frames=[]
    for at in range(0,len(data),552):
        record=data[at:at+552];sequence,frame,ready,pointer,owner,dt=struct.unpack_from('<5If',record)
        before=np.frombuffer(record,'<f4',20,24).astype(float)
        if before[7]!=-30:continue
        after=np.frombuffer(record,'<f4',20,308).astype(float)
        rest=np.frombuffer(record,'<f4',16,172).reshape(4,4).astype(float)
        parent=np.frombuffer(record,'<f4',16,240).reshape(4,4).astype(float)
        output=np.frombuffer(record,'<f4',16,388).reshape(4,4).astype(float)
        planes=np.frombuffer(record,'<f4',24,456).reshape(2,4,3)
        assert np.array_equal(planes,config['planes'])
        assert abs(before[1]-config['length'])<1e-7
        assert before[2]==config['inertia'] and before[3]==config['response']
        assert np.array_equal(before[5:8],config['gravity'])
        p,v=advance(config,before[11:14],before[14:17],before[8:11],parent,dt)
        expected=matrix(after[11:14],rest,parent)
        errors.append([float(abs(p-after[11:14]).max()),float(abs(v-after[14:17]).max()),float(abs(expected-output).max())]);frames.append(frame)
    assert len(errors)>=100 and len(set(frames))>=100
    maxima=np.max(errors,axis=0);assert np.all(maxima<[1e-5,0.002,5e-5]),maxima
    return dict(samples=len(errors),max_position_error=maxima[0],max_velocity_error=maxima[1],max_matrix_error=maxima[2],
                capture_sha256=hashlib.sha256(data).hexdigest(),scope='One-step dynamics on captured parent inputs; not native startup or autonomous trajectory parity.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('--sources',type=Path,nargs='+',required=True)
    a=p.parse_args();report=verify(a.sources,a.capture);a.output.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
