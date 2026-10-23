"""Resolve static GAO mesh/material links in the frozen Menu3D resource."""
import argparse, hashlib, json, struct
from pathlib import Path
from probe_menu3d import records
from resolve_camera_function_bodies import HASH


def static_links(d):
    if len(d) < 20 or d[:4] != b'.gao':
        raise ValueError('Not a complete GAO header')
    version, _, flags, n = struct.unpack_from('<4I', d, 4)
    if version != 10 or n < 1 or 20+n > len(d):
        raise ValueError('Unsupported version or name extent')
    name = d[20:20+n]
    if not name.endswith(b'.gao\0') or b'\0' in name[:-1]:
        raise ValueError('Invalid name')
    if not flags & 0x4000:
        raise ValueError('No direct static mesh link')
    offset = n+122+(24 if flags & 0x80000 else 0)
    if offset+8 > len(d):
        raise ValueError('Truncated links')
    mesh, material = struct.unpack_from('<II', d, offset)
    return dict(name=name[:-1].decode('ascii'), flags=flags, link_offset=offset,
                mesh=f'0x{mesh:08X}', material_pack=f'0x{material:08X}',
                matrix_offset=n+30)


def export(source, output):
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != HASH:
        raise ValueError('Unsupported source')
    inventory = records(data)
    by = {}
    for r in inventory:
        by.setdefault(r['key'], []).append(r)
    rows, excluded = [], []
    def payload(r):
        return data[r['offset']+12:r['end']]
    for r in inventory:
        d = payload(r)
        if d[:4] != b'.gao':
            continue
        try:
            item = static_links(d)
        except (ValueError, UnicodeError) as error:
            excluded.append(dict(key=r['key'], reason=str(error)))
            continue
        targets = {}
        for role in ('mesh', 'material_pack'):
            matches = by.get(item[role], [])
            targets[role] = dict(matches=len(matches), offsets=[m['offset'] for m in matches])
        matches = by.get(item['mesh'], [])
        mesh_header = None
        if len(matches) == 1 and len(payload(matches[0])) >= 8:
            mesh_header = list(struct.unpack_from('<2I', payload(matches[0])))
        rows.append(dict(key=r['key'], record_offset=r['offset'], **item,
                         targets=targets, mesh_header=mesh_header,
                         mesh_layout_supported=mesh_header in ([1, 7], [1, 8])))
    report = dict(source_sha256=HASH, objects=rows, excluded=excluded,
                  limitations=['Direct static links only; no indirect object resolution',
                               'Resolved keys do not prove visibility or active scene membership',
                               'No material decoding or transform hierarchy inferred'])
    with output.open('x', encoding='utf8') as stream:
        json.dump(report, stream, indent=2)
    print(len(rows), 'static link candidates;', len(excluded), 'excluded GAOs')
    print(sum(x['mesh_layout_supported'] and all(t['matches']==1 for t in x['targets'].values()) for x in rows), 'unique supported mesh/material pairs')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path); p.add_argument('output', type=Path)
    a=p.parse_args(); export(a.source, a.output)
