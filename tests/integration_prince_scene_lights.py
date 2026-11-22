from pathlib import Path
import sys,struct,json,hashlib
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from prince_resources import Resources
from prince_scene_lights import decode,parameters
import argparse
p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('capture',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();source=a.source
r=Resources([source]);lights=decode(r)
folder=a.capture;p=folder.name
trans=list(struct.iter_unpack('<2I35f',(folder/f'{p}-transfer.bin').read_bytes()))
raw=(folder/f'{p}-draws.bin').read_bytes();draws={}
for at in range(0,len(raw),4116):
 h=struct.unpack_from('<5I',raw,at);draws.setdefault(h[:2],[]).append(np.frombuffer(raw,'<f4',1024,at+20).reshape(256,4))
errors=dict(direction=0.,position=0.,color=0.,attenuation=0.);count=0
for row in trans:
 inv=np.array(row[5:21]).reshape(4,4);inv[3,3]=1
 gpu=np.array(row[21:37]).reshape(4,4)
 v=parameters(r,np.linalg.inv(inv),np.zeros(31))
 for c in draws[row[:2]]:
  count+=1
  d=v[3:6]@gpu[:3,:3];d/=np.linalg.norm(d)
  errors['direction']=max(errors['direction'],float(abs(d-c[27,:3]).max()))
  for offset,register in [(15,30),(23,34)]:
   pos=(np.r_[v[offset:offset+3],1]@gpu)[:3]
   errors['position']=max(errors['position'],float(abs(pos-c[register,:3]).max()))
   errors['attenuation']=max(errors['attenuation'],float(abs(v[offset+6:offset+8]-c[register+3,:2]).max()))
  for offset,register in [(0,25),(6,28),(18,32),(26,36)]:
   errors['color']=max(errors['color'],float(abs(v[offset:offset+3]-c[register,:3]).max()))
assert count==506 and len(trans)==121
assert errors['direction']<3e-7 and errors['position']<3e-6 and errors['color']<1e-7 and errors['attenuation']<1e-7,errors
report=dict(samples=len(trans),draws=count,max_errors=errors,sources=r.sources,resources=r.used,
            limitations=['Fixed-menu captures only; Camera02 transition not measured.', 'Generated direction/color remain capture-derived.'])
out=a.output;out.mkdir(exist_ok=True)
(out/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
