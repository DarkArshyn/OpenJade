"""Inspect selected camera dynamic-function descriptors without executing game code."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from probe_menu3d import records
from inspect_camera_behavior_tokens import tokens
from inspect_global_camera_links import HASH


def parse_table(data):
    """Read the observed compact 88-byte form, not the 100-byte runtime object."""
    if len(data) < 4:
        raise ValueError('Truncated table header')
    count = struct.unpack_from('<I', data)[0]
    if len(data) != 4 + count * 88:
        raise ValueError('Unsupported compact descriptor extent')
    result = []
    for index in range(count):
        offset = 4 + index * 88
        words = struct.unpack_from('<22I', data, offset)
        if words[4] > 16:
            raise ValueError('Parameter count exceeds fixed type array')
        result.append(dict(payload_offset=offset, stored_index=words[0],
                           identifier=words[1], model=words[2], file=words[3],
                           parameter_count=words[4], return_type=words[5],
                           parameter_types=list(words[6:6+words[4]]), raw_words=list(words)))
    return result


def export(source, output):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASH:
        raise ValueError('Unsupported source hash')
    inventory = records(raw)
    by_key = {}
    for record in inventory:
        by_key.setdefault(record['key'], []).append(record)
    def payload(key):
        found = by_key.get(key, [])
        if not found:
            raise ValueError('Missing or ambiguous linked key: ' + key)
        candidates = {raw[r['offset']+12:r['end']] for r in found}
        if len(candidates) != 1:
            raise ValueError('Conflicting duplicate payloads: ' + key)
        r = found[0]
        return raw[r['offset']+12:r['end']]
    links = payload('0xB60024E2')
    if len(links) % 8:
        raise ValueError('Malformed key/type list')
    selected = {0x5b82, 0x5b83}
    matches, definitions, scanned = [], [], []
    for offset in range(0, len(links), 8):
        key, kind = struct.unpack_from('<I4s', links, offset)
        key = f'0x{key:08X}'
        if kind not in (b'.ttt', b'.ofc'):
            continue
        try:
            data = payload(key)
        except ValueError as error:
            scanned.append(dict(key=key, kind=kind.decode(), unresolved=str(error)))
            continue
        if kind == b'.ttt':
            rows = parse_table(data)
            scanned.append(dict(key=key, kind='ttt', count=len(rows)))
            matches.extend(dict(record=key, **r) for r in rows if r['identifier'] in selected)
        elif kind == b'.ofc':
            nodes = tokens(data)['tokens']
            scanned.append(dict(key=key, kind='ofc', count=len(nodes)))
            definitions.extend(dict(record=key, **n) for n in nodes
                               if n['category'] == 0x1c and n['low24'] in selected)
    output.mkdir(parents=True, exist_ok=False)
    report = dict(source_sha256=HASH, linked_records=scanned, duplicate_counts={k:len(v) for k,v in by_key.items() if len(v)>1}, descriptors=matches,
                  definitions=definitions, limitations=['Linked records only',
                  'Model/file values are not resolved resource keys', 'No runtime execution'])
    (output/'descriptors.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(f'{len(matches)} descriptors; {len(definitions)} definitions in linked records')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    export(args.source, args.output)


