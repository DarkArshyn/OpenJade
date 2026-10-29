"""Audit the frozen menu's cached balcony, submitted textures and fog probes.

Reads original data only; this is not a live original-game render capture.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import numpy as np
from probe_menu3d import records
from menu_primary_geometry import primary_mesh, instance_colors
from resolve_camera_function_bodies import HASH
from inspect_menu_scene_links import static_links
from menu_fixture_materials import sample_stage
from menu_fog_state import sample_fog


def compare_cached(primary, ids, rgb, vertices, indices, bgra):
    """Compare expanded corners, accounting for cached BGRA channel order."""
    if indices.max() >= len(vertices) or len(vertices) != len(bgra):
        raise ValueError('Invalid cached indices/count')
    if len(indices) != len(primary):
        raise ValueError('Cached corner count mismatch')
    return dict(corners=len(indices),
                position_max_error=float(np.abs(vertices[indices,:3]-primary[:,:3]).max()),
                uv_max_error=float(np.abs(vertices[indices,3:]-primary[:,3:]).max()),
                rgb_mismatches=int(np.any(bgra[indices][:,[2,1,0]] != np.rint(rgb[ids]*255),axis=1).sum()))


def cached_balcony(by):
    mesh, instance = by['0x30000C8C'], by['0x30000CD9']
    v,tri,groups,ids,nv,_,layout = primary_mesh(mesh)
    rgb,offset = instance_colors(instance,175,nv)
    if offset != 197: raise ValueError('Unexpected instance layout')
    p = layout['primary_end']+8
    count = struct.unpack_from('<I',mesh,p)[0]; p += 4
    pairs = [struct.unpack_from('<II',mesh,p+i*8) for i in range(count)]
    if pairs != groups: raise ValueError('Cached group mismatch')
    p += count*8
    size,kind,n,stride = struct.unpack_from('<4I',mesh,p)
    if kind != 0 or stride != 20 or size != 8+n*stride: raise ValueError('Cached mesh layout')
    start = p+16
    cv = np.frombuffer(mesh,dtype='<f4',count=n*5,offset=start).reshape(-1,5)
    p = start+n*stride
    index_size = struct.unpack_from('<I',mesh,p)[0]
    if index_size != len(tri)*6 or p+4+index_size != len(mesh): raise ValueError('Cached indices extent')
    indices = np.frombuffer(mesh,dtype='<u2',count=index_size//2,offset=p+4)
    cp = offset+nv*4+20
    csize,cn,cs = struct.unpack_from('<3I',instance,cp)
    if cn != n or cs != 12 or csize != 8+cn*cs: raise ValueError('Cached instance extent')
    colors = np.frombuffer(instance,dtype=np.uint8,count=cn*cs,offset=cp+12).reshape(-1,cs)[:,:4]
    result = compare_cached(v,ids,rgb,cv,indices,colors)
    result.update(vertices=n,mesh_stride=stride,color_stride=cs,mesh_offset=start,color_offset=cp+12)
    return result


def fog_probes(package, manifest):
    """Ray probes using exported geometry, base-level linear samples and depth.

    Ignores fixture transparent contributions and is not a full GPU rasterizer.
    Reports only points where the nearest cutout-passing opaque draw is balcony.
    """
    data=package.read_bytes()
    if hashlib.sha256(data).hexdigest()!=manifest['package_sha256']: raise ValueError('Package hash')
    if data[:8]!=b'OJSCN003': raise ValueError('Package version')
    nv,w,h,nl=struct.unpack_from('<4I',data,8)
    camera=np.array(struct.unpack_from('<13f',data,24)); eye=camera[:3]
    vertices=np.frombuffer(data,dtype='<f4',count=nv*9,offset=76).reshape(-1,9)
    pixel_start=76+nv*36; draw_start=pixel_start+w*h*nl*4
    count=struct.unpack_from('<I',data,draw_start)[0]
    if count!=len(manifest['draws']): raise ValueError('Draw count')
    textures=[]
    for i,t in enumerate(manifest['textures']):
        tw,th=t['original_size']
        im=np.frombuffer(data,dtype=np.uint8,count=w*h*4,offset=pixel_start+i*w*h*4).reshape(h,w,4)
        textures.append(im[:th,:tw])
    draws=[]
    for i,entry in enumerate(manifest['draws']):
        first,n,blend,write,*params=struct.unpack_from('<4I8f',data,draw_start+4+i*48)
        tri=vertices[first:first+n].reshape(-1,3,9)
        draws.append((entry,tri,blend,write,np.array(params)))
    result=[]; focal=300/math.tan(math.radians(camera[12])/2)
    for y in range(120,281,8):
        for x in range(240,401,8):
            ray=camera[9:12]+camera[3:6]*((x+.5-400)/focal)-camera[6:9]*((y+.5-300)/focal)
            hits=[]
            for entry,tri,blend,write,params in draws:
                a=tri[:,0,:3];e1=tri[:,1,:3]-a;e2=tri[:,2,:3]-a
                cross=np.cross(np.broadcast_to(ray,e2.shape),e2);det=np.sum(e1*cross,axis=1)
                inv=np.divide(1.,det,out=np.zeros_like(det),where=np.abs(det)>1e-9)
                delta=eye-a;u=np.sum(delta*cross,axis=1)*inv;q=np.cross(delta,e1)
                v=np.sum(q*ray,axis=1)*inv;z=np.sum(e2*q,axis=1)*inv
                valid=(np.abs(det)>1e-9)&(u>1e-7)&(v>1e-7)&(u+v<1-1e-7)&(z>.1)
                for j in np.flatnonzero(valid):
                    uv=((1-u[j]-v[j])*tri[j,0,3:5]+u[j]*tri[j,1,3:5]+v[j]*tri[j,2,3:5])*params[:2]+params[2:4]
                    image=textures[int(tri[j,0,8])]
                    sample=sample_fog(image,uv) if params[7]==2 else sample_stage(image,uv,dict(flags=0,scale=[1,1],rate=[0,0]),0)
                    alpha=float(sample[3]/255*params[4])
                    if alpha>=params[6]:hits.append((float(z[j]),entry['object'],bool(write),params[7]==2,alpha))
            opaque=[h for h in hits if h[2]]
            if not opaque:continue
            nearest=min(opaque)
            if nearest[1]!='Menu3D_FarahRoom_Balcony.gao':continue
            fog=[h for h in hits if h[3] and h[0]<nearest[0]]
            result.append(dict(pixel=[x,y],depth=nearest[0],fog=[dict(object=h[1],alpha=h[4],depth=h[0]) for h in fog],transmission=float(np.prod([1-h[4] for h in fog]))))
    return result


def audit(source, scene, package_dir, output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH:raise ValueError('Unsupported frozen resource')
    by={}
    for r in records(raw):
        if r['key'] in by:
            if r['key'] in ('0x30000C8C','0x30000CD9'):raise ValueError('Ambiguous balcony resource')
            continue
        by[r['key']]=raw[r['offset']+12:r['end']]
    report=json.loads((scene/'scene.json').read_text())
    manifest=json.loads((package_dir/'manifest.json').read_text())
    if report['source_sha256']!=HASH or manifest['source_sha256']!=HASH:raise ValueError('Source mismatch')
    if hashlib.sha256((scene/'scene.json').read_bytes()).hexdigest()!=manifest['source_report_sha256']:raise ValueError('Report hash mismatch')
    names={}
    for key,d in by.items():
        if d[:4]==b'.gao' and len(d)>=20:
            n=struct.unpack_from('<I',d,16)[0];names[key]=d[20:20+n].rstrip(b'\0').decode('ascii')
    materials=[]
    for m in report['materials']:
        users=[o['name'] for o in report['accepted'] if any(c['material']==m['key'] for c in o['color_groups'])]
        draws=[d for d in manifest['draws'] if d['material']==m['key']]
        materials.append(dict(slot=m['slot'],material=m['key'],texture=m['texture'],users=users,submitted_passes=len(draws),images=[d['texture'] for d in draws]))
    missing=[]
    for t in manifest['textures']:
        p=scene/t['file']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=t['sha256']:missing.append(t['file'])
    excluded=[]
    for e in report['excluded']:
        row=dict(e,name=names.get(e['key']))
        try:
            link=static_links(by[e['key']]); row.update(mesh=link['mesh'],material_pack=link['material_pack'])
            pack=by[link['material_pack']]
            if len(pack)>=12 and struct.unpack_from('<I',pack)[0]==4:
                n=struct.unpack_from('<I',pack,8)[0]
                if len(pack)!=12+4*n:raise ValueError('Pack extent')
                keys=[f'0x{k:08X}' for k in struct.unpack_from('<'+'I'*n,pack,12)]
            else:keys=[link['material_pack']]
            groups=primary_mesh(by[link['mesh']])[2]
            row['resolved_materials']=[keys[slot] for slot,_ in groups if slot<len(keys)]
            row['unresolved_slots']=[slot for slot,_ in groups if slot>=len(keys)]
        except (ValueError,KeyError,struct.error) as error:
            row['link_audit_limit']=str(error)
        excluded.append(row)
    result=dict(source_sha256=HASH,cached_balcony=cached_balcony(by),materials=materials,
                missing_or_changed_submitted_images=missing,excluded=excluded,
                named_lights=[dict(key=k,name=n,runtime='not implemented as a scene light') for k,n in names.items() if '_LUM_' in n],
                fog_probes=fog_probes(package_dir/'menu.ojscene',manifest),
                limitations=['Named lights are not proof of active runtime lighting',
                             'Texture submission is not proof of visible screen coverage',
                             'Fog probes use exported fixed pose/phase, not original-game depth or fog state',
                             'Cached byte equality does not capture runtime selection or shader arithmetic'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf8') as stream:json.dump(result,stream,indent=2)
    print('Cached balcony:',result['cached_balcony'])
    print('Unsubmitted materials:',[m['slot'] for m in materials if not m['submitted_passes']])
    probes=result['fog_probes'];trans=[p['transmission'] for p in probes]
    print('Lights:',len(result['named_lights']),'missing submitted images:',missing)
    print('Balcony probes:',len(probes),'fog intersections:',sum(bool(p['fog']) for p in probes),'transmission range:',[min(trans),max(trans)] if trans else [])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','scene','package_dir','output'):p.add_argument(name,type=Path)
    a=p.parse_args();audit(a.source,a.scene,a.package_dir,a.output)
