"""Validate initial ambient cache provenance and captured actor shader arithmetic."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from probe_menu3d import records
from replay_actor_vertex_shader import disassemble, program, replay


def verify(folder, scene):
    prefix = folder.name
    registry = list(struct.iter_unpack('<5I', (folder/f'{prefix}-registry.bin').read_bytes()))
    assert len(registry) == 5000
    def key(pointer, callback):
        matches = {row[0] for row in registry if row[2] == callback and row[4] == pointer}
        assert len(matches) == 1
        return matches.pop()
    source = scene.read_bytes()
    resources = {}
    for row in records(source):
        resources.setdefault(int(row['key'], 16), []).append(source[row['offset']+12:row['end']])
    for resource_key, name in [(0x30000cd9, 'Menu3D_FarahRoom_Balcony.gao'), (0x30000ce4, 'Menu3D_LUM_Ambiant.gao')]:
        assert len(resources[resource_key]) == 1
        raw = resources[resource_key][0]
        size = struct.unpack_from('<I', raw, 16)[0]
        assert raw[:4] == b'.gao' and raw[20:20+size].rstrip(b'\0').decode() == name
    assert len(resources[0x30000ce8]) == 1
    assert struct.unpack_from('<I', resources[0x30000ce8][0], 12)[0] == 0x003b2e25
    events = [line.split() for line in (folder/f'{prefix}-events.txt').read_text().splitlines()]
    initial = [row for row in events if row[0] == 'object' and row[4] == 'before' and int(row[11], 16) == 0]
    assert len(initial) == 3
    caches = []
    for before in initial:
        sequence, owner = int(before[1]), int(before[5], 16)
        related = [row for row in events if int(row[1]) == sequence]
        after = next(row for row in related if row[0] == 'object' and row[4] == 'after' and int(row[5], 16) == owner)
        resolved = next(row for row in related if row[0] == 'resolve' and int(row[5], 16) == owner)
        fallback = next(row for row in related if row[0] == 'fallback-source')
        assert int(after[11], 16) != 0 and int(after[13], 16) == 0xff3b2e25
        assert int(resolved[13], 16) == 0x003b2e25
        assert int(resolved[17], 16) == int(fallback[3], 16)
        assert key(int(fallback[3], 16), 0x67df50) == 0x30000cd9
        assert key(int(fallback[7], 16), 0x67df50) == 0x30000ce4
        assert key(int(fallback[9], 16), 0x43f120) == 0x30000ce8
        assert int(fallback[11], 16) == 0x003b2e25
        assert key(int(resolved[15], 16), 0x67df50) == 0xcc000431
        caches.append(dict(owner=f'0x{key(owner, 0x67df50):08X}', sequence=sequence,
                           before='null', after=f'0x{int(after[13],16):08X}'))
    assert {row['owner'] for row in caches} == {'0xCC000431','0x3F000E2F','0x330005EC'}
    arithmetic = replay(folder)
    assert arithmetic['draws'] == 24 and arithmetic['vertices'] == 2434
    assert len({row['receiver'] for row in arithmetic['results']}) == 11
    materials = Counter()
    special = []
    for path in sorted(folder.glob(f'{prefix}-draw-*.txt')):
        lines = path.read_text().splitlines()
        assert 'constants_hr 00000000' in lines and 'vs_hr 00000000' in lines
        target = next(line for line in lines if line.startswith('target ')).split()
        shader = disassemble(path.with_suffix('.vs').read_bytes())
        if target[1:3] == ['256','256']:
            assert 'mov oD0' not in shader
            materials['offscreen_without_diffuse_output'] += 1
            continue
        assert target[1:3] == ['800','600'] and 'mov oD0' in shader
        assert 'state 137 0' in lines
        assert not any(line.startswith('decl ') and line.split()[5] == '10' for line in lines)
        state = {int(line.split()[1]): int(line.split()[2]) for line in lines if line.startswith('state ')}
        stages = {(int(line.split()[1]), int(line.split()[2])): int(line.split()[3]) for line in lines if line.startswith('tss ')}
        if path.with_suffix('.ps').exists():
            assert 'ps_hr 00000000' in lines and 'pixel_constants_hr 00000000' in lines
            text = disassemble(path.with_suffix('.ps').read_bytes())
            constants = np.fromfile(path.with_suffix('.pixelconstants'), '<f4').astype(float).reshape(8,4)
            assert np.allclose(constants[0,:3],np.array([64,71,74])/255,atol=1e-7,rtol=0)
            max_error = 0.
            for alpha in (0., .25, .5, 1.):
                for gain in (0., .25, .75, 1.):
                    first = np.array([.2,.4,.7,alpha]); second = np.array([.8,.5,.3,.6]); diffuse = np.array([gain,.5*gain,.25*gain,1.])
                    output = program(text,dict(t0=first,t1=second,v0=diffuse),constants)['r0']
                    expected = np.r_[2*((1-alpha)*first[:3]*diffuse[:3]+alpha*second[:3]*constants[0,:3]), alpha*second[3]+(1-alpha)*alpha]
                    max_error = max(max_error, float(np.max(np.abs(output-expected))))
            assert max_error < 1e-14
            materials['two_texture_pixel_shader'] += 1
            special.append(dict(draw=path.stem,pixel_math_cases=16,pixel_math_max_error=max_error))
        else:
            assert stages[0,1] == 5 and stages[0,2] == 2 and stages[1,1] == 1
            assert stages[0,4] == 4 and stages[0,5] == 2
            if stages[0,3] == 0:
                materials['texture_times_diffuse_x2'] += 1
            else:
                assert stages[0,3] == 3
                materials['texture_times_factor_x2'] += 1
                special.append(dict(draw=path.stem,texture_factor=f'0x{state[60]:08X}'))
    assert materials == {'offscreen_without_diffuse_output':22,'two_texture_pixel_shader':1,
                         'texture_times_diffuse_x2':22,'texture_times_factor_x2':1}
    return dict(initial_caches=caches,scene_sha256=hashlib.sha256(source).hexdigest(),
                materials=dict(materials),special=special,vertex_arithmetic=arithmetic,
                limitations=['CPU arithmetic replay in double precision; not a measurement of GPU output precision.',
                             'Texture sampling, interpolation, fog and final composited pixels are not replayed.'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture',type=Path);parser.add_argument('scene',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.capture,args.scene),indent=2))
