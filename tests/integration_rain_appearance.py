"""Compare local native rain draw captures to the independent appearance reference."""
import argparse,collections,json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_rain_appearance import appearance

def compare(directory):
    counts=collections.Counter();draws=0
    for path in sorted(directory.glob('rain-v-*.vb')):
        raw=path.read_bytes();particles=path.with_suffix('.particles').read_bytes();d=path.with_suffix('.descriptor').read_bytes()
        if len(d)!=0x164 or len(particles)%48 or len(raw)!=len(particles)//48*216:raise ValueError('Invalid capture extent')
        if struct.unpack_from('<I',d,0x14)[0]!=0x08020241 or d[0xf5:0xf7]!=b'\0\0':raise ValueError('Unsupported rain flags/axes')
        colors=[struct.unpack_from('<I',d,o)[0] for o in [0xe8,0xe0,0xe4,0xec]]
        matrix=[1,0,0,0,0,0,-1,0,0,1,0,0,0,0,0,1]
        for j in range(len(particles)//48):
            particle=struct.unpack_from('<I11f',particles,j*48);counts[particle[0]]+=1
            for k,(position,uv,argb) in enumerate(appearance(particle,matrix,colors)):
                actual=struct.unpack_from('<6fI2f',raw,(j*6+k)*36)
                if actual[:3]!=position or actual[7:]!=uv or actual[6]!=argb:raise AssertionError(f'{path.name}: particle {j}, corner {k}')
        draws+=1
    if not draws or set(counts)!={0,1,2}:raise ValueError('Need captures covering all three phases')
    return dict(draws=draws,phase_counts=dict(counts),vertices=sum(counts.values())*6,exact_match=True)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path)
    print(json.dumps(compare(p.parse_args().directory),indent=2))
