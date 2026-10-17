"""Fixed-sample texture hypotheses; synthetic DDS headers, top level only."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from PIL import Image
from probe_menu3d import records


def export(source,output):
    raw=source.read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    if digest!='96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb':
        raise ValueError('Unsupported sample')
    by={r['key']:r for r in records(raw)}
    output.mkdir(parents=True,exist_ok=False)
    manifest={'source_sha256':digest,'interpretation':'Candidate codecs and top-level offset; original container semantics unverified','textures':[]}
    for key,block,code,codec in [('0x30000C67',8,b'DXT1',1),('0x30000C66',16,b'DXT5',3)]:
        r=by[key];data=raw[r['offset']+12:r['end']]
        width,height=struct.unpack_from('<II',data,44)
        if (width,height)!=struct.unpack_from('<HH',data,12):raise ValueError('Dimension copies disagree')
        size=((width+3)//4)*((height+3)//4)*block
        if 56+size>len(data):raise ValueError('Truncated candidate image')
        packed=data[56:56+size]
        header=[124,0x81007,height,width,size,0,1]+[0]*11+[32,4,int.from_bytes(code,'little'),0,0,0,0,0]+[0x1000,0,0,0,0]
        (output/(key+'.dds')).write_bytes(b'DDS '+struct.pack('<31I',*header)+packed)
        (output/(key+'-record.bin')).write_bytes(data)
        (output/(key+'-remainder.bin')).write_bytes(data[56+size:])
        image=Image.frombytes('RGBA',(width,height),packed,'bcn',codec)
        image.save(output/(key+'.png'))
        manifest['textures'].append(dict(key=key,record_offset=r['offset'],payload_data_offset=56,width=width,height=height,
            candidate_format=code.decode(),top_level_bytes=size,remainder_bytes=len(data)-56-size,
            rgba_sha256=hashlib.sha256(image.tobytes()).hexdigest(),extrema=image.getextrema()))
    (output/'candidates.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
