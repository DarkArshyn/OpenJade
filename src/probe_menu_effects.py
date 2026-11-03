"""Read-only focused inventory of rain, birds and flies in the frozen menu."""
import argparse,hashlib,json,re,struct
from pathlib import Path
from probe_menu3d import records
from inspect_menu_scene_links import static_links
from resolve_camera_function_bodies import HASH
from assemble_menu_scene import texture_image
from menu_rain_parameters import decode, summary

def particle_record(data):
    if len(data)!=274 or struct.unpack_from("<2I",data)!=(11,23):
        raise ValueError("Unsupported effect record extent/header")
    # Numeric slots are evidence, not yet named spawn/lifetime parameters.
    return dict(header=[11,23],word_08=struct.unpack_from("<I",data,8)[0],
        word_0c=f"0x{struct.unpack_from('<I',data,12)[0]:08X}",
        sha256=hashlib.sha256(data).hexdigest(),payload_hex=data.hex(),
        native_fields=decode(data),parameters=summary(decode(data)))

def inspect(data):
    if hashlib.sha256(data).hexdigest()!=HASH:raise ValueError("Unsupported menu source")
    rows=records(data);by={}
    for r in rows:by.setdefault(r['key'],[]).append(r)
    def payload(key):
        found=by.get(key,[])
        if len(found)!=1:raise ValueError("Missing or ambiguous record "+key)
        r=found[0];return data[r['offset']+12:r['end']]
    objects=[];effects={};materials={}
    for r in rows:
        d=data[r['offset']+12:r['end']]
        if d[:4]!=b'.gao' or not any(re.search(r'rain|bird|mouch|flys',n['text'],re.I) for n in r['names']):continue
        row=dict(key=r['key'],record_offset=r['offset'],names=r['names'])
        try:link=static_links(d)
        except ValueError as e:
            row['direct_link_status']=str(e);objects.append(row);continue
        row.update(link)
        start=link['matrix_offset'];row['stored_matrix']=list(struct.unpack_from('<16f',d,start))
        mesh=payload(link['mesh']);row['geometry_header']=list(struct.unpack_from('<2I',mesh))
        if row['geometry_header']==[11,23]:effects[link['mesh']]=particle_record(mesh)
        mat=payload(link['material_pack'])
        if len(mat)==48 and struct.unpack_from('<2I',mat)==(5,6):
            texture=f"0x{struct.unpack_from('<I',mat,44)[0]:08X}"
            targets=by.get(texture,[])
            info=dict(texture=texture,local_texture_matches=len(targets),material_hex=mat.hex())
            decoded=[]
            info['texture_records']=[dict(offset=t['offset'],size=t['size']) for t in targets]
            for t in targets:
                tex=data[t['offset']+12:t['end']]
                try: image=texture_image(tex)
                except (ValueError,struct.error):continue
                decoded.append(dict(offset=t['offset'],dimensions=list(image.size),sha256=hashlib.sha256(tex).hexdigest()))
            info['decoded_candidates']=decoded
            materials[link['material_pack']]=info
        objects.append(row)
    rain=[effects[k] for k in ('0x2E00E1B3','0x2E00E1B4')]
    a,b=(bytes.fromhex(r['payload_hex']) for r in rain)
    return dict(source_sha256=HASH,objects=objects,effect_records=effects,materials=materials,
        rain_descriptor_different_byte_offsets=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y],
        limitations=['Stored matrices are not resolved hierarchy transforms','Record presence does not prove active emission or visibility',
        'Version-23 fields match the native reader; full scene activation, random spawning and appearance are not validated',
        'No animation or renderer settings are changed'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();report=inspect(a.source.read_bytes())
    with a.output.open('x',encoding='utf-8') as f:json.dump(report,f,indent=2,allow_nan=False)
    print(len(report['objects']),'objects;',len(report['effect_records']),'effect descriptors')
    print('Rain descriptor differing bytes:',report['rain_descriptor_different_byte_offsets'])
