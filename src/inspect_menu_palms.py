"""Bounded palm inventory and native-verified compact deformation component."""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from probe_menu3d import records
from inspect_menu_scene_links import static_links
from menu_primary_geometry import primary_mesh, instance_colors
from resolve_camera_function_bodies import HASH


def suffix_candidate(data):
    """Recognize a repeated 40-byte suffix, retaining raw roles as unknown."""
    if len(data)<40:
        return None
    offset=len(data)-40
    words=struct.unpack_from('<10I',data,offset)
    if words[:3]!=(1,0,25) or words[3] not in (7,15) or words[4]!=0 or words[-2:]!=(0xffffffff,0xffffffff):
        return None
    return dict(payload_offset=offset,raw_words=[f'0x{x:08X}' for x in words],
                float_candidates=list(struct.unpack_from('<3f',data,offset+20)),
                interpretation='Unresolved stream alignment and field semantics; not animation controls')


def decode_compact_palm(data, color_end):
    """Decode only the observed no-cache compact GAO tail, anchored after colors."""
    if color_end<0 or len(data)!=color_end+82:
        raise ValueError('Unsupported compact palm extent')
    prefix=struct.unpack_from('<6I',data,color_end)
    if prefix!=(1,0xffffffff,0x30000CE4,0x30000CE9,0,0xffffffff):
        raise ValueError('Unsupported post-color references/cache')
    metadata=color_end+24
    if struct.unpack_from('<I',data,metadata)[0]!=1:
        raise ValueError('Missing component')
    start=metadata+18
    kind,header_flags,version,flags=struct.unpack_from('<4I',data,start)
    phase,amplitude,spatial,rate=struct.unpack_from('<4f',data,start+16)
    group,end=struct.unpack_from('<2I',data,start+32)
    if (kind,header_flags,version)!=(1,0,25) or flags not in (7,15) or (group,end)!=(0xffffffff,0xffffffff):
        raise ValueError('Unsupported palm component')
    if not all(math.isfinite(v) for v in (phase,amplitude,spatial,rate)):
        raise ValueError('Non-finite deformation parameter')
    return dict(payload_offset=start,reader='006ACCD0',update='006AB5A0',
        type=kind,version=version,flags=flags,initial_phase=phase,
        amplitude=amplitude,spatial_factor=spatial,phase_rate_factor=rate,
        group_filter=group,affected_coordinates='Y/Z driven by X' if flags==7 else 'X driven by Y and Z',
        timing_status='Phase increment = rate factor * 30 * effective engine seconds')


def inspect(raw):
    if hashlib.sha256(raw).hexdigest()!=HASH:
        raise ValueError('Unsupported frozen scene')
    inventory=records(raw)
    by={}
    for row in inventory:
        by.setdefault(row['key'],[]).append(row)
    def payload(key):
        rows=by.get(key,[])
        if len(rows)!=1: raise ValueError('Missing or ambiguous key '+key)
        row=rows[0]
        return raw[row['offset']+12:row['end']]
    palms=[];wind=[]
    for row in inventory:
        data=raw[row['offset']+12:row['end']]
        if data[:4]!=b'.gao':continue
        n=struct.unpack_from('<I',data,16)[0]
        name=data[20:20+n].rstrip(b'\0').decode('ascii')
        if name=='wind.gao':
            wind.append(dict(key=row['key'],name=name,record_offset=row['offset'],payload_size=len(data)))
        if not name.startswith('Menu3D_palm'):continue
        link=static_links(data)
        vertices,triangles,groups,ids,count,colors,layout=primary_mesh(payload(link['mesh']))
        # Byte matches are candidates only, including possible matches in color data.
        matches=[]
        for key in ('0x30000CE4','0x30000CE9','0x30000D35','0x30000CF1'):
            needle=struct.pack('<I',int(key,16));start=0
            while True:
                p=data.find(needle,start)
                if p<0:break
                matches.append(dict(key=key,payload_offset=p));start=p+1
        suffix=suffix_candidate(data)
        if suffix: suffix['absolute_offset']=row['offset']+12+suffix['payload_offset']
        rgb,color_offset=instance_colors(data,link['link_offset'],count)
        component=None;reason=None
        try:
            if color_offset is None: raise ValueError('Missing instance colors')
            if link['flags']!=0x97000: raise ValueError('Unsupported GAO flags')
            component=decode_compact_palm(data,color_offset+count*4)
        except ValueError as error:reason=str(error)
        palms.append(dict(key=row['key'],record_offset=row['offset'],payload_size=len(data),
            **link,primary_vertices=count,triangles=len(triangles),geometry_bones=layout['bones'],
            suffix_candidate=suffix,component=component,component_exclusion=reason,key_byte_matches=matches))
    return dict(source_sha256=HASH,palms=palms,wind_objects=wind,
        limitations=['No palm animation implemented',
        'Zero geometry bones does not exclude procedural deformation or external animation',
        'Suffix scan alone does not establish runtime links; bounded component decode uses the color-end cursor',
        'wind.gao name is not proof that it drives these palms'])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();result=inspect(a.source.read_bytes())
    with a.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2)
    print(len(result['palms']),'palms;',sum(bool(x['suffix_candidate']) for x in result['palms']),'repeated suffixes;',len(result['wind_objects']),'wind objects')
