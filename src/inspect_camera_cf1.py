"""Sample-specific CF1 sequence probe, retaining unknown bytes and semantics."""
import argparse,hashlib,json,math,struct
from pathlib import Path
from probe_menu3d import records
from preview_menu3d_landmarks import SOURCE_HASH


def read_samples(data,start,count,end):
    if count<1 or start<0 or start+count*13!=end or end>len(data):raise ValueError('Invalid sequence extent')
    rows=[]
    for i in range(count):
        offset=start+13*i;tag,x,y,z=struct.unpack_from('<B3f',data,offset)
        if not all(math.isfinite(v) for v in (x,y,z)):raise ValueError('Nonfinite sample')
        rows.append(dict(index=i,payload_offset=offset,leading_byte=tag,triplet=[x,y,z]))
    return rows


def export(source,output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_HASH:raise ValueError('Unsupported source')
    by={r['key']:r for r in records(raw)};r=by['0x30000CF1'];data=raw[r['offset']+12:r['end']]
    if len(data)!=624:raise ValueError('Unexpected CF1 extent')
    count=struct.unpack_from('<I',data,70)[0];samples=read_samples(data,80,count,496)
    output.mkdir(parents=True,exist_ok=False)
    (output/'CF1.bin').write_bytes(data)
    report=dict(source_sha256=SOURCE_HASH,key=r['key'],record_offset=r['offset'],payload_size=len(data),
                samples=samples,leading_byte_sum=sum(s['leading_byte'] for s in samples),
                unknown_prefix_hex=data[:80].hex(),unknown_suffix_hex=data[496:].hex(),
                suffix_record_differences=[i for i,(a,b) in enumerate(zip(data[512:568],data[568:624])) if a!=b],
                limitations=['Sample-specific boundaries','Leading byte is not a verified timestamp',
                             'Triplets are not confirmed positions or angles','No coordinate space, duration or interpolation established'])
    (output/'sequence.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    lines=['index,payload_offset,leading_byte,x,y,z']
    lines += [','.join(map(str,[s['index'],s['payload_offset'],s['leading_byte'],*s['triplet']])) for s in samples]
    (output/'sequence.csv').write_text('\n'.join(lines)+'\n',encoding='ascii')
    # Plot against ordinal index, not an invented time scale.
    colors=['#d99954','#66b5df','#a7c777'];parts=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="600" viewBox="0 0 900 600">','<rect width="900" height="600" fill="#181c24"/>','<text x="30" y="30" fill="white">CF1: raw float components versus sample index (not time)</text>']
    values=[v for s in samples for v in s['triplet']];lo=min(values);hi=max(values)
    for component,color in enumerate(colors):
        points=' '.join(f"{50+s['index']*800/(count-1):.2f},{540-(s['triplet'][component]-lo)*460/(hi-lo):.2f}" for s in samples)
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2"/>')
        parts.append(f'<text x="{50+component*240}" y="575" fill="{color}">component {component+1}</text>')
    parts.append('</svg>');(output/'components.svg').write_text('\n'.join(parts),encoding='utf8')
    print('Samples:',count,'Leading-byte sum:',report['leading_byte_sum'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
