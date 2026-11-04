"""Measure splash quads and check packed phase colors against local GOG draw captures."""
import argparse
import collections
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from menu_rain_appearance import UVS, packed_lerp
from menu_rain_parameters import f32


def scaled_alpha(color, factor):
    if factor >= f32(.98):
        return color >> 24
    if factor <= f32(.02):
        return 0
    bits = struct.unpack("<I", struct.pack("<f", factor + 49152.))[0]
    alpha = color >> 24
    return sum(alpha >> shift for shift in range(1, 6) if bits & (1 << (8-shift)))


def measure(directory):
    counts = collections.Counter()
    examples = {}
    geometry_error = 0.
    draws = sorted(directory.glob("splash-draw-*.vb"))
    state_log = (directory / "splash-draw-draws.txt").read_text().splitlines()
    states = []
    for line in state_log:
        if line.startswith("frame "):
            states.append({})
        elif line.startswith("state "):
            _, key, value = line.split()
            states[-1][int(key)] = int(value)
    expected = {27:1,19:5,20:6,7:1,14:0,15:0,28:1,168:7,171:1,23:4,206:0}
    assert len(states) == len(draws) and all(all(s.get(k)==v for k,v in expected.items()) for s in states)
    for path in draws:
        meta = path.with_suffix(".txt").read_text().splitlines()
        assert "lock 00000000" in meta and "stride 36" in meta[0]
        assert all(f"tss 0 {k} {v} hr 00000000" in meta for k,v in [(1,5),(2,2),(3,0),(4,4),(5,2),(6,0)])
        data = path.read_bytes()
        particles = path.with_suffix(".particles").read_bytes()
        desc = path.with_suffix(".descriptor").read_bytes()
        assert len(desc)==356 and struct.unpack_from("<I",desc,20)[0]==0x20149
        colors = [struct.unpack_from("<I",desc,i)[0] for i in [232,224,228,236]]
        assert len(particles)%48==0 and len(data)==len(particles)//48*216
        for j,(phase,*v) in enumerate(struct.iter_unpack("<I11f",particles)):
            counts[phase]+=1
            ratio = f32(v[7]*v[8])
            t = f32(1-ratio) if phase==1 else ratio
            endpoints = {0:(2,1),1:(0,1),2:(3,2)}[phase]
            c = packed_lerp(colors[endpoints[0]],colors[endpoints[1]],t)
            alpha = c>>24 if phase==0 else scaled_alpha(c,t)
            argb = (alpha<<24)|((c&255)<<16)|(c&0xff00)|((c>>16)&255)
            q = [struct.unpack_from("<6fI2f",data,216*j+36*k) for k in range(6)]
            assert all(x[6]==argb for x in q), (path,j,hex(argb),hex(q[0][6]))
            assert tuple(x[7:] for x in q)==UVS and q[2][:3]==q[3][:3] and q[0][:3]==q[5][:3]
            errors = [abs(math.dist(q[0][:3],q[1][:3])/2-v[10]),
                      abs(math.dist(q[1][:3],q[2][:3])/2-v[9])]
            errors.extend(abs((q[0][i]+q[2][i])/2-v[i]) for i in range(3))
            geometry_error=max(geometry_error,*errors)
            if phase not in examples and alpha:
                examples[phase]=dict(draw=path.stem,slot=j,vertices=[x[:3] for x in q],argb=f"{argb:08X}")
    assert set(counts)=={0,1,2} and geometry_error<1e-4
    return dict(draws=len(draws),phase_counts=dict(counts),vertices=6*sum(counts.values()),maximum_geometry_error=geometry_error,examples=examples)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory",type=Path)
    print(json.dumps(measure(parser.parse_args().directory),indent=2))

