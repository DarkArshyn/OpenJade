"""Export source-evaluated Prince body animation for the Vulkan diagnostic viewer.

Draw states and frozen lighting still come from the previous diagnostic capture.
No captured matrices are used for vertex positions. The dagger uses a source-backed constrained diagnostic controller; native startup remains unverified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import numpy as np
from export_prince_preview import export as export_frozen
from prince_resources import Resources, COMPONENTS
from prince_animation import Skeleton, node
from prince_attachments import holder_points, dagger_local
from prince_sheath import configuration, encode


def influences(resources, skeleton, component):
    mesh = component['geometry']
    if component['mesh'] == '0x057CC7F4':
        local=dagger_local(resources)
        points=(np.c_[mesh['position'],np.ones(len(mesh['position']))]@local)[:,:3]
        return [[(skeleton.index[0x130035EE],1.,p)] for p in points]
    if component['mesh'] == '0x3F000E05':
        return [[(skeleton.index[0x130035BE], 1., p)] for p in holder_points(resources, component)]
    if component['mesh'] == '0x33001050':
        # The source snap transform composed with Spine2 matches eleven native poses.
        local, _, _ = node(resources, 0x3F000E3C)
        points = (np.c_[mesh['position'], np.ones(len(mesh['position']))] @ local)[:, :3]
        return [[(skeleton.index[0x130035BE], 1., p)] for p in points]
    # Neutral facial joints are source-local. Their expression controllers are not evaluated.
    if component['mesh'] == '0x13008483':
        world = {};visiting=set()
        def visit(k):
            if k in visiting:raise ValueError('Cyclic face hierarchy')
            if k not in world:
                visiting.add(k);m,p,_=node(resources,k)
                world[k]=m@visit(p) if p else m
                visiting.remove(k)
            return world[k]
        palette=np.array([b['inverse_bind']@visit(int(link['key'],16)) for b,link in zip(mesh['bones'],component['bindings'])])
        points=np.c_[mesh['position'],np.ones(len(mesh['position']))]
        local=np.einsum('vb,bjk,vj->vk',mesh['weights'],palette,points)[:,:3]
        face_local=node(resources,0x13005EEA)[0]
        local=(np.c_[local,np.ones(len(local))]@face_local)[:,:3]
        return [[(5,1.,p)] for p in local]
    if mesh['weights'] is None:
        key={'0x13008427':0x13006955,'0x13008428':0x13006959}[component['mesh']]
        local,parent,_=node(resources,key)
        points=(np.c_[mesh['position'],np.ones(len(mesh['position']))]@local)[:,:3]
        return [[(skeleton.index[parent],1.,p)] for p in points]
    result=[]
    for v,p in enumerate(mesh['position']):
        links=[]
        for j in np.flatnonzero(mesh['weights'][v]):
            bone=mesh['bones'][j];binding=component['bindings'][j]
            links.append((skeleton.index[int(binding['key'],16)],float(mesh['weights'][v,j]),(np.r_[p,1.]@bone['inverse_bind'])[:3]))
        if not 1<=len(links)<=3:raise ValueError('Unsupported influence count')
        result.append(links)
    return result


def export(sources,capture,output):
    report=export_frozen(sources,capture,output)
    r=Resources(sources);s=Skeleton(r)
    components={c['mesh'][2:]:c for c in (r.component(k) for k in COMPONENTS)}
    excluded=set()
    path=output/'prince.ojscene';raw=path.read_bytes()
    nv,w,h,nlayers=struct.unpack_from('<4I',raw,8)
    old=np.frombuffer(raw,'<f4',count=nv*9,offset=76).reshape(nv,9)
    texture_end=76+nv*36+w*h*nlayers*4
    count=struct.unpack_from('<I',raw,texture_end)[0]
    pending={key:list(c['geometry']['groups']) for key,c in components.items()}
    rows=[];draws=[];links=[];evidence=[]
    for i,item in enumerate(report['draws']):
        key=item['mesh'][2:]
        first,num=struct.unpack_from('<2I',raw,texture_end+4+i*48)
        group=pending[key].pop(0)
        if key in excluded:continue
        component=components[key];mesh=component['geometry'];per_vertex=influences(r,s,component)
        ids=mesh['faces'][group['first']:group['first']+group['count'],:3].ravel()
        block=old[first:first+num].copy()
        start=sum(len(a) for a in rows)
        for j,vid in enumerate(ids):links.append((start+j,per_vertex[vid]))
        rows.append(block)
        draw=bytearray(raw[texture_end+4+i*48:texture_end+4+(i+1)*48]);struct.pack_into('<I',draw,0,start);draws.append(draw);evidence.append(item)
    vertices=np.concatenate(rows);world=s.world(0)
    for index,weights in links:
        vertices[index,:3]=sum(weight*(np.r_[p,1.]@world[bone])[:3] for bone,weight,p in weights)
    lo=vertices[:,:3].min(0);hi=vertices[:,:3].max(0);center=(lo+hi)/2
    distance=float(np.linalg.norm(hi-lo)/2)/np.sin(np.deg2rad(22.5))*1.12
    camera=[*(center-np.array([0.,distance,0.])),1.,0.,0.,0.,0.,1.,0.,1.,0.,45.]
    header=bytearray(raw[:76]);struct.pack_into('<I',header,8,len(vertices));struct.pack_into('<13f',header,24,*camera)
    blob=header+vertices.astype('<f4').tobytes()+raw[76+nv*36:texture_end]+struct.pack('<I',len(draws))+b''.join(draws)+raw[texture_end+4+count*48:]
    path.write_bytes(blob)
    tracks=[t for t in s.tracks if t['target']!=65535]
    # Five ticks/second is measured against GOG palettes; loop replay is diagnostic.
    control=bytearray(b'OJACT001')+struct.pack('<3I2f',len(s.keys),len(tracks),len(links),5.,20.)
    for parent,(matrix,_,_) in zip(s.parents,s.nodes):control+=struct.pack('<i16f',parent,*matrix.ravel())
    for t in tracks:
        rotation=t['kind']=='rotation'
        control+=struct.pack('<3I',t['target'],0 if rotation else 1,len(t['keys']))
        for key in t['keys']:
            values=np.asarray(key['values'],float)/(32768 if rotation else 1)
            if not rotation:values=np.r_[values,0.]
            control+=struct.pack('<5f',key['tick'],*values)
    for index,weights in links:
        control+=struct.pack('<2I',index,len(weights))
        for bone,weight,p in weights:control+=struct.pack('<I4f',bone,weight,*p)
    (output/'prince.actor').write_bytes(control)
    (output/'prince.sheath').write_bytes(encode(configuration(r),s.index[0x130035EE]))
    report.update(bounds=[lo.tolist(),hi.tolist()],camera=camera,components_rendered=len({d['component'] for d in evidence}),triangles=len(vertices)//3,draws=evidence,
                  sources=r.sources,animation_resource_records=r.used,scene_sha256=hashlib.sha256(blob).hexdigest(),
                  actor_sha256=hashlib.sha256(control).hexdigest(),animation=dict(bones=62,tracks=37,clip='2D000AD4',ticks_per_second=5.,duration_ticks=20,loop='diagnostic replay'))
    report['limitations']=[
        'Body positions use original skeleton, inverse binds, packed weights and animation keys; no captured pose matrices.',
        'Untracked secondary joints use source-local transforms; procedural clothing fidelity is not validated.',
        'Neutral face follows the head bone; facial expression/eye controllers are not implemented.',
        'Dagger uses measured local orientation and source sheath constraints. Fixed 125 Hz diagnostic stepping resets from rest with each clip; native startup and wind activation are not reproduced.',
        'Holder internal joints use the source sheathed clip 3F000E32; other holder actions are not selected.',
        'Sword uses its source snap transform and Spine2; reflection and material slot remapping remain unimplemented.',
        'Lighting colors and draw states remain from the frozen diagnostic capture; animated normal lighting is not implemented.',
        'Five ticks/second matches the short native sample; action selection and looping semantics remain unverified.',
        'Standalone diagnostic, not integrated into the menu or gameplay.']
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    from prince_actor_lighting import prepare
    report['animated_lighting']=prepare(sources,capture,output)
    report['limitations']=[x for x in report['limitations'] if not x.startswith('Lighting colors')]
    report['limitations'].append('Normals and lighting colors update at runtime; lighting parameters and material states retain native-capture provenance.')
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--sources',type=Path,nargs='+',required=True);a=p.parse_args()
    result=export(a.sources,a.capture,a.output);print(json.dumps({k:result[k] for k in ('components_rendered','triangles','animation','limitations')},indent=2))
