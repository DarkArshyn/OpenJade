"""Bounded eight-byte token inspection of selected camera behavior candidates."""
import argparse,hashlib,json,struct
from collections import Counter
from pathlib import Path
from probe_menu3d import records
from inspect_global_camera_links import HASH
KEYS=['0xB60024DE','0xB6002512','0x080009C9']


def tokens(data):
    if len(data)<8:raise ValueError('Truncated header')
    opaque,size=struct.unpack_from('<II',data)
    if size%8 or size>len(data)-8:raise ValueError('Invalid token extent')
    result=[]
    for offset in range(8,8+size,8):
        operand,tag=struct.unpack_from('<II',data,offset)
        result.append(dict(payload_offset=offset,operand=operand,tag=tag,category=tag>>24,low24=tag&0xffffff))
    return dict(opaque_header=opaque,declared_bytes=size,tokens=result,trailing_hex=data[8+size:].hex())


def common_run(a,b,ia,ib):
    def equal(i,j):return (a[i]['operand'],a[i]['tag'])==(b[j]['operand'],b[j]['tag'])
    if not equal(ia,ib):return None
    left=0;right=1
    while ia-left>0 and ib-left>0 and equal(ia-left-1,ib-left-1):left+=1
    while ia+right<len(a) and ib+right<len(b) and equal(ia+right,ib+right):right+=1
    return dict(first_offset=a[ia-left]['payload_offset'],second_offset=b[ib-left]['payload_offset'],token_count=left+right)


def export(source,output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH:raise ValueError('Unsupported source')
    records_list=records(raw);blocks={}
    for key in KEYS:
        matches=[r for r in records_list if r['key']==key]
        if len(matches)!=1:raise ValueError('Ambiguous record')
        r=matches[0];blocks[key]=tokens(raw[r['offset']+12:r['end']])
        blocks[key]['record_offset']=r['offset']
        blocks[key]['categories']=dict(Counter(t['category'] for t in blocks[key]['tokens']))
        blocks[key]['field_candidates']=[t for t in blocks[key]['tokens'] if (t['operand'],t['tag']) in [(1508,0x14000022),(1716,0x14000022),(1720,0x14000025)]]
    a=blocks[KEYS[1]]['tokens'];b=blocks[KEYS[2]]['tokens'];runs=[]
    for value in [1508,1716]:
        aa=[i for i,t in enumerate(a) if (t['operand'],t['tag'])==(value,0x14000022)]
        bb=[i for i,t in enumerate(b) if (t['operand'],t['tag'])==(value,0x14000022)]
        if len(aa)!=1 or len(bb)!=1:raise ValueError('Ambiguous comparison anchor')
        runs.append(dict(field_offset=value,**common_run(a,b,aa[0],bb[0])))
    output.mkdir(parents=True,exist_ok=False)
    (output/'tokens.json').write_text(json.dumps(dict(source_sha256=HASH,blocks=blocks,common_runs=runs,limitations=['Token categories are numeric, not decoded opcode names','Operand roles, control flow and runtime effects unverified','Tail bytes retained without interpretation']),indent=2),encoding='utf8')
    print(json.dumps(runs))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
