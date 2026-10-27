"""Decode the native-verified first two tracks of the frozen Camera02 CF1."""
import argparse,hashlib,json,math,struct
from pathlib import Path
from probe_menu3d import records
from preview_menu3d_landmarks import SOURCE_HASH

def decode(data):
    if len(data)!=624 or struct.unpack_from('<2H',data)!=(3,2):
        raise ValueError('Unsupported CF1 container')
    tracks=[]
    for start,end,flags,count,size,kind in ((4,62,0xbc04,4,48,'packed_rotation'),(62,496,0xba04,32,512,'vector')):
        actual,target,allocation,n=struct.unpack_from('<HHII',data,start)
        if (actual,target,allocation,n)!=(flags,0xffff,size,count):raise ValueError('Unexpected track header')
        pos=start+12;rows=[];elapsed=0;event=None
        for i in range(count):
            off=pos
            fmt='<B' if flags&0x200 else '<H'
            ticks=struct.unpack_from(fmt,data,pos)[0];pos+=struct.calcsize(fmt)
            if i==0:
                event,expanded,payload_flags=struct.unpack_from('<3H',data,pos);pos+=6
                expected=(0x84,12,0x1010) if kind=='packed_rotation' else (0x80,16,1)
                if (event,expanded,payload_flags)!=expected:raise ValueError('Unsupported key payload')
            value_offset=pos
            fmt='<4h' if kind=='packed_rotation' else '<3f'
            values=list(struct.unpack_from(fmt,data,pos));pos+=struct.calcsize(fmt)
            if not all(math.isfinite(x) for x in values):raise ValueError('Nonfinite key')
            rows.append(dict(index=i,duration_offset=off,value_offset=value_offset,duration_ticks=ticks,
                             start_seconds=elapsed/60,duration_seconds=ticks/60,values=values))
            elapsed+=ticks
        if pos!=end:raise ValueError('Track extent mismatch')
        tracks.append(dict(kind=kind,offset=start,end=end,flags=flags,target=target,
                           expanded_payload_bytes=size,event_flags=event,duration_ticks=elapsed,
                           duration_seconds=elapsed/60,keys=rows))
    return dict(tracks=tracks,remaining_offset=496,remaining_hex=data[496:].hex(),
                limitations=['Third track retained raw','No world-space pose or interpolation implemented','Runtime start and phase not captured'])

def export(source,output):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SOURCE_HASH:raise ValueError('Unsupported source')
    rs=records(raw)
    def get(key):
        matches=[r for r in rs if r['key']==key]
        if len(matches)!=1:raise ValueError('Ambiguous resource')
        r=matches[0];return raw[r['offset']+12:r['end']]
    cam=get('0x30000CF0')
    if struct.unpack_from('<I',cam,227)[0]!=0x30000CF1:raise ValueError('Camera02 link changed')
    result=decode(get('0x30000CF1'));result['source_sha256']=SOURCE_HASH
    output.mkdir(parents=True,exist_ok=False)
    (output/'tracks.json').write_text(json.dumps(result,indent=2)+'\n')
    print([(t['kind'],len(t['keys']),t['duration_seconds']) for t in result['tracks']])
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path);a=p.parse_args();export(a.source,a.output)
