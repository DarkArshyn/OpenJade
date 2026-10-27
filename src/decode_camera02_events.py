"""Decode the bounded, stripped-PC third Camera02 track without executing it."""
import struct


def decode_events(data):
    if len(data) != 624:
        raise ValueError('Expected frozen CF1 size')
    if struct.unpack_from('<HHIII', data, 496) != (0x14, 0xffff, 104, 0, 2):
        raise ValueError('Unsupported stripped-PC event track header')
    rows = []
    elapsed = 0
    for start in (512, 568):
        duration, flags, count = struct.unpack_from('<HHI', data, start)
        if flags != 0x41 or count != 6:
            raise ValueError('Unsupported event key')
        nodes = []
        for offset in range(start + 8, start + 56, 8):
            operand, tag = struct.unpack_from('<II', data, offset)
            nodes.append(dict(offset=offset, operand=operand, tag=tag))
        rows.append(dict(offset=start, duration_ticks=duration,
                         start_seconds=elapsed / 60, flags=flags, nodes=nodes))
        elapsed += duration
    return dict(offset=496, end=624, flags=0x14, target=0xffff,
                object_key=0, payload_allocation=104, keys=rows,
                duration_seconds=elapsed / 60,
                identical_instructions=[(x['operand'], x['tag']) for x in rows[0]['nodes']] ==
                [(x['operand'], x['tag']) for x in rows[1]['nodes']])


if __name__ == '__main__':
    import argparse, json
    from pathlib import Path
    from link_menu_camera_behaviors import checked_read, unique_record, MENU_HASH
    from probe_menu3d import records
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    raw=checked_read(a.source,MENU_HASH)
    _,data=unique_record(raw,records(raw),0x30000cf1)
    result=decode_events(data);result['source_sha256']=MENU_HASH
    with a.output.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2);f.write('\n')
