"""Inspect selected balcony bounds fields; archived values are not runtime state."""
import argparse,hashlib,json,struct
from pathlib import Path
from probe_menu3d import records
from inspect_global_camera_links import field_table
from resolve_camera_function_bodies import HASH
OFFSETS=(0,172,276,396,436,464,512)


def value(data,table,field):
    kind=field['tag']&0xffff
    width={0x21:4,0x28:4,0x25:12}.get(kind)
    if width is None or field['count']!=1: raise ValueError('Unsupported selected field')
    offset=field['offset'];start=table['values_start']+offset
    if offset<0 or offset+width>table['values_length'] or start+width>len(data):
        raise ValueError('Field exceeds value area')
    raw=data[start:start+width]
    return dict(raw_hex=raw.hex(),value=list(struct.unpack('<3f',raw)) if kind==0x25 else struct.unpack('<I',raw)[0])


def export(source,output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH: raise ValueError('Unsupported source')
    rs=records(raw)
    def load(key):
        found=[r for r in rs if r['key']==key]
        if len(found)!=1: raise ValueError('Missing or ambiguous key')
        r=found[0];data=raw[r['offset']+12:r['end']]
        return data,field_table(data)
    data,definition=load('0xB60024E8');rows=[]
    for offset in OFFSETS:
        found=[f for f in definition['fields'] if f['offset']==offset]
        if len(found)!=1: raise ValueError('Ambiguous definition field')
        f=found[0];instances=[]
        for key in ('0x30000D61','0x3C00144B'):
            d,t=load(key);matches=[g for g in t['fields'] if g['identifier']==f['identifier']]
            if len(matches)>1: raise ValueError('Ambiguous instance field')
            if matches and (matches[0]['tag']&0xffff)!=(f['tag']&0xffff): raise ValueError('Field type mismatch')
            instances.append(dict(key=key,present=bool(matches),field=matches[0] if matches else None,
                                  stored=value(d,t,matches[0]) if matches else None))
        rows.append(dict(model_offset=offset,field=f,definition=value(data,definition,f),instances=instances))
    output.mkdir(parents=True,exist_ok=False)
    (output/'fields.json').write_text(json.dumps(dict(source_sha256=HASH,fields=rows,
        limitations=['Missing instance entries are not runtime zero values','No active object or runtime bounds verified']),indent=2),encoding='utf8')
    print('Verified seven definition fields against two balcony instances')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
