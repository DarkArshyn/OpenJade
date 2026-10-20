"""Trace selected balcony-field uses and the bounds-writing callback."""
import argparse,hashlib,json,struct
from pathlib import Path
from probe_menu3d import records
from inspect_camera_behavior_tokens import tokens
from inspect_global_camera_links import field_table
from resolve_camera_function_bodies import HASH


def callback_tail(data):
    if len(data)<24: raise ValueError('Truncated callback tail')
    fixed=list(struct.unpack_from('<5I',data))
    count=struct.unpack_from('<I',data,20)[0]
    if len(data)!=24+count*4: raise ValueError('Invalid callback extent')
    return dict(fixed=fixed,indexed=list(struct.unpack_from('<'+str(count)+'I',data,24)))


def export(source,output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH: raise ValueError('Unsupported source')
    inventory=records(raw)
    def payload(key):
        found=[r for r in inventory if r['key']==key]
        if len(found)!=1: raise ValueError('Missing or ambiguous selected record')
        r=found[0];return raw[r['offset']+12:r['end']]
    links=payload('0xB60024E9');uses=[];blocks=[];writer=None
    if len(links)%8: raise ValueError('Invalid link extent')
    for off in range(0,len(links),8):
        key,kind=struct.unpack_from('<I4s',links,off)
        if kind!=b'.ofc':continue
        key=f'0x{key:08X}';ts=tokens(payload(key))['tokens'];blocks.append(key)
        if key=='0x3200000F':writer=ts
        for i,n in enumerate(ts):
            if n['category']==0x14 and n['operand'] in (172,276,464,512):
                uses.append(dict(record=key,field=n['operand'],offset=n['payload_offset'],window=ts[max(0,i-2):i+13]))
    if writer is None: raise ValueError('Writer is not linked')
    byoffset={n['payload_offset']:n for n in writer}
    expected=[(32,464,0x14000025),(40,0,0x03001fa5),(48,0,0x02000960),
              (56,512,0x14000025),(64,464,0x14000025),(72,0,0x02000960),
              (80,464,0x14000025),(88,0,0x03002bc3),(96,0,0x02000961),
              (104,512,0x14000025),(112,0,0x03002bc5),(120,0,0x02000961)]
    for off,operand,tag in expected:
        if off not in byoffset or (byoffset[off]['operand'],byoffset[off]['tag'])!=(operand,tag):
            raise ValueError('Bounds writer sequence differs')
    definition=payload('0xB60024E8');table=field_table(definition)
    start=table['values_start']+table['values_length'];callbacks=callback_tail(definition[start:])
    if len(callbacks['indexed'])<=5 or callbacks['indexed'][5]!=0x3200000f:
        raise ValueError('Expected callback link missing')
    output.mkdir(parents=True,exist_ok=False)
    (output/'writers.json').write_text(json.dumps(dict(source_sha256=HASH,linked_blocks=blocks,
        field_uses=uses,writer_tokens=writer,callbacks=callbacks,callback_payload_offset=start,
        direct_writer_offsets=[48,72,96,120],limitations=['Only eight linked blocks inspected',
        'No runtime invocation established','No direct writes to 172/276 identified; indirect writers not excluded']),indent=2),encoding='utf8')
    print(f'{len(blocks)} blocks; {len(uses)} field uses; four verified bound writes; callback index 5')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
