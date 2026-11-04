"""Export bounded native rain controls and pixels from the frozen menu only."""
import hashlib, struct
from inspect_menu_palms import HASH, records, static_links
from assemble_menu_scene import texture_image
from menu_rain_parameters import decode

def export_rain(source, *, splashes=False):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH: raise ValueError('Unsupported rain source')
    rows=records(raw)
    def payload(key):
        found=[r for r in rows if r['key']==key]
        if len(found)!=1: raise ValueError('Ambiguous rain record '+key)
        r=found[0];return raw[r['offset']+12:r['end']]
    splash_keys=[0x2E00E1B1,*range(0x2E00E1B5,0x2E00E1BC)]
    emitters=[(f'0x{key:08X}','0x2E00E1B2') for key in splash_keys] if splashes else [('0x2E00E1AD','0x2E00E1B3'),('0x2E00E1AF','0x2E00E1B4')]
    material='0x2E004F14' if splashes else '0x2E005783'
    texture='0x2E00581E' if splashes else '0x2E005781'
    side=64 if splashes else 32
    result=bytearray(b'OJSPLH01' if splashes else b'OJRAIN01')
    for key,descriptor in emitters:
        obj=payload(key);link=static_links(obj)
        if link['mesh']!=descriptor or link['material_pack']!=material: raise ValueError('Rain binding mismatch')
        fields=decode(payload(descriptor))
        v=lambda offset:fields[f'{offset:03x}']['value']
        if (v(0x14),v(8),v(0x1c),v(0x1d))!=((0x20149,20,4,2) if splashes else (0x08020241,150,1,0)): raise ValueError('Unsupported rain mode')
        matrix=struct.unpack_from('<16f',obj,link['matrix_offset'])
        offsets=[0xdc,0x44,0x48,0x50,0x54,0x80,0x84,0x70,0x74,0x78,0x7c,0x8c,0x90,0x94,0x60,0x64,0x68,0x6c]
        result.extend(struct.pack('<16fI18f4I',*matrix,v(8),*(v(o) for o in offsets),*(v(o) for o in [0xe8,0xe0,0xe4,0xec])))
        if splashes: result.extend(struct.pack('<3f',v(0x40),v(0x58),v(0x5c)))
    images=[]
    for r in rows:
        if r['key']!=texture: continue
        try: image=texture_image(raw[r['offset']+12:r['end']])
        except (ValueError,struct.error): continue
        images.append(image)
    if len(images)!=1 or images[0].size!=(side,side): raise ValueError('Ambiguous rain texture')
    result.extend(images[0].convert('RGBA').tobytes())
    assert len(result)==(17736 if splashes else 4416)
    return bytes(result)
