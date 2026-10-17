"""Inspect one frozen camera sample and compare explicit projection hypotheses."""
import argparse, hashlib, json, math, struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from probe_menu3d import records
from preview_menu3d_landmarks import SOURCE_HASH, LANDMARKS, mesh_groups, raster


def vertical_fov(angle, aspect, horizontal):
    if not math.isfinite(angle) or not 0 < angle < math.pi:
        raise ValueError('Angle must be between zero and pi radians')
    if not math.isfinite(aspect) or aspect <= 0:
        raise ValueError('Aspect must be positive')
    return math.degrees(2*math.atan(math.tan(angle/2)/aspect) if horizontal else angle)


def export(source, textures_dir, output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_HASH: raise ValueError('Unsupported sample')
    entries=records(raw); by={r['key']:r for r in entries}
    def payload(key):
        r=by[key];return raw[r['offset']+12:r['end']]
    def transform(key):
        d=payload(key);n=struct.unpack_from('<I',d,16)[0]
        f=np.array(struct.unpack_from('<15f',d,30+n))
        return np.array([f[:3],f[4:7],f[8:11]]),f[12:15]
    camera=payload('0x30000CF0')
    if struct.unpack_from('<I',camera,159)[0]!=0x30000CEF: raise ValueError('Camera reference changed')
    parameters=payload('0x30000CEF')
    if len(parameters)!=24: raise ValueError('Parameter extent changed')
    words=struct.unpack('<4I2f',parameters); angle=words[5]
    objects=[];slots=set()
    for name,key,mesh,h in LANDMARKS:
        vertices,triangles,groups=mesh_groups(payload(mesh),h);basis,pos=transform(key)
        if not np.array_equal(basis,np.eye(3)): raise ValueError('Unsupported object basis')
        objects.append(dict(name=name,vertices=vertices[:,:3]+pos,uv=vertices[:,3:],triangles=triangles,groups=groups))
        slots.update(slot for slot,_ in groups)
    textures={slot:np.asarray(Image.open(textures_dir/f'texture-slot-{slot}.png').convert('RGBA'))
              if (textures_dir/f'texture-slot-{slot}.png').exists() else np.array([[[230,40,180,255]]],dtype=np.uint8)
              for slot in slots}
    basis,pos=transform('0x30000CF0')
    if not np.allclose(basis@basis.T,np.eye(3),atol=1e-5): raise ValueError('Nonorthogonal basis')
    output.mkdir(parents=True,exist_ok=False)
    sheet=Image.new('RGB',(1600,1200));views=[]
    cases=[('baseline',60,basis),('vertical-radians',vertical_fov(angle,4/3,False),basis),
           ('horizontal-radians',vertical_fov(angle,4/3,True),basis),
           ('transposed-basis',vertical_fov(angle,4/3,False),basis.T)]
    for i,(name,fov,axes) in enumerate(cases):
        result,coverage,count=raster(objects,textures,pos,axes,fov)
        ImageDraw.Draw(result).text((12,12),f'{name}: vertical FOV {fov:.3f} / hypothesis',fill='white',font_size=17)
        result.save(output/(name+'.png'));sheet.paste(result,((i%2)*800,(i//2)*600))
        views.append(dict(name=name,vertical_fov_degrees=fov,covered_pixels=coverage,drawn_triangles=count))
    sheet.save(output/'projection-comparison.png')
    references=[]
    for key in ['0x30000CF0','0x30000D63','0x3C00144D','0x30000D62','0x3C00144C','0x30000D61','0x3C00144B']:
        d=payload(key);links=[]
        for offset in range(len(d)-3):
            target=f'0x{struct.unpack_from("<I",d,offset)[0]:08X}'
            if target in by: links.append(dict(payload_offset=offset,target=target))
        references.append(dict(key=key,record_offset=by[key]['offset'],payload_size=len(d),candidate_key_matches=links))
    report=dict(source_sha256=SOURCE_HASH,parameter_key='0x30000CEF',parameter_record_offset=by['0x30000CEF']['offset'],
                parameter_words=list(words),parameter_hex=parameters.hex(),references=references,views=views,
                limitations=['Float semantics not confirmed','Camera activation and controller evaluation unknown',
                             'Byte matches are candidate references, not a complete schema','No lighting or fog',
                             'No image fitting performed; screenshot agreement not established'])
    (output/'camera-projection.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('textures',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args();export(args.source,args.textures,args.output)
