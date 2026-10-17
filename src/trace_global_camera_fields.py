"""Locate typed field-offset candidates without interpreting behavior opcodes."""
import argparse,hashlib,json,struct
from pathlib import Path
from probe_menu3d import records
from inspect_global_camera_links import HASH
FIELDS=[('0x2D0ED330',1508,0x22),('0xA61FCA47',1716,0x22),('0x39449276',1720,0x25)]


def occurrences(data,needle):
    start=0
    while True:
        offset=data.find(needle,start)
        if offset<0:return
        yield offset
        start=offset+1


def inspect(source):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH:raise ValueError('Unsupported source')
    rs=records(raw)
    lists=[r for r in rs if r['key']=='0xB60024E2']
    if len(lists)!=1:raise ValueError('Ambiguous definition list')
    r=lists[0];d=raw[r['offset']+12:r['end']]
    if len(d)%8:raise ValueError('Invalid link list')
    linked={f'0x{struct.unpack_from("<I",d,i)[0]:08X}':d[i+4:i+8].decode('ascii') for i in range(0,len(d),8)}
    results=[]
    for identifier,value,tag in FIELDS:
        declarations=[];candidates=[]
        for r in rs:
            data=raw[r['offset']+12:r['end']]
            for o in occurrences(data,struct.pack('<I',int(identifier,16))):
                declarations.append(dict(record_key=r['key'],record_offset=r['offset'],payload_offset=o))
            if linked.get(r['key']) not in ['.ofc','.ttt']:continue
            for o in occurrences(data,struct.pack('<I',value)):
                following=struct.unpack_from('<I',data,o+4)[0] if o+8<=len(data) else None
                candidates.append(dict(record_key=r['key'],record_offset=r['offset'],type_tag=linked[r['key']],payload_offset=o,
                  following_word=following,matching_low_type=following is not None and (following&0xffff)==tag,
                  context_start=max(0,o-12),context_hex=data[max(0,o-12):o+20].hex()))
        results.append(dict(identifier=identifier,definition_value_offset=value,expected_low_type=tag,identifier_occurrences=declarations,offset_candidates=candidates))
    return dict(source_sha256=HASH,fields=results,limitations=['Byte matches are candidates, not decoded instructions','No field names, read/write direction or execution order established','Record duplicates are preserved'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();report=inspect(a.source)
    with a.output.open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
