"""Validate receiver origin bindings against original resources and native palettes."""
from pathlib import Path
import struct,json,sys,argparse
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from prince_resources import Resources
from prince_animation import node,Skeleton
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('capture',type=Path);parser.add_argument('manifest',type=Path);parser.add_argument('output',type=Path)
args=parser.parse_args();p=args.capture;prefix=p.name
registry=list(struct.iter_unpack('<5I',(p/f'{prefix}-registry.bin').read_bytes()))
manifest=json.loads(args.manifest.read_text(encoding='utf-8'))
r=Resources([Path(x['path']) for x in manifest['sources']]);sk=Skeleton(r)
refs=list(struct.iter_unpack('<2I6f',(p/f'{prefix}-reference.bin').read_bytes()))
objects={};owners={}
for f in p.glob(prefix+'-object-*.txt'):
 obj=int(f.stem.rsplit('-',1)[1],16);lines={x.split()[0]:x.split()[1:] for x in f.read_text().splitlines() if x.split()}
 for role,cb,target in [('mesh',0x43f120,objects),('owner',0x67df50,owners)]:
  pointer=int(lines[role][0],16);keys={k for k,_,c,_,v in registry if v==pointer and c==cb};assert len(keys)==1;target[obj]=keys.pop()
components={int(c['mesh'],16):c for c in (r.component(k) for k in __import__('prince_resources').COMPONENTS)}
raw=(p/f'{prefix}-draws.bin').read_bytes();frames={};shared=0.
for off in range(0,len(raw),4116):
 frame,obj,*_=struct.unpack_from('<5I',raw,off);c=components[objects[obj]]
 if not c['name'].startswith('M_Prince_'):continue
 const=np.frombuffer(raw,'<f4',1024,off+20).reshape(256,4);obs=frames.setdefault(frame,{})
 for b,link in zip(c['geometry']['bones'],c['bindings']):
  key=int(link['key'],16);m=np.eye(4);m[:,:3]=const[42+3*b['index']:45+3*b['index']].T
  world=np.linalg.inv(b['inverse_bind'])@m
  if key in obs:shared=max(shared,float(abs(world-obs[key]).max()))
  obs[key]=world
trans=list(struct.iter_unpack('<2I35f',(p/f'{prefix}-transfer.bin').read_bytes()))
roots={}
for t in trans:
 if objects[t[1]]==0x13008426:
  m=np.array(t[5:21]).reshape(4,4);m[3,3]=1;roots[t[0]]=np.linalg.inv(m)
errors={};counts={};details=[]
for ref in refs:
 frame,obj=ref[:2];owner=owners[obj];actual=np.array(ref[2:5]);root=roots[frame]
 for label,expected in [('root',root[3,:3]),('spine2',(frames[frame][0x130035be]@root)[3,:3]),('head',(frames[frame][0x130035c0]@root)[3,:3]),('face-local',(node(r,0x13005eea)[0]@frames[frame][0x130035c0]@root)[3,:3])]:
  name=f'{owner:08X}/{label}';error=float(abs(expected-actual).max());errors[name]=max(errors.get(name,0),error)
 counts[f'{owner:08X}']=counts.get(f'{owner:08X}',0)+1
print('counts',counts,'shared',shared);print(json.dumps(errors,indent=2))


assert counts=={'CC000431':2475,'3F000E2F':275,'330005EC':275}
assert shared<1e-6
for key in ['CC000431/root','3F000E2F/spine2','330005EC/head']:assert errors[key]<7e-6
assert errors['3F000E2F/head']>.2 and errors['330005EC/spine2']>.2

args.output.write_text(json.dumps(dict(errors=errors,counts=counts,shared=shared,sources=r.sources,resources=r.used),indent=2),encoding='utf-8')
