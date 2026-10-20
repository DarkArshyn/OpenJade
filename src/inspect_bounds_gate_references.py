"""Inventory one field identifier in two frozen camera resources, read-only."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from probe_menu3d import records
from resolve_camera_function_bodies import HASH as MENU_HASH
from inspect_global_camera_links import HASH as GLOBAL_HASH

IDENTIFIER = 0xC4E1F69A


def find_hits(data):
    """Search only complete payloads; retain unaligned matches without interpretation."""
    needle = struct.pack('<I', IDENTIFIER)
    hits = []
    for record in records(data):
        base = record['offset'] + 12
        payload = data[base:record['end']]
        offset = payload.find(needle)
        while offset >= 0:
            hits.append(dict(key=record['key'], record_offset=record['offset'],
                             payload_offset=offset, absolute_offset=base+offset))
            offset = payload.find(needle, offset+1)
    return hits


def export(menu, global_camera, output):
    results = []
    for path, expected in ((menu, MENU_HASH), (global_camera, GLOBAL_HASH)):
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Unsupported source hash')
        results.append(dict(source_sha256=expected, hits=find_hits(data)))
    with output.open('x', encoding='utf8') as stream:
        json.dump(dict(identifier=f'0x{IDENTIFIER:08X}', resources=results,
                       limitations=['Raw identifier matches are not field writes',
                                    'Offset-based and indirect access need not contain this identifier',
                                    'Only the two supplied frozen resources are covered']),
                  stream, indent=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('menu', type=Path)
    parser.add_argument('global_camera', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    export(args.menu, args.global_camera, args.output)
