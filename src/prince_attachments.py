"""Source-backed attachment poses validated against independent TSoT captures."""
import struct
import numpy as np
from prince_animation import node, decode_tracks, sample
from sample_camera02_animation import quaternion_matrix


def holder_world(resources):
    """Evaluate the source sheathed pose; this is not an action-state selector."""
    data=resources.get(0x3F000E2C)
    if len(data)!=24:raise ValueError('Unsupported holder bone list')
    keys=list(struct.unpack('<6I',data));nodes={k:node(resources,k) for k in keys}
    if len(nodes)!=6:raise ValueError('Duplicate holder bone')
    tracks=decode_tracks(resources.get(0x3F000E32))
    local={k:m.copy() for k,(m,_,_) in nodes.items()};channels=set()
    for t in tracks:
        target=t['target']
        if target==65535:continue  # Separate object-root channel, not a joint transform.
        if target>=len(keys) or (target,t['kind']) in channels:raise ValueError('Invalid holder channel')
        channels.add((target,t['kind']));m=local[keys[target]];value=sample(t,0.)
        if t['kind']=='rotation':m[:3,:3]=quaternion_matrix(value)
        else:m[3,:3]=value
    world={};visiting=set()
    def visit(k):
        if k in visiting:raise ValueError('Cyclic holder skeleton')
        if k not in nodes:raise ValueError('External holder parent')
        if k not in world:
            visiting.add(k);parent=nodes[k][1]
            world[k]=local[k]@visit(parent) if parent else local[k]
            visiting.remove(k)
        return world[k]
    for k in keys:visit(k)
    return world


def holder_points(resources,component):
    mesh=component['geometry'];world=holder_world(resources)
    palette=np.array([b['inverse_bind']@world[int(link['key'],16)]
                      for b,link in zip(mesh['bones'],component['bindings'])])
    points=np.c_[mesh['position'],np.ones(len(mesh['position']))]
    return np.einsum('vb,bjk,vj->vk',mesh['weights'],palette,points)[:,:3]


def dagger_local(resources):
    """Observed native sheathed orientation followed by the original snap transform.

    This basis is measured at native attachment initialization, not a GAO field.
    It is a proper half-turn around (1, -1, 0). The sheath parent controller is
    deliberately separate and is not reconstructed by this local transform.
    """
    basis=np.array([[0.,-1.,0.,0.],[-1.,0.,0.,0.],[0.,0.,-1.,0.],[0.,0.,0.,1.]])
    snap,parent,_=node(resources,0x130046A1)
    if parent!=0x130035EE:raise ValueError('Unexpected dagger snap parent')
    return basis@snap
