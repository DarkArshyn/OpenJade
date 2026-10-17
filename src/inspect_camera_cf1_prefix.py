"""Inspect candidate packed rotations in the frozen Camera02 CF1 prefix."""
import argparse,json,math,struct
from pathlib import Path


def rotations(data,start=22,count=4,end=62):
    if count<1 or start<0 or start+count*10!=end or end>len(data):raise ValueError('Invalid rotation extent')
    result=[]
    for i in range(count):
        offset=start+i*10;word,*q=struct.unpack_from('<H4h',data,offset)
        norm=math.sqrt(sum(v*v for v in q))
        if abs(norm-32767)>2:raise ValueError('Not a unit-scale quaternion candidate')
        result.append(dict(payload_offset=offset,opaque_leading_word=word,signed_components=q,
                           norm=norm,scaled_components=[v/32767 for v in q]))
    return result


def export(source,output):
    from hashlib import sha256
    from preview_menu3d_landmarks import SOURCE_HASH
    from probe_menu3d import records
    raw=source.read_bytes()
    if sha256(raw).hexdigest()!=SOURCE_HASH:raise ValueError('Unsupported source')
    record=next(r for r in records(raw) if r['key']=='0x30000CF1')
    d=raw[record['offset']+12:record['end']]
    if len(d)!=624:raise ValueError('Unexpected payload extent')
    count=struct.unpack_from('<I',d,12)[0];q=rotations(d,count=count)
    report=dict(source_sha256=SOURCE_HASH,rotations=q,
                first_word_u16=struct.unpack_from('<H',d)[0],
                candidate_sections=[dict(start=4,end=62,count=count,stored_word=struct.unpack_from('<I',d,8)[0],hypothetical_expanded_stride=12),
                 dict(start=62,end=496,count=struct.unpack_from('<I',d,70)[0],stored_word=struct.unpack_from('<I',d,66)[0],hypothetical_expanded_stride=16),
                 dict(start=496,end=624,count=struct.unpack_from('<I',d,508)[0],stored_word=struct.unpack_from('<I',d,500)[0],hypothetical_expanded_stride=52)],
                limitations=['Quaternion component order and handedness unknown','Leading words are opaque; first is 0x1010',
                             'No verified interpolation or clock','Expanded strides are inferred, not decoded',
                             'No quaternion applied to Camera02; local/global composition unknown'])
    output.mkdir(parents=True,exist_ok=False)
    (output/'prefix.json').write_text(json.dumps(report,indent=2),encoding='utf8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
