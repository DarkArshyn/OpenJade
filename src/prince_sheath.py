"""Source-backed sheathed-dagger diagnostic with independently measured constraints.

The selected menu fixture has no measured external wind contribution. Startup,
action changes and arbitrary external force activation are not reconstructed.
"""
import struct
import numpy as np
from prince_animation import node


def configuration(resources):
    data=resources.get(0x130035EE)
    if len(data)!=415 or struct.unpack_from('<4I',data,271)!=(22,0x1000000,1,2):
        raise ValueError('Unsupported sheath modifier')
    if struct.unpack_from('<I',data,307)[0]!=2 or struct.unpack_from('<fI',data,407)!=(2.,0xffffffff):
        raise ValueError('Unsupported sheath constraints or wind factor')
    initial=node(resources,0x130035EE)[0][3,:3]
    planes=np.frombuffer(data,'<f4',24,311).astype(float).reshape(2,4,3)[:,[0,1,3,2],:]
    return dict(length=float(np.linalg.norm(initial)),inertia=struct.unpack_from('<f',data,287)[0],
                response=struct.unpack_from('<f',data,291)[0],gravity=np.frombuffer(data,'<f4',3,295).astype(float),
                initial=initial,planes=planes)


def encode(config,bone):
    values=[config['length'],config['inertia'],config['response'],*config['gravity'],*config['initial'],*config['planes'].ravel()]
    return b'OJSHT001'+struct.pack('<I33f',bone,*values)


def advance(config,point,velocity,previous,parent,dt):
    if not np.isfinite(dt) or dt<=0:raise ValueError('Invalid sheath time step')
    p=np.array(point,float);v=np.array(velocity,float);direction=p/np.linalg.norm(p)
    project=lambda value,normal:value-np.dot(value,normal)*normal
    delta=(previous-parent[3,:3])@parent[:3,:3].T
    v+=project(delta,direction)*config['inertia']/dt+(config['gravity']@parent[:3,:3].T)*dt
    for a,b,soft_b,soft_a in config['planes']:
        if np.dot(b,direction)<0:
            if np.dot(v,b)<0:v=project(v,b)
            if np.dot(a,direction)<0 and np.dot(v,a)<0:v=project(v,a)
        elif np.dot(a,direction)<0:
            if np.dot(v,a)<0:v=project(v,a)
        elif np.dot(soft_b,direction)<0:
            if np.dot(v,soft_b)<0:
                f=-np.dot(soft_b,direction)/abs(np.dot(soft_b,b));v=project(v,b)+f*np.dot(v,b)*b
        elif np.dot(soft_a,direction)<0 and np.dot(v,soft_a)<0:
            f=-np.dot(soft_a,direction)/abs(np.dot(soft_a,a));v=project(v,a)+f*np.dot(v,a)*a
    p+=dt*config['response']*v
    correction=p/np.linalg.norm(p)*(np.linalg.norm(p)-config['length'])
    return p-correction,v-correction/dt


def matrix(point,rest,parent):
    result=rest@parent
    target=-(point@parent[:3,:3]);target/=np.linalg.norm(target)
    axis=np.cross(target,result[0,:3]);sine=min(np.linalg.norm(axis),1.)
    if sine>1e-8:
        axis/=np.linalg.norm(axis);x,y,z=axis;skew=np.array([[0,-z,y],[z,0,-x],[-y,x,0]])
        rotation=np.eye(3)+sine*skew+(1-np.sqrt(max(0.,1-sine*sine)))*(skew@skew)
        result[:3,:3]=result[:3,:3]@rotation
    result[3,:3]=point@parent[:3,:3]+parent[3,:3]
    return result


def world(skeleton,config,seconds):
    """Fixed 125 Hz diagnostic replay; controller history survives body clip loops."""
    time=max(0.,seconds);bone=skeleton.index[0x130035EE];parent=skeleton.parents[bone]
    p=config['initial'].copy();v=np.zeros(3);previous=skeleton.world(0)[parent][3,:3]
    count=int(time*125)
    for step in range(1,count+1):
        pose=skeleton.world((step/125*5)%20)[parent]
        p,v=advance(config,p,v,previous,pose,1/125);previous=pose[3,:3]
    poses=skeleton.world((time*5)%20)
    if time-count/125>1e-7:p,v=advance(config,p,v,previous,poses[parent],time-count/125)
    poses[bone]=matrix(p,skeleton.nodes[bone][0],poses[parent])
    changed={bone}
    for i,(_,_,_) in enumerate(skeleton.nodes):
        if i!=bone and skeleton.parents[i] in changed:
            poses[i]=skeleton.nodes[i][0]@poses[skeleton.parents[i]];changed.add(i)
    return poses
