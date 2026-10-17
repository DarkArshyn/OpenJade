"""Inventory explicitly supplied decoded resources for camera comparisons; no archive scan."""
import argparse,hashlib,json,struct
from collections import Counter
from pathlib import Path
from probe_menu3d import records


def inspect(path):
    raw=path.read_bytes();items=records(raw);counts=Counter(r['key'] for r in items)
    result=dict(source=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest(),length=len(raw),record_count=len(items),
                duplicate_keys={k:v for k,v in counts.items() if v>1},gao_objects=[],signature_candidates=[])
    for r in items:
        d=raw[r['offset']+12:r['end']]
        if len(d)>=16 and d[6:8]==b'\xff\xff' and 0<struct.unpack_from('<H',d)[0]<10:
            result['signature_candidates'].append(dict(key=r['key'],offset=r['offset'],size=len(d),prefix=d[:24].hex()))
        if d[:4]!=b'.gao' or len(d)<20:continue
        n=struct.unpack_from('<I',d,16)[0]
        if n>len(d)-20:raise ValueError('GAO name exceeds payload')
        name=d[20:20+n].split(b'\0')[0].decode('ascii','replace')
        obj=dict(key=r['key'],name=name,record_offset=r['offset'],links=[])
        if 'cam' in name.lower():
            for offset in range(20+n,len(d)-3):
                key=f'0x{struct.unpack_from("<I",d,offset)[0]:08X}'
                matches=[q for q in items if q['key']==key]
                if matches:
                    # Preserve duplicate record occurrences; never silently pick the last.
                    obj['links'].append(dict(payload_offset=offset,key=key,targets=[dict(record_offset=q['offset'],size=q['size'],prefix_hex=raw[q['offset']+12:min(q['end'],q['offset']+44)].hex()) for q in matches]))
        result['gao_objects'].append(obj)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);p.add_argument('inputs',type=Path,nargs='+')
    a=p.parse_args();report=dict(inputs=[inspect(path) for path in a.inputs],limitations=['Signature matches are not validated track decodes','Key matches do not prove runtime activation'])
    with a.output.open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
