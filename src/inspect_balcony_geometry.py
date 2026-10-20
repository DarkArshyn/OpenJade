"""Read the two observed compact balcony GAOs, not arbitrary GAO versions."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from probe_menu3d import records
from resolve_camera_function_bodies import HASH


def inspect_payload(data):
    if len(data) < 20 or data[:16] != bytes.fromhex('2e67616f0a0000000800000020a00000'):
        raise ValueError('Unsupported GAO header or flags')
    length = struct.unpack_from('<I', data, 16)[0]
    if length < 1 or len(data) != length + 148:
        raise ValueError('Unexpected compact GAO extent')
    name_bytes = data[20:20+length]
    if not name_bytes.endswith(b'.gao\0') or b'\0' in name_bytes[:-1]:
        raise ValueError('Invalid GAO name')
    name = name_bytes[:-1].decode('ascii')
    matrix_offset = 30 + length
    bounds_offset = matrix_offset + 68
    matrix = struct.unpack_from('<16fI', data, matrix_offset)
    bounds = struct.unpack_from('<6f', data, bounds_offset)
    if not all(math.isfinite(x) for x in (*matrix[:16], *bounds)):
        raise ValueError('Nonfinite geometry')
    if any(bounds[i] > bounds[i+3] for i in range(3)):
        raise ValueError('Unordered stored limits')
    return dict(name=name, matrix_offset=matrix_offset,
                translation=list(matrix[12:15]), bounds_offset=bounds_offset,
                lower=list(bounds[:3]), upper=list(bounds[3:]),
                bounds_raw_hex=data[bounds_offset:bounds_offset+24].hex(),
                tail_offset=bounds_offset+24,
                tail_raw_hex=data[bounds_offset+24:].hex())


def export(source, output):
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != HASH:
        raise ValueError('Unsupported source hash')
    inventory = records(data)
    result = []
    for key in ('0x30000D63', '0x3C00144D'):
        matches = [r for r in inventory if r['key'] == key]
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous selected GAO')
        r = matches[0]
        result.append(dict(key=key, record_offset=r['offset'],
                           **inspect_payload(data[r['offset']+12:r['end']])))
    with output.open('x', encoding='utf8') as stream:
        json.dump(dict(source_sha256=HASH, objects=result,
                       limitations=['Stored bounds only; runtime mutation and activation unresolved',
                                    'No world-space conversion or active camera selection inferred']),
                  stream, indent=2, allow_nan=False)
    print('Verified stored bounds in two balcony GAOs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    export(args.source, args.output)
