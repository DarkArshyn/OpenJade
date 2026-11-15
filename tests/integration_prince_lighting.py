"""Write independent formula references for animated actor normals and positions."""
import argparse,json,struct
from pathlib import Path
import numpy as np
from prince_resources import Resources
from prince_animation import Skeleton
from prince_sheath import configuration,world
from replay_actor_vertex_shader import formula

def references(sources,package):
    resources=Resources(sources);skeleton=Skeleton(resources);config=configuration(resources)
    data=(package/'prince.actor').read_bytes();nb,nt,nv=struct.unpack_from('<3I',data,8);at=28+nb*68
    for _ in range(nt):_,_,nk=struct.unpack_from('<3I',data,at);at+=12+nk*20
    weights=[]
    for _ in range(nv):
        index,count=struct.unpack_from('<2I',data,at);at+=8;row=[]
        for _ in range(count):bone,weight,x,y,z=struct.unpack_from('<I4f',data,at);at+=20;row.append((bone,weight,np.array([x,y,z])))
        weights.append((index,row))
    assert at==len(data)
    light=(package/'prince.actorlight').read_bytes();assert light[:8]==b'OJALIT01';assert struct.unpack_from('<I',light,8)[0]==nv
    values=np.frombuffer(light,'<f4',31,12).astype(float);c=np.zeros((256,4));c[4:8]=np.eye(4);c[8:11,:3]=np.eye(3);c[25,:3]=values[:3]
    for off,d,col in [(3,27,28),(9,39,40)]:c[d,:3]=values[off:off+3];c[col,:3]=values[off+3:off+6]
    for off,p,col,a in [(15,30,32,33),(23,34,36,37)]:c[p,:3]=values[off:off+3];c[col,:3]=values[off+3:off+6];c[a,:2]=values[off+6:off+8]
    at=136;normals=[]
    for _,row in weights:
        active=struct.unpack_from('<I',light,at)[0];at+=4
        if active:
            normals.append(np.frombuffer(light,'<f4',len(row)*3,at).reshape(-1,3));at+=len(row)*12
        else:normals.append(None)
    assert at==len(light)
    times=[0.,.5,1.,1.7,2.,3.,4.];out=bytearray(b'OJCLR001')+struct.pack('<2I',len(times),nv);colors=[]
    for time in times:
        matrices=world(skeleton,config,float(np.float32(time)));out+=struct.pack('<f',time);frame=[]
        for (_,row),ns in zip(weights,normals):
            color=np.array([-1.,-1.,-1.])
            if ns is not None:
                p=sum(w*(np.r_[point,1.]@matrices[b])[:3] for b,w,point in row)
                n=sum(w*(normal@matrices[b][:3,:3]) for (b,w,_),normal in zip(row,ns))
                color=np.clip(formula(dict(v0=np.r_[p,1.],v2=np.r_[n,1.]),c)[0],0,1)
            frame.append(color);out+=struct.pack('<3f',*color)
        colors.append(np.array(frame))
    (package/'prince.lightingposes').write_bytes(out)
    difference=float(abs(colors[0]-colors[4]).max());assert difference>1e-3
    return dict(times=times,vertices=nv,fixed_material_vertices=sum(n is None for n in normals),max_animated_rgb_change=difference,scope='CPU formula reference; not original-game pixel parity.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('package',type=Path);p.add_argument('--sources',type=Path,nargs='+',required=True);a=p.parse_args();print(json.dumps(references(a.sources,a.package),indent=2))
