"""Check private GOG light-ablation captures without modifying game resources."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from probe_menu3d import records
from inspect_menu_scene_links import static_links


def verify(captures, sources):
    prefix = 'light-ablation2'
    resources = {}
    provenance = []
    for source in sources:
        raw = source.read_bytes()
        provenance.append(dict(path=str(source), sha256=hashlib.sha256(raw).hexdigest()))
        for row in records(raw):
            resources.setdefault(int(row['key'], 16), set()).add(raw[row['offset']+12:row['end']])
    registry = list(struct.iter_unpack('<5I', (captures/f'{prefix}-registry.bin').read_bytes()))
    assert len(registry) == 5000

    def binding(pointer, callback):
        keys = {key for key, _, cb, _, value in registry if value == pointer and cb == callback}
        assert len(keys) == 1, 'Missing or ambiguous resource binding'
        return keys.pop()

    def resource(key):
        assert len(resources[key]) == 1, 'Ambiguous required resource'
        return next(iter(resources[key]))

    def resource_name(key):
        raw = resource(key)
        assert raw[:4] == b'.gao'
        length = struct.unpack_from('<I', raw, 16)[0]
        assert 0 < length < 200 and 20+length <= len(raw)
        return raw[20:20+length].rstrip(b'\0').decode('ascii')

    selected = {}
    receiver = None
    for line in (captures/f'{prefix}-selected.txt').read_text().splitlines():
        fields = line.split()
        if fields[0] == 'receiver':
            receiver = (int(fields[1]), int(fields[2], 16))
            assert fields[-2:] == ['count', '3']
            selected[receiver] = []
        elif fields[0] == 'light':
            slot, pointer, descriptor = int(fields[1]), int(fields[2], 16), int(fields[3], 16)
            key = binding(pointer, 0x67df50)
            assert key == (0x30000ce2, 0x30000cf4, 0x30000d57)[slot]
            selected[receiver].append((descriptor, int(fields[7], 16), resource_name(key)))
        else:
            raise AssertionError('Unexpected light selection record')
    slots = list(struct.iter_unpack('<6I', (captures/f'{prefix}-slots.bin').read_bytes()))
    slot_groups = {}
    for frame, pointer, descriptor, color, kind, slot in slots:
        slot_groups.setdefault((frame, pointer), []).append((descriptor, color, kind, slot))
    assert set(selected) == set(slot_groups)
    for key, group in slot_groups.items():
        assert [row[3] for row in group] == [0, 1, 2, 3]
        assert [row[2] for row in group] == [1, 3, 3, 1]
        assert [(row[0], row[1]) for row in group[:3]] == [row[:2] for row in selected[key]]
        assert group[3][1] == 0x40404040
    cpu = captures/f'{prefix}-deltas.bin'
    assert not cpu.exists() or cpu.stat().st_size == 0
    result, excluded = [], []
    for path in sorted(captures.glob(f'{prefix}-replay-*.txt')):
        lines = path.read_text().splitlines()
        header = lines[0].split()
        pointer, frame, triangles = int(header[1], 16), int(header[3]), int(header[7])
        width, height = map(int, header[-2:])
        index = int(path.stem.rsplit('-', 1)[1])
        assert frame == 120
        if (width, height) != (800, 600):
            excluded.append(dict(draw=index, size=[width, height], reason='No supported BGRA readback'))
            continue
        assert all(f'variant {variant} drawhr 00000000' in lines for variant in range(8))
        assert int(next(line.split()[1] for line in lines if line.startswith('shader ')), 16)
        constants = {int(line.split()[1]): list(map(float, line.split()[2:]))
                     for line in lines if line.startswith('constant ')}
        for slot, (_, color, _, _) in enumerate(slot_groups[(frame, pointer)]):
            expected = [(color >> shift & 255)/255 for shift in (0, 8, 16)] + [1.0]
            assert np.allclose(constants[28+slot*4], expected, atol=1e-7, rtol=0)
        roots = {line.split()[0]: [int(value, 16) for value in line.split()[1:]]
                 for line in (captures/f'{prefix}-object-{pointer:08x}.txt').read_text().splitlines()
                 if line.split()[0] in ('mesh', 'owner', 'instance')}
        assert roots['instance'][1] == roots['mesh'][0]
        mesh = binding(roots['mesh'][0], 0x43f120)
        assert struct.unpack_from('<I', resource(mesh), 16)[0] == roots['mesh'][3]
        owner = resource_name(binding(roots['owner'][0], 0x67df50))
        labels = set()
        for candidates in resources.values():
            for raw in candidates:
                if raw[:4] != b'.gao':
                    continue
                try:
                    links = static_links(raw)
                except (ValueError, KeyError, struct.error):
                    continue
                if int(links['mesh'], 16) == mesh:
                    labels.add(links['name'])
        assert len(labels) == 1
        images = []
        for variant in range(8):
            raw = (captures/f'mask-120-{index:03d}-{prefix}-v{variant}.bgra').read_bytes()
            assert len(raw) == width*height*4
            images.append(np.frombuffer(raw, np.uint8).reshape(height, width, 4).astype(np.int16))
        assert np.array_equal(images[0], images[6]), 'Repeated baseline differs'
        statistics = []
        for variant in (1, 2, 3, 4, 5, 7):
            delta = images[0][:, :, :3] - images[variant][:, :, :3]
            mask = np.any(delta != 0, axis=2)
            y, x = np.where(mask)
            statistics.append(dict(variant=variant, pixels=int(mask.sum()),
                                   max_delta=int(np.abs(delta).max()),
                                   rgb_sum=[int(value) for value in delta.sum(axis=(0, 1))[::-1]],
                                   bounds=[int(x.min()), int(y.min()), int(x.max()), int(y.max())] if mask.any() else None))
        result.append(dict(draw=index, receiver=f'0x{pointer:08X}', mesh=f'0x{mesh:08X}',
                           name=labels.pop(), owner=owner, triangles=triangles, statistics=statistics))
    assert len(result) == 24 and len(excluded) == 22
    assert len({row['receiver'] for row in result}) == 11
    summary = []
    for name in dict.fromkeys(row['name'] for row in result):
        draws = [row for row in result if row['name'] == name]
        summary.append(dict(name=name, draws=len(draws),
                            max_delta=[max(stat['max_delta'] for row in draws for stat in row['statistics'] if stat['variant'] == variant)
                                       for variant in (1, 2, 3, 4, 5, 7)]))
    return dict(resources=provenance, selected_samples=len(selected), gpu_uploads=len(slots),
                frames=sorted({key[0] for key in selected}), summary=summary, draws=result, excluded=excluded,
                limitations=['Per-draw color-target differences before later passes, not final displayed pixel attribution.',
                             'Zero means no measurable RGB change in this pose at 800x600, not a globally inactive light.',
                             'Differences across draws or lights are not additive physical intensities.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('captures', type=Path)
    parser.add_argument('sources', type=Path, nargs='+')
    args = parser.parse_args()
    print(json.dumps(verify(args.captures, args.sources), indent=2))
