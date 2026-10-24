"""Cross-check selected native camera bindings and frozen resource chains, read-only."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from prepare_camera_native_followup import pe_sections
from probe_menu3d import records
from inspect_camera_behavior_tokens import tokens
from inspect_global_camera_links import field_table

EXE_HASH = '6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9'
MENU_HASH = '96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'
GLOBAL_HASH = '68c1323218f0c5479c5064a53ac3c60a329e45cba6c11c7f08affbb649484582'


def checked_read(path, expected):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Unsupported input hash: ' + str(path))
    return data


def unique_record(raw, inventory, key):
    matches = [r for r in inventory if r['key'] == f'0x{key:08X}']
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous selected record: ' + hex(key))
    r = matches[0]
    return r, raw[r['offset'] + 12:r['end']]


def binding(table, key):
    if len(table) % 8:
        raise ValueError('Truncated native binding table')
    matches = [(i, pointer) for i, (identifier, pointer) in
               enumerate(struct.iter_unpack('<II', table)) if identifier == key]
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous binding: ' + hex(key))
    index, pointer = matches[0]
    return dict(key=f'0x{key:08X}', index=index, pointer=f'0x{pointer:08X}',
                entry_va=f'0x{0x7f28c0 + index * 8:08X}')


def chain(raw, inventory, gao, wrapper, behavior, instance, body):
    gr, gd = unique_record(raw, inventory, gao)
    _, wd = unique_record(raw, inventory, wrapper)
    _, bd = unique_record(raw, inventory, behavior)
    unique_record(raw, inventory, instance)
    unique_record(raw, inventory, body)
    if wd != struct.pack('<II', behavior, instance):
        raise ValueError('Unexpected behavior/instance pair')
    if len(bd) % 8 or (body, b'.ofc') not in list(struct.iter_unpack('<I4s', bd)):
        raise ValueError('Missing typed OFC link')
    needle = struct.pack('<I', wrapper)
    positions = [i for i in range(len(gd) - 3) if gd[i:i + 4] == needle]
    if len(positions) != 1:
        raise ValueError('Missing or ambiguous GAO reference')
    return dict(gao=f'0x{gao:08X}', names=gr['names'],
                wrapper=f'0x{wrapper:08X}', reference_offset=positions[0],
                behavior=f'0x{behavior:08X}', instance=f'0x{instance:08X}',
                body=f'0x{body:08X}')


def export(exe, menu, global_camera, output):
    binary = checked_read(exe, EXE_HASH)
    m = checked_read(menu, MENU_HASH)
    g = checked_read(global_camera, GLOBAL_HASH)
    base, sections = pe_sections(binary)
    if base != 0x400000:
        raise ValueError('Unexpected image base')
    start, size = 0x7f28c0, 0x3c7 * 8
    section = next(s for s in sections if base + s['rva'] <= start and
                   start + size <= base + s['rva'] + s['size'])
    offset = section['offset'] + start - base - section['rva']
    table = binary[offset:offset + size]
    bindings = [binding(table, k) for k in (0x3200043d, 0x03002045, 0xb60024f7)]
    if [r['pointer'] for r in bindings] != ['0x0051DFA0', '0x005A6D10', '0x00605670']:
        raise ValueError('Unexpected selected bindings')
    mr, gr = records(m), records(g)
    chains = [chain(g, gr, 0xcc000403, 0x057cc738, 0xb60024e2, 0x057cc737, 0x3200043d),
              chain(m, mr, 0xb60024ed, 0xb60024ef, 0xb60024e4, 0xb60024ee, 0xb60024f7)]
    _, body = unique_record(g, gr, 0x3200043d)
    nodes = tokens(body)['tokens']
    expected = {32: (0, 0x01000021), 40: (0x604, 0x14000022),
                48: (0, 0x030030d9), 56: (0, 0x01000021), 64: (0, 0x030030d4)}
    for at, pair in expected.items():
        match = [t for t in nodes if t['payload_offset'] == at]
        if len(match) != 1 or (match[0]['operand'], match[0]['tag']) != pair:
            raise ValueError('Activation motif changed')
    _, definition = unique_record(g, gr, 0xb60024e1)
    fields = field_table(definition)
    fov = [f for f in fields['fields'] if f['offset'] == 0x604]
    if len(fov) != 1:
        raise ValueError('Missing unique FOV definition field')
    at = fields['values_start'] + 0x604
    presence = {label: {row['key']: sum(r['key'] == row['key'] for r in inventory)
                       for row in bindings}
                for label, inventory in [('menu', mr), ('global_camera', gr)]}
    report = dict(hashes=dict(exe=EXE_HASH, menu=MENU_HASH, global_camera=GLOBAL_HASH),
                  bindings=bindings, chains=chains, record_presence=presence,
                  activation_tokens=nodes,
                  fov_definition=dict(field=fov[0], raw_hex=definition[at:at+4].hex(),
                                      float32=struct.unpack_from('<f', definition, at)[0]),
                  limitations=['Static association, not observed runtime activation',
                               '03002045 absent from the two selected containers',
                               'Definition FOV is not a verified live menu value',
                               'Camera02 is not established as the attached object'])
    output.mkdir(parents=True, exist_ok=False)
    (output / 'links.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print('Validated three native bindings, two object chains and the activation motif')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('exe', 'menu', 'global_camera', 'output'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    export(args.exe, args.menu, args.global_camera, args.output)
