"""Assemble supported frozen Menu3D meshes with a diagnostic fixed camera."""
import argparse, hashlib, json, struct, math
from pathlib import Path
import numpy as np
from PIL import Image
from probe_menu3d import records
from resolve_camera_function_bodies import HASH
from inspect_menu_scene_links import static_links
from preview_menu3d_landmarks import mesh_groups
from menu_colored_raster import raster
from menu_material_colors import color_state, apply_material_colors
from menu_gpu_colors import direct_tree_colors
from menu_primary_geometry import primary_mesh, instance_colors
from menu_fog_state import fog_state, transform_fog_points, fog_uv_motion, animate_fog_uv


def decode_mesh(d):
    d=bytes(d)
    if len(d)<44 or struct.unpack_from('<2I',d) not in ((1,7),(1,8)):
        raise ValueError('Unsupported geometry header')
    found=[]
    # Candidate discovery is followed by complete extent, index and XYZ checks.
    for h in range(44,len(d)-12,4):
        n,stride=struct.unpack_from('<2I',d,h)
        if stride!=20 or n==0 or h+8+n*20+4>len(d):continue
        try: result=mesh_groups(d,h)
        except (ValueError,struct.error,IndexError):continue
        found.append((h,result))
    if len(found)!=1:raise ValueError('Missing or ambiguous validated cooked mesh')
    return found[0]


def material_keys(d):
    if len(d)>=12 and struct.unpack_from('<I',d)[0]==4:
        n=struct.unpack_from('<I',d,8)[0]
        if len(d)!=12+n*4:raise ValueError('Material pack extent mismatch')
        return list(struct.unpack_from('<'+'I'*n,d,12))
    if len(d)==48 and struct.unpack_from('<2I',d)==(5,6):return None
    raise ValueError('Unsupported material pack')


def texture_image(d):
    if len(d)<56:raise ValueError('Truncated texture')
    fmt,w,h=struct.unpack_from('<3I',d,40)
    if fmt not in (0,5,7) or not (0<w<=8192 and 0<h<=8192) or (w,h)!=struct.unpack_from('<HH',d,12):
        raise ValueError('Unsupported texture layout')
    if fmt==0:
        levels=struct.unpack_from('<I',d,52)[0]+1
        if not 1<=levels<=14:raise ValueError('Invalid raw mip count')
        total=sum(max(1,w>>i)*max(1,h>>i)*4 for i in range(levels))
        if len(d)!=56+total:raise ValueError('Raw texture mip extent mismatch')
        return Image.frombytes('RGBA',(w,h),d[56:56+w*h*4],'raw','BGRA')
    codec,block=(1,8) if fmt==5 else (3,16)
    offset=60 if fmt==5 else 56
    if fmt==5 and d[56:60]!=bytes.fromhex('000000c0'):raise ValueError('Unknown BC1 prefix')
    size=((w+3)//4)*((h+3)//4)*block
    if offset+size>len(d):raise ValueError('Truncated compressed pixels')
    return Image.frombytes('RGBA',(w,h),d[offset:offset+size],'bcn',codec)


def export(source,out, yaw=12.0, pitch=-1.0, fov=50.0, fog_time=0.0, tree_upload_check=False):
    if not math.isfinite(fog_time) or fog_time < 0:raise ValueError("Fog time must be finite and nonnegative")
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH:raise ValueError('Unsupported source')
    by={}
    for r in records(raw):by.setdefault(r['key'],[]).append(r)
    def payload(key):
        rows=by.get(key,[])
        if len(rows)!=1:raise ValueError('Missing or ambiguous key '+key)
        r=rows[0];return raw[r['offset']+12:r['end']]
    out.mkdir(parents=True,exist_ok=False)
    objects=[];accepted=[];excluded=[];materials={};textures={};material_reports=[]
    def material(key):
        if key in materials:return materials[key]
        d=payload(key)
        if len(d)!=48 or struct.unpack_from('<2I',d)!=(5,6):raise ValueError('Unsupported leaf material '+key)
        texkey=f'0x{struct.unpack_from("<I",d,44)[0]:08X}'
        images=[]
        for record in by.get(texkey,[]):
            try: images.append(texture_image(raw[record['offset']+12:record['end']]))
            except ValueError: pass
        if len(images)!=1:raise ValueError('Missing or ambiguous pixel payload '+texkey)
        image=images[0];slot=len(materials)
        materials[key]=slot;textures[slot]=np.asarray(image);image.save(out/f'material-{slot}.png')
        material_reports.append(dict(slot=slot,key=key,texture=texkey,color_state=color_state(d)))
        return slot
    for key,rs in by.items():
        if len(rs)!=1:continue
        d=payload(key)
        if d[:4]!=b'.gao':continue
        try:
            link=static_links(d);v,tri,groups,vertex_ids,nv,colors,layout=primary_mesh(payload(link['mesh']));h=44
            rli,color_offset=instance_colors(d,link['link_offset'],nv)
            if rli is not None:colors=rli
            color_source='instance' if rli is not None else ('geometry' if colors is not None else 'white fallback')
            if colors is None:colors=np.ones((nv,3))
            colors=colors[vertex_ids]
            pack=material_keys(payload(link['material_pack']))
            mapped=[]
            fog_states=[]
            color_states=[]
            partial = key in {'0x30000D53', '0x30000F45', '0x3000FCFA'}
            retained=[]; group_start=0; omitted=[]
            for slot,count in groups:
                if pack is None:
                    if slot!=0:raise ValueError('Nonzero slot for leaf material')
                    leaf=link['material_pack']
                else:
                    if slot>=len(pack):raise ValueError('Material slot out of range')
                    leaf=f'0x{pack[slot]:08X}'
                if partial and len(payload(leaf)) != 48:
                    omitted.append(dict(material=leaf,triangles=count,reason='Multi-stage material not implemented'))
                    group_start += count
                    continue
                retained.append(tri[group_start:group_start+count])
                group_start += count
                mapped.append((material(leaf),count))
                color_states.append(dict(material=leaf,triangles=count,**color_state(payload(leaf))))
                if leaf == "0x30000CAB":
                    state=fog_state(payload(leaf));state["motion"]=fog_uv_motion(payload(leaf));fog_states.append(state)
            if partial:
                tri=np.concatenate(retained) if retained else np.empty((0,3),dtype=int)
            matrix=np.array(struct.unpack_from('<16f',d,link['matrix_offset'])).reshape(4,4)
            if not np.isfinite(matrix[:,:3]).all() or (key not in {"0x30000D38", "0x30000CCE", "0x30000D53", "0x30000F45"} and not np.allclose(matrix[:3,3],0,atol=1e-6)):
                raise ValueError('Unsupported affine matrix')
            world=transform_fog_points(v[:,:3],matrix) if key in {"0x30000D38", "0x30000CCE", "0x30000D53", "0x30000F45"} else v[:,:3]@matrix[:3,:3]+matrix[3,:3]
            is_fog=bool(fog_states) and len(fog_states)==len(mapped)
            if is_fog:
                colors=np.tile(np.array(fog_states[0]["constant_rgb"])*2/255,(len(v),1))
                color_source="native material constant x2"
                v[:,3:]=animate_fog_uv(v[:,3:],fog_states[0]["motion"],fog_time)
            previous_colors=colors.copy()
            colors=apply_material_colors(colors,tri,mapped,color_states)
            if tree_upload_check and key == '0x30000CBC':
                if rli is None:raise ValueError('Missing direct tree colors')
                colors=direct_tree_colors(colors,struct.unpack_from('<I',d,link['link_offset']+8)[0],color_states)
                color_source='tronc4 loaded-state dynamic upload experiment: recorded RGB x2'
            if not is_fog and any(s["mode"]==2 for s in color_states):color_source="per-group constant x2 / existing vertex approximation"
            objects.append(dict(previous_colors=previous_colors,blend=is_fog,fog_sampler=is_fog,name=link['name'],vertices=world,uv=v[:,3:],triangles=tri,groups=mapped,colors=colors))
            accepted.append(dict(omitted_groups=omitted,color_groups=color_states,fog_states=fog_states,scale=matrix[:3,3].tolist() if key in {"0x30000D38", "0x30000CCE", "0x30000D53", "0x30000F45"} else None,key=key,name=link['name'],mesh=link['mesh'],header_offset=layout["vertex_offset"],color_source=color_source,color_offset=color_offset,layout=layout,vertices=len(v),triangles=len(tri),material_pack=link['material_pack']))
        except (ValueError,struct.error,IndexError) as error:
            excluded.append(dict(key=key,reason=str(error)))
    if not objects:raise ValueError('No supported objects')
    lines=['# Diagnostic common-space assembly; original lighting not reproduced','mtllib scene.mtl'];base=1
    for obj in objects:
        lines.append('o '+obj['name'])
        lines+=['v '+' '.join(map(str,(*p,*c))) for p,c in zip(obj['vertices'],obj['colors'])]
        lines+=['vt '+str(p[0])+' '+str(1-p[1]) for p in obj['uv']]
        start=0
        for slot,count in obj['groups']:
            lines.append('usemtl material-'+str(slot))
            lines+=['f '+' '.join(f'{int(i)+base}/{int(i)+base}' for i in t) for t in obj['triangles'][start:start+count]];start+=count
        base+=len(obj['vertices'])
    (out/'scene.obj').write_text('\n'.join(lines)+'\n',encoding='utf8')
    (out/'scene.mtl').write_text('\n'.join(f'newmtl material-{i}\nKd 1 1 1\nmap_Kd material-{i}.png\n' for i in textures),encoding='ascii')
    cam=payload('0x30000CF0');n=struct.unpack_from('<I',cam,16)[0]
    f=np.array(struct.unpack_from('<16f',cam,30+n)).reshape(4,4)
    basis=f[:3,:3].copy()
    right,up,forward=basis[0],basis[2],-basis[1]
    a=math.radians(yaw);right,forward=math.cos(a)*right-math.sin(a)*forward,math.sin(a)*right+math.cos(a)*forward
    a=math.radians(pitch);up,forward=math.cos(a)*up-math.sin(a)*forward,math.sin(a)*up+math.cos(a)*forward
    adjusted=np.array([right,-forward,up])
    previous_objects=[dict(o,colors=o['previous_colors']) for o in objects]
    previous,_,_=raster(previous_objects,textures,f[3,:3],adjusted,fov,False,blend_enabled=True)
    previous.save(out/'previous-colors.png')
    baseline,_,_=raster(objects,textures,f[3,:3],adjusted,fov,False,blend_enabled=False)
    baseline.save(out/'alpha-test-baseline.png')
    image,coverage,drawn=raster(objects,textures,f[3,:3],adjusted,fov,False,blend_enabled=True)
    image.save(out/'fixed-camera.png')
    report=dict(fog_time=fog_time,fog_time_basis="effective engine seconds, forward playback, chosen phase zero; not wall-clock replay",source_sha256=HASH,accepted=accepted,excluded=excluded,materials=material_reports,coverage_pixels=coverage,rasterized_triangles=drawn,
        camera=dict(key='0x30000CF0',vertical_fov=fov,yaw_adjustment=yaw,pitch_adjustment=pitch,adjustment_status='manual screenshot approximation',forward='-Y',position=f[3,:3].tolist()),
        limitations=['Camera02 is a candidate, not confirmed main-menu framing','Common-space row transforms assumed; hierarchy unresolved; fourth matrix word in final row is opaque and unused','Constant-color mode 2 is applied per group; modes 0/3 retain diagnostic vertex colors rather than recovered lighting. Non-fog alpha threshold 128, repeat UV and nearest sampling remain diagnostic; fog uses base-level linear wrap-U/clamp-V; mip selection unresolved; dynamic U sampled analytically at effective engine time, initial phase fixed to zero','Three fog panels use native-verified source-over and no depth writes; object-center sorting remains diagnostic; fog RGB uses native material constant x2 and texture alpha','Raw format 0 interpreted as BGRA with exact mip-chain extent validation','Particles, unsupported layouts and animation excluded','OBJ V is inverted for interchange; native UV retained for raster'])
    report['tree_upload_check']=tree_upload_check
    report['limitations'].append('Opt-in tronc4 experiment assumes the traced dynamic upload and loaded flags; cached buffer execution is not captured')
    (out/'scene.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(len(accepted),'objects;',sum(x['triangles'] for x in accepted),'triangles;',len(materials),'materials;',coverage,'covered pixels',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--yaw',type=float,default=12);p.add_argument('--pitch',type=float,default=-1);p.add_argument('--fov',type=float,default=50)
    p.add_argument("--fog-time",type=float,default=0,help="Forward effective engine seconds from diagnostic phase zero")
    p.add_argument('--tree-upload-check',action='store_true',help='Apply the traced direct-color dynamic-upload case to tronc4 only')
    a=p.parse_args();export(a.source,a.output,a.yaw,a.pitch,a.fov,a.fog_time,a.tree_upload_check)







