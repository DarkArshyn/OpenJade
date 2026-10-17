"""Trace global-camera instance fields against an explicit definition candidate."""
import argparse,hashlib,json,struct
from pathlib import Path
from probe_menu3d import records
HASH='68c1323218f0c5479c5064a53ac3c60a329e45cba6c11c7f08affbb649484582'


def field_table(d):
    if len(d)<12:raise ValueError('Truncated header')
    first,size=struct.unpack_from('<II',d)
    if size%12 or size>len(d)-12:raise ValueError('Invalid descriptor extent')
    n=size//12;mark=8+size;value_header=mark+4+4*n
    if value_header+4>len(d):raise ValueError('Truncated identifier table')
    length=struct.unpack_from('<I',d,value_header)[0];start=value_header+4
    if start+length>len(d):raise ValueError('Truncated value area')
    fields=[]
    for i in range(n):
        offset,count,tag=struct.unpack_from('<III',d,8+12*i)
        if offset>=length:raise ValueError('Offset beyond value area')
        identifier=struct.unpack_from('<I',d,mark+4+4*i)[0]
        fields.append(dict(identifier=f'0x{identifier:08X}',offset=offset,count=count,tag=tag))
    return dict(opaque_first_word=first,fields=fields,values_start=start,values_length=length,trailing_hex=d[start+length:].hex())


def extract_value(d,table,field):
    kind=field['tag']&0xffff
    width={0x22:4,0x25:12}.get(kind)
    if width is None or field['count']!=1:raise ValueError('Unsupported selected field')
    offset=field['offset']
    if offset+width>table['values_length']:raise ValueError('Field extends beyond values')
    start=table['values_start']+offset
    return dict(payload_offset=start,raw_hex=d[start:start+width].hex(),floats=list(struct.unpack_from('<'+'f'*(width//4),d,start)))


def export(source,output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH:raise ValueError('Unsupported resource')
    rs=records(raw)
    def payload(key):
        matches=[r for r in rs if r['key']==key]
        if len(matches)!=1:raise ValueError('Missing or ambiguous selected key')
        r=matches[0];return raw[r['offset']+12:r['end']]
    wrapper=payload('0x057CC738')
    if wrapper!=struct.pack('<II',0xB60024E2,0x057CC737):raise ValueError('Wrapper changed')
    descriptor=payload('0xB60024E2')
    if len(descriptor)%8:raise ValueError('Invalid key/type list')
    links=[dict(offset=i,key=f'0x{struct.unpack_from("<I",descriptor,i)[0]:08X}',type=descriptor[i+4:i+8].decode('ascii')) for i in range(0,len(descriptor),8)]
    instance=payload('0x057CC737');definition=payload('0xB60024E1')
    a=field_table(instance);b=field_table(definition);comparison=[]
    for field in a['fields']:
        matches=[f for f in b['fields'] if f['identifier']==field['identifier']]
        if len(matches)!=1:raise ValueError('Ambiguous field identity')
        match=matches[0]
        if field['tag']!=(match['tag']&0xffff):raise ValueError('Base field tags differ')
        comparison.append(dict(identifier=field['identifier'],instance=extract_value(instance,a,field),definition=extract_value(definition,b,match),instance_tag=field['tag'],definition_tag=match['tag']))
    other=payload('0x55000013');target=payload('0x55000012')
    if struct.unpack_from('<I',other)[0]!=0x55000012:raise ValueError('Secondary reference changed')
    report=dict(source_sha256=HASH,wrapper_keys=['0xB60024E2','0x057CC737'],definition_links=links,instance_table=a,definition_table=b,field_comparison=comparison,
                secondary=dict(source_key='0x55000013',target_key='0x55000012',source_hex=other.hex(),target_hex=target.hex()),
                limitations=['Instance/definition roles are inferred','Field names and runtime effects unknown','Upper tag bits retained, not interpreted','Secondary encoding not decoded'])
    output.mkdir(parents=True,exist_ok=False)
    (output/'global-camera-links.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
