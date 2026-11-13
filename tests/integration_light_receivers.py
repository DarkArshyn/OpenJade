"""Resolve captured dynamic-light receivers through native load bindings (read-only)."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from probe_menu3d import records
from inspect_menu_scene_links import static_links


def verify(captures, sources, previous=None):
    resources = {}
    provenance = []
    for source in sources:
        raw = source.read_bytes()
        provenance.append(dict(path=str(source), sha256=hashlib.sha256(raw).hexdigest()))
        for row in records(raw):
            payload = raw[row['offset']+12:row['end']]
            key = int(row['key'], 16)
            resources.setdefault(key, set()).add(payload)
    raw = (captures/'light-identify-registry.bin').read_bytes()
    assert len(raw) == 5000*20
    registry = list(struct.iter_unpack('<5I', raw))
    raw = (captures/'light-identify-accumulated.bin').read_bytes()
    assert len(raw) % 8 == 0
    calls = list(struct.iter_unpack('<2I', raw))
    counts = Counter(pointer for _, pointer in calls)
    assert len(counts) == 11 and set(counts.values()) == {31}
    result = []
    for pointer in sorted(counts):
        dump = (captures/f'light-identify-object-{pointer:08x}.txt').read_text()
        roots = {line.split()[0]: [int(v, 16) for v in line.split()[1:]]
                 for line in dump.splitlines() if line.split()[0] in ('object', 'owner', 'instance', 'mesh')}
        assert roots['object'][0] == pointer
        owner_pointer, instance, mesh_pointer = roots['owner'][0], roots['instance'][0], roots['mesh'][0]
        assert roots['instance'][1] == mesh_pointer
        owner_keys = {key for key, target, callback, flags, value in registry
                      if value == owner_pointer and callback == 0x0067df50}
        mesh_keys = {key for key, target, callback, flags, value in registry
                     if value == mesh_pointer and callback == 0x0043f120}
        assert len(owner_keys) == len(mesh_keys) == 1
        owner_key, mesh_key = next(iter(owner_keys)), next(iter(mesh_keys))
        assert len(resources[owner_key]) == len(resources[mesh_key]) == 1, 'Ambiguous required resource'
        owner = next(iter(resources[owner_key]))
        assert owner[:4] == b'.gao'
        length = struct.unpack_from('<I', owner, 16)[0]
        assert 0 < length <= 200 and 20+length <= len(owner)
        name = owner[20:20+length].rstrip(b'\0').decode('ascii')
        mesh = next(iter(resources[mesh_key]))
        assert struct.unpack_from('<I', mesh)[0] == 1
        vertices = struct.unpack_from('<I', mesh, 16)[0]
        assert vertices == roots['mesh'][3]
        assert sorted(frame for frame, p in calls if p == pointer) == list(range(0, 361, 12))
        labels = set()
        for resource_key, candidates in resources.items():
            for candidate in candidates:
                if candidate[:4] != b'.gao':
                    continue
                try:
                    links = static_links(candidate)
                except (ValueError, KeyError, struct.error):
                    continue
                if int(links['mesh'], 16) == mesh_key:
                    labels.add((resource_key, links['name']))
        assert len(labels) == 1, 'Ambiguous mesh label'
        label_key, label = next(iter(labels))
        result.append(dict(receiver=f'0x{pointer:08X}', owner=f'0x{owner_key:08X}', name=name,
                           mesh=f'0x{mesh_key:08X}', label=label, label_key=f'0x{label_key:08X}', vertices=vertices, calls=counts[pointer]))
    assert Counter(r['name'] for r in result) == {'Prince.gao': 9, 'Prince_Head_LowRes.gao': 1, 'Prince_Holder_WAY.gao': 1}
    if previous:
        raw=(previous/'hangfire-light-prepared.bin').read_bytes()
        assert len(raw)%88 == 0
        sizes={struct.unpack_from('<6I',raw,o)[1]:struct.unpack_from('<6I',raw,o)[4] for o in range(0,len(raw),88)}
        old=list(struct.iter_unpack('<2I',(previous/'hangfire-light-accumulated.bin').read_bytes()))
        assert len(old)==len(calls)
        assert Counter(sizes[p] for p in {p for _,p in old})==Counter(r['vertices'] for r in result)
    return dict(resources=provenance, receivers=result, calls=len(calls),
                limitations=['Addresses are session-local; the older capture cannot uniquely distinguish equal-size meshes.',
                             'An accumulation call is not proof of a nonzero light contribution.'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures',type=Path)
    parser.add_argument('sources',type=Path,nargs='+')
    parser.add_argument('--previous',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.captures,args.sources,args.previous),indent=2))
