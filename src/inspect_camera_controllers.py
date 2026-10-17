"""Bounded inspection of camera-linked descriptor/value blocks; semantics are hypotheses."""
import argparse,hashlib,json,struct,math
from pathlib import Path
from probe_menu3d import records
from preview_menu3d_landmarks import SOURCE_HASH


def parse_block(data):
    if len(data)<12:raise ValueError('Truncated block')
    zero,size=struct.unpack_from('<II',data)
    if zero or size%12 or size>len(data)-12:raise ValueError('Unsupported descriptor header')
    n=size//12; marker=8+size; values_size_at=marker+4+4*n
    if values_size_at+4>len(data):raise ValueError('Truncated identifiers')
    value_size=struct.unpack_from('<I',data,values_size_at)[0];start=values_size_at+4
    if start+value_size>len(data):raise ValueError('Truncated values')
    fields=[]
    for i in range(n):
        offset,count,tag=struct.unpack_from('<III',data,8+12*i)
        next_offset=struct.unpack_from('<I',data,8+12*(i+1))[0] if i+1<n else value_size
        if count!=1 or not 0<=offset<next_offset<=value_size:raise ValueError('Invalid field extent')
        chunk=data[start+offset:start+next_offset]
        identifier=struct.unpack_from('<I',data,marker+4+4*i)[0]
        field=dict(index=i,identifier=f'0x{identifier:08X}',type_tag=tag,value_offset=offset,payload_offset=start+offset,raw_hex=chunk.hex())
        if len(chunk)==4:
            field['uint32']=struct.unpack('<I',chunk)[0]
            f=struct.unpack('<f',chunk)[0]
            field['float32']=f if math.isfinite(f) else None
        if len(chunk)==12:field['float32_triplet']=list(struct.unpack('<3f',chunk))
        fields.append(field)
    return dict(descriptor_count=n,opaque_word=struct.unpack_from('<I',data,marker)[0],values_start=start,values_size=value_size,fields=fields,trailing_hex=data[start+value_size:].hex())


def export(source,output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_HASH:raise ValueError('Unsupported sample')
    by={r['key']:r for r in records(raw)}
    def payload(k):
        r=by[k];return raw[r['offset']+12:r['end']]
    result={}
    for key in ['0x30000D61','0x3C00144B','0x30000CF2']:
        block=parse_block(payload(key));block['record_offset']=by[key]['offset']
        for field in block['fields']:
            target=f"0x{field.get('uint32',0):08X}"
            if target in by:
                field['matching_record_key']=target;d=payload(target)
                if d[:4]==b'.gao':
                    n=struct.unpack_from('<I',d,16)[0];f=struct.unpack_from('<15f',d,30+n)
                    field['gao_name']=d[20:20+n].split(b'\0')[0].decode('ascii','replace')
                    field['candidate_position']=list(f[12:15])
        result[key]=block
    output.mkdir(parents=True,exist_ok=False)
    (output/'controllers.json').write_text(json.dumps(dict(source_sha256=SOURCE_HASH,blocks=result),indent=2),encoding='utf8')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
