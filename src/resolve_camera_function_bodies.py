"""Resolve two selected dynamic-function bodies in the frozen Menu3D container."""
import argparse, hashlib, json
from pathlib import Path
from probe_menu3d import records
from inspect_camera_behavior_tokens import tokens
from inspect_camera_function_descriptors import parse_table
HASH='96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'


def function_body(nodes, identifier):
    starts=[i for i,n in enumerate(nodes) if n['tag']==0x1c000000+identifier]
    if len(starts)!=1:
        raise ValueError('Missing or ambiguous function definition')
    start=starts[0]
    stop=next((i for i in range(start+1,len(nodes)) if nodes[i]['category'] in (0x1c,0x1f)),len(nodes))
    body=nodes[start:stop]
    if not body or body[-1]['tag']!=0x1d000000:
        raise ValueError('Function end marker not found before next definition')
    return body


def export(source, output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH: raise ValueError('Unsupported Menu3D hash')
    inventory=records(raw)
    def record(key):
        found=[r for r in inventory if r['key']==key]
        if len(found)!=1: raise ValueError('Ambiguous selected record '+key)
        r=found[0]
        return r,raw[r['offset']+12:r['end']]
    r,data=record('0xB60024E5')
    nodes=tokens(data)['tokens']
    table_candidates=[]
    for candidate in inventory:
        if candidate['key']!='0x08000338': continue
        rows=parse_table(raw[candidate['offset']+12:candidate['end']])
        table_candidates.append((candidate,rows))
    matched=[(r,rows) for r,rows in table_candidates if {0x5b82,0x5b83}.issubset({d['identifier'] for d in rows})]
    if len(matched)!=1: raise ValueError('Ambiguous descriptor table containing both IDs')
    table_record,descriptors=matched[0]
    result=[]
    for identifier in (0x5b82,0x5b83):
        matches=[d for d in descriptors if d['identifier']==identifier]
        if len(matches)!=1: raise ValueError('Ambiguous descriptor')
        d=matches[0]
        if (d['model'],d['file'])!=(0x263c,0x5d): raise ValueError('Unexpected model/file pair')
        result.append(dict(identifier=identifier,descriptor=d,tokens=function_body(nodes,identifier)))
    _,links=record('0xB60024E9')
    import struct
    pairs=[(struct.unpack_from('<I',links,o)[0],links[o+4:o+8]) for o in range(0,len(links),8)]
    if (0xb60024e5,b'.ofc') not in pairs or (0x08000338,b'.ttt') not in pairs:
        raise ValueError('Behavior list does not link body and table')
    chains=[]
    for pairkey,gaokey in [('0x30000D62','0x30000D63'),('0x3C00144C','0x3C00144D')]:
        _,pair=record(pairkey);gao,gdata=record(gaokey)
        if len(pair)!=8 or struct.unpack_from('<I',pair)[0]!=0xb60024e9: raise ValueError('Invalid behavior pair')
        needle=struct.pack('<I',int(pairkey,16));at=gdata.find(needle)
        if at<0: raise ValueError('Missing GAO reference')
        chains.append(dict(gao=gaokey,names=gao['names'],payload_reference_offset=at,pair=pairkey,behavior_list='0xB60024E9'))
    output.mkdir(parents=True,exist_ok=False)
    report=dict(source_sha256=HASH,body_record=r,table_record=table_record,table_occurrences=[dict(offset=c[0]["offset"],count=len(c[1])) for c in table_candidates],functions=result,object_chains=chains,
                limitations=['Cross-reference association, not a general model/file key-conversion formula',
                             'No live loading or object identity verified','5b83 arithmetic not fully decoded'])
    (output/'functions.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('Resolved two definitions and two balcony-object reference chains')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)

