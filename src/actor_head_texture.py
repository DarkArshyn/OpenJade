"""Load the bounded Prince face material and indexed texture from decoded records."""
import hashlib
import struct
import numpy as np
from probe_menu3d import records
from inspect_menu_scene_links import static_links


def load_head_texture(source):
    data=source.read_bytes()
    inventory=records(data)
    used=[]
    def payload(key, size=None):
        matches=[r for r in inventory if r['key']==f'0x{key:08X}' and (size is None or r['size']==size)]
        if len(matches)!=1:
            raise ValueError(f'Missing or ambiguous record {key:08X}')
        r=matches[0]; used.append(dict(key=r['key'],offset=r['offset'],size=r['size']))
        return data[r['offset']+12:r['end']]
    links=static_links(payload(0x13005EEA))
    if links['mesh']!='0x13008483' or links['material_pack']!='0x13005EE2':
        raise ValueError('Unexpected face links')
    pack=payload(0x13005EE2)
    if struct.unpack('<5I',pack)!=(4,0,2,0x1300848A,0x1300848B):
        raise ValueError('Unexpected face material slots')
    material=payload(0x1300848A,48)
    if struct.unpack_from('<2I',material)!=(5,6) or struct.unpack_from('<I',material,44)[0]!=0x1300663D:
        raise ValueError('Unexpected face material texture')
    # The observed bundle includes a header-only declaration and one full payload.
    texture=payload(0x1300663D,349564)
    if struct.unpack_from('<4I',texture,40)!=(1,512,512,6):
        raise ValueError('Unsupported indexed texture layout')
    if struct.unpack_from('<HH',texture,12)!=(512,512):
        raise ValueError('Inconsistent texture dimensions')
    palette_key=struct.unpack_from('<I',texture,56)[0]
    palette=payload(palette_key,1028)
    if struct.unpack_from('<I',palette)[0]!=palette_key:
        raise ValueError('Inconsistent palette identity')
    colors=np.frombuffer(palette,dtype=np.uint8,offset=4).reshape(256,4)[:,[2,1,0,3]]
    levels=[]; offset=60
    for level in range(7):
        size=512>>level; count=size*size
        indices=np.frombuffer(texture,dtype=np.uint8,count=count,offset=offset)
        levels.append(colors[indices].reshape(size,size,4));offset+=count
    if offset!=len(texture):
        raise ValueError('Unexpected texture trailing bytes')
    return levels,dict(source=str(source.resolve()),sha256=hashlib.sha256(data).hexdigest(),
                       records=used,format='indexed BGRA palette',mip_sizes=[list(x.shape[:2]) for x in levels])
