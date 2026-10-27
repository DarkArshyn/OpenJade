"""Export verified fog/fixture passes from existing research exports to OJSCN002.

Effective time is a chosen sample, not a captured original-game animation phase.
Original inputs are read only. Lighting selectors 0/3 remain explicitly diagnostic.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from PIL import Image


def pass_parameters(stage, time):
    """Preserve static offsets; advance only native dynamic U/V flags."""
    flags = stage['flags']
    mode = stage['blend']
    if (mode, stage['depth_write']) not in ((0, True), (1, False), (6, False)):
        raise ValueError('Unsupported blend/depth combination')
    offset = [(r * (time if flags & bit else 1)) % 1
              for r, bit in zip(stage['rate'], (0x40000000, 0x80000000))]
    return mode, [*stage['scale'], *offset, stage['alpha'], 2., 0., 1.]


def convert(source, camera, output, time=0.):
    if not math.isfinite(time) or time < 0: raise ValueError('Invalid effective time')
    if output.exists(): raise FileExistsError(output)
    report = json.loads((source/'scene.json').read_text(encoding='utf-8'))
    poses = json.loads(camera.read_text(encoding='utf-8'))
    if report['source_sha256'] != poses['source_sha256']: raise ValueError('Scene/camera source mismatch')
    accepted = {o['name']: o for o in report['accepted']}
    if len(accepted) != len(report['accepted']) or any(o['omitted_groups'] for o in accepted.values()):
        raise ValueError('Ambiguous or incomplete object export')
    materials = {m['slot']: m for m in report['materials']}
    matrix = poses['poses'][0]['matrix']
    if poses['poses'][0]['time'] != 0: raise ValueError('Expected initial Camera02')
    eye = matrix[3][:3]; forward = [-v for v in matrix[1][:3]]
    camera_values = eye + [-v for v in matrix[0][:3]] + matrix[2][:3] + forward + [poses['vertical_fov']]
    vertices, uvs, groups = [], [], []
    name, current = None, None
    for line in (source/'scene.obj').read_text(encoding='utf-8').splitlines():
        p=line.split()
        if not p or p[0].startswith('#'): continue
        if p[0]=='o': name=' '.join(p[1:]); current=None
        elif p[0]=='v':
            if len(p)!=7: raise ValueError('Expected XYZ RGB')
            vertices.append(list(map(float,p[1:])))
        elif p[0]=='vt':
            if len(p)!=3: raise ValueError('Expected UV')
            uvs.append(list(map(float,p[1:])))
        elif p[0]=='usemtl':
            if name not in accepted: raise ValueError('Unknown OBJ object')
            slot=int(p[1].removeprefix('material-'))
            if slot not in materials: raise ValueError('Unknown material slot')
            current=dict(name=name,slot=slot,vertices=[]);groups.append(current)
        elif p[0]=='f':
            if current is None or len(p)!=4: raise ValueError('Expected grouped triangle')
            for item in p[1:]:
                pair=list(map(int,item.split('/')))
                if len(pair)!=2 or not(0<pair[0]<=len(vertices) and 0<pair[1]<=len(uvs)): raise ValueError('Invalid OBJ index')
                v=vertices[pair[0]-1];uv=uvs[pair[1]-1]
                current['vertices'].append([*v[:3],uv[0],1-uv[1],*v[3:]])
    counts={name:sum(len(g['vertices'])//3 for g in groups if g['name']==name) for name in accepted}
    if any(counts[name]!=row['triangles'] for name,row in accepted.items()): raise ValueError('Triangle count mismatch')
    # Keep object/group pass order. Fog is deferred and sorted by object-center view depth.
    solid=[g for g in groups if not accepted[g['name']]['fog_states']]
    fog=[g for g in groups if accepted[g['name']]['fog_states']]
    def distance(g):
        center=[sum(v[i] for v in g['vertices'])/len(g['vertices']) for i in range(3)]
        return sum((center[i]-eye[i])*forward[i] for i in range(3))
    fog.sort(key=distance,reverse=True)
    image_names=[];expanded=[];draws=[];audit=[]
    for g in solid+fog:
        row=accepted[g['name']];slot=g['slot'];material=materials[slot]
        color_groups=[x for x in row['color_groups'] if x['material']==material['key']]
        if len(color_groups)!=1: raise ValueError('Ambiguous material color state')
        color=color_groups[0]
        if row['fog_states']:
            if len(row['fog_states'])!=1: raise ValueError('Ambiguous fog state')
            state=row['fog_states'][0]
            if state['flags']!='0x40014205': raise ValueError('Unsupported fog flags')
            # OBJ UVs already include the export's sampled fog motion.
            motion=state['motion'];du=motion['rate_u']*(time-report['fog_time'])
            passes=[(f'material-{slot}.png',1,[1.,1.,du%1,0.,1.,1.,0.,2.])]
        elif material['stages']:
            passes=[]
            for i,stage in enumerate(material['stages']):
                mode,params=pass_parameters(stage,time)
                passes.append((f'material-{slot}-stage-{i}.png',mode,params))
        else:
            passes=[(f'material-{slot}.png',0,[1.,1.,0.,0.,1.,1.,.5,0.])]
        for image,mode,params in passes:
            if image not in image_names: image_names.append(image)
            layer=image_names.index(image);first=len(expanded)
            for vertex in g['vertices']:
                vertex=vertex.copy()
                if color['mode']==2:
                    # Reconstruct the verified constant explicitly, avoiding a second x2.
                    vertex[5:8]=[c*2/255 for c in color['constant_rgb']]
                expanded.append([*vertex,float(layer)])
            draws.append((first,len(g['vertices']),mode,0 if mode else 1,params))
            audit.append(dict(object=g['name'],material=material['key'],texture=image,blend=mode,depth_write=mode==0,
                              parameters=params,color_mode=color['mode'],color_status='verified constant x2' if color['mode']==2 else 'exported vertex colors; active runtime lighting unresolved'))
    size=512;pixels=bytearray();textures=[]
    for name in image_names:
        path=source/name
        with Image.open(path) as image:
            original=image.size
            pixels.extend(image.convert('RGBA').resize((size,size),Image.Resampling.NEAREST).tobytes())
        textures.append(dict(file=name,original_size=original,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    values=camera_values+[f for v in expanded for f in v]+[f for d in draws for f in d[4]]
    if not all(math.isfinite(x) for x in values): raise ValueError('Non-finite export')
    blob=bytearray(b'OJSCN002');blob.extend(struct.pack('<4I13f',len(expanded),size,size,len(image_names),*camera_values))
    for v in expanded: blob.extend(struct.pack('<9f',*v))
    blob.extend(pixels);blob.extend(struct.pack('<I',len(draws)))
    for first,count,mode,write,params in draws: blob.extend(struct.pack('<4I8f',first,count,mode,write,*params))
    if len(blob)>256*1024*1024: raise ValueError('Package too large')
    output.mkdir(parents=True,exist_ok=False)
    (output/'menu.ojscene').write_bytes(blob)
    manifest=dict(version=2,source_sha256=report['source_sha256'],source_obj_sha256=hashlib.sha256((source/'scene.obj').read_bytes()).hexdigest(),
        source_report_sha256=hashlib.sha256((source/'scene.json').read_bytes()).hexdigest(),camera_sha256=hashlib.sha256(camera.read_bytes()).hexdigest(),
        package_sha256=hashlib.sha256(blob).hexdigest(),object_count=len(counts),objects=counts,geometry_triangles=sum(counts.values()),
        submitted_triangles=len(expanded)//3,texture_layers=len(image_names),textures=textures,draws=audit,effective_time=time,
        limitations=['Time is an explicit sample with chosen phase zero; no wall-clock animation',
                    'Fog sorted by object center; native global sorting unresolved',
                    'Mode 0/3 colors and sRGB/linear behavior remain diagnostic; faithful scene lighting is not established',
                    '512x512 texture array resampling and base-level sampling; no original mip selection',
                    'No fire particles or actual light emission from the fixtures'])
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(f"{len(counts)} objects; {sum(counts.values())} geometry triangles; {len(expanded)//3} submitted triangles; {len(draws)} passes; {len(image_names)} textures")

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('camera',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--time',type=float,default=0.,help='Effective animation time in seconds (fixed sample)')
    a=p.parse_args();convert(a.source,a.camera,a.output,a.time)
