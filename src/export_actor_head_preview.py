"""Export one frozen native head sample for a bounded Vulkan material comparison.

This is a capture-driven diagnostic, not a native actor loader or animation runtime.
Inputs are read-only; extracted game data must remain outside version control.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

import numpy as np
from PIL import Image
from replay_actor_vertex_shader import formula


def export(capture, output, clamp=True, pixel_offset=.5):
    if output.exists():
        raise FileExistsError(output)
    prefix=capture.name
    lines=(capture/f'{prefix}-reference.txt').read_text().splitlines()
    assert 'draw_hr 00000000' in lines and 'texture_copy 00000000 00000000' in lines
    target=lines[0].split()[1].lower()
    registry=list(struct.iter_unpack('<5I',(capture/f'{prefix}-registry.bin').read_bytes()))
    object_lines=(capture/f'{prefix}-object-{target}.txt').read_text().splitlines()
    mesh=int(next(line.split()[1] for line in object_lines if line.startswith('mesh ')),16)
    assert {row[0] for row in registry if row[4]==mesh and row[2]==0x43f120}=={0x13008483}
    candidates=[]
    for path in capture.glob(f'{prefix}-draw-*.txt'):
        text=path.read_text()
        if text.split()[1]==target and 'target 800 600 ' in text:candidates.append(path)
    assert len(candidates)==1
    meta=candidates[0];text=meta.read_text().splitlines();header=text[0].split()
    assert int(header[3])==550 and int(header[9])==417 and int(header[11])==1
    assert 'state 27 0' in text and 'tss 0 1 5' in text and 'tss 0 3 0' in text
    stream=next(line.split() for line in text if line.startswith('stream 0 '))
    offset,stride=int(stream[3]),int(stream[5]);assert stride==52
    raw=meta.with_suffix('.stream0').read_bytes()
    c=np.fromfile(meta.with_suffix('.constants'),'<f4').astype(float).reshape(256,4)
    # Header fields: object, triangles, start, base, vertices, indexed.
    ids=np.fromfile(meta.with_suffix('.indices'),'<u2')[int(header[5]):int(header[5])+550*3].astype(int)+int(header[7])
    # The actual base is header[7]; validate the bounded stream range below.
    assert len(ids)==1650
    values={};light_max=0.
    for index in np.unique(ids):
        at=offset+int(index)*stride
        position=np.r_[struct.unpack_from('<3f',raw,at),1.]
        normal=np.r_[struct.unpack_from('<3f',raw,at+12),1.]
        indices=np.array(struct.unpack_from('<4h',raw,at+24),dtype=float)
        weights=np.r_[struct.unpack_from('<3f',raw,at+32),1.]
        uv=struct.unpack_from('<2f',raw,at+44)
        inputs=dict(v0=position,v2=normal,v7=indices,v1=weights)
        lighting,_=formula(inputs,c)
        bone=sum(weights[k]*c[42+int(indices[k]):45+int(indices[k])] for k in range(3))
        posed=np.r_[bone@position,1.]
        view=(c[4:8]@posed)[:3]
        light_max=max(light_max,float(lighting.max()))
        color=np.clip(lighting,0,1) if clamp else lighting
        values[int(index)]=[*view,*uv,*color,0.]
    camera_line=next(line.split() for line in lines if line.startswith('camera '))
    eye=list(map(float,camera_line[1:4]));fx,fy=map(float,camera_line[5:7])
    assert fx>0 and fy<0 and abs(abs(fy/fx)-4/3)<1e-5
    camera=[*eye,1,0,0,0,-1,0,0,0,1,math.degrees(2*math.atan(1/abs(fy)))]
    if pixel_offset not in (0.,.5):
        raise ValueError('Unsupported diagnostic raster offset')
    # Express a viewport pixel-center correction in this frozen view-space sample.
    # The original captured positions are never modified; this is not a pose adjustment.
    for vertex in values.values():
        depth=vertex[2]-eye[2]
        vertex[0]+=2*pixel_offset*depth/(800*fx)
        vertex[1]+=2*pixel_offset*depth/(600*abs(fy))
    # A diagnostic black plane matches the native isolated render-target clear.
    z=eye[2]+50
    corners=[[eye[0]+x,eye[1]+y,z,0,0,0,0,0,0] for x,y in [(-100,-100),(100,-100),(100,100),(-100,100)]]
    vertices=[corners[i] for i in (0,1,2,0,2,3)]+[values[int(i)] for i in ids]
    texture=np.fromfile(capture/'mask-00-000-actor-head2-texture.bgra',np.uint8).reshape(512,512,4)[:,:,[2,1,0,3]]
    blob=bytearray(b'OJSCN003')+struct.pack('<4I13f',len(vertices),512,512,1,*camera)
    blob+=np.asarray(vertices,dtype='<f4').tobytes()+texture.tobytes()+struct.pack('<I',2)
    for first,count,gain in [(0,6,1.),(6,1650,2.)]:
        blob+=struct.pack('<4I8f',first,count,0,1,1.,1.,0.,0.,1.,gain,0.,1.)
    blob+=struct.pack('<2I',512,512)
    output.mkdir(parents=True)
    (output/'head.ojscene').write_bytes(blob)
    Image.fromarray(texture).save(output/'head-texture.png')
    native=np.fromfile(capture/'mask-00-000-actor-head2.bgra',np.uint8).reshape(600,800,4)[:,:,[2,1,0]]
    Image.fromarray(native).save(output/'gog-reference.png')
    report=dict(component='M_Pr_Face.gao',mesh='0x13008483',triangles=550,render_vertices=417,
                referenced_vertices=len(values),texture_size=[512,512],camera=camera,vertex_color_clamp=clamp,
                unclamped_lighting_max=light_max,pixel_center_offset=pixel_offset,
                scene_sha256=hashlib.sha256(blob).hexdigest(),
                inputs={path.name:hashlib.sha256(path.read_bytes()).hexdigest() for path in [meta,meta.with_suffix('.constants'),meta.with_suffix('.stream0'),meta.with_suffix('.indices'),capture/f'{prefix}-reference.txt',capture/'mask-00-000-actor-head2-texture.bgra',capture/'mask-00-000-actor-head2.bgra']},
                limitations=['Frozen captured skeleton pose and per-vertex lighting; no actor animation or dynamic runtime lighting.',
                             'Isolated close-up in captured view coordinates; no menu integration, occluders or fog.',
                             'Base texture copied from the native GPU; native archive texture identity is not resolved.'])
    (output/'manifest.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--unclamped',action='store_true')
    parser.add_argument('--pixel-center-offset',type=float,choices=[0.,.5],default=.5)
    args=parser.parse_args();print(json.dumps(export(args.capture,args.output,not args.unclamped,args.pixel_center_offset),indent=2))
