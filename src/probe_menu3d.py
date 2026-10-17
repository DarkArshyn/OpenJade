"""Read-only record inventory for the two observed decoded menu3D resources.

Record boundaries are validated; payload semantics remain unknown.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def records(data):
    offset=0;result=[]
    while offset<len(data):
        if len(data)-offset<12:raise ValueError('Truncated header at '+str(offset))
        size,marker,key=struct.unpack_from('<III',data,offset)
        if marker!=0xEEFFC099:raise ValueError('Unexpected marker at '+str(offset))
        end=offset+12+size
        if end>len(data):raise ValueError('Truncated payload at '+str(offset))
        payload=data[offset+12:end]
        names=[{'offset':offset+12+m.start(),'text':m.group().decode('ascii')}
               for m in re.finditer(rb'[A-Za-z0-9_@. -]{3,}\.gao',payload)]
        result.append(dict(offset=offset,end=end,size=size,key=f'0x{key:08X}',
                           prefix_hex=payload[:16].hex(),names=names))
        offset=end
    return result


def inspect(wow,wol):
    big=wow.read_bytes();small=wol.read_bytes();r=records(big);s=records(small)
    # This particular WOL payload consists of fifteen key/type pairs.
    if len(s)!=1 or s[0]['size']%8:raise ValueError('Unexpected WOL layout')
    pairs=[dict(offset=o,key=f'0x{struct.unpack_from("<I",small,o)[0]:08X}',type_hex=small[o+4:o+8].hex())
           for o in range(12,len(small),8)]
    keys={item['key'] for item in r}
    for pair in pairs:pair['matching_wow_record_key']=pair['key'] in keys
    return dict(schema=1,inputs=[dict(path=str(p.resolve()),sha256=hashlib.sha256(d).hexdigest(),length=len(d)) for p,d in [(wow,big),(wol,small)]],
                wow_records=r,wol_records=s,wol_pairs=pairs,
                limitations=['Key matches are not proof of runtime loading semantics','Payload geometry and camera fields are not decoded'])


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('wow',type=Path);parser.add_argument('wol',type=Path)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    report=inspect(args.wow,args.wol)
    with args.output.open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
    print('Validated',len(report['wow_records']),'WOW records and',len(report['wol_pairs']),'WOL pairs.')
