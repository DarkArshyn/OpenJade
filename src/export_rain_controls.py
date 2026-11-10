"""Export bounded native rain controls and pixels from the frozen menu only."""
import hashlib, struct
from inspect_menu_palms import HASH, records, static_links
from assemble_menu_scene import texture_image
from menu_rain_parameters import decode

def export_rain(source, *, splashes=False, birds=False, pollen=False, fog=False):
    if sum((splashes,birds,pollen,fog))>1: raise ValueError("Select only one effect family")
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
    if pollen or fog:
        if splashes or birds: raise ValueError('Select only one effect family')
        emitters=[('0x30000D26','0x30000D27'),('0x30000D28','0x30000D27')] if fog else [('0x30000D39','0x30000D3B')]
        material,texture,side=('0x2E0051F1','0x2E004FE4',64) if fog else ('0x30000D3C','0x2E00522D',64)
        result=bytearray(b'OJFOGG01' if fog else b'OJPOLL01')
        if struct.unpack_from('<I',payload(material),44)[0]!=int(texture,16):
            raise ValueError('Pollen texture binding mismatch')
    if birds:
        if splashes: raise ValueError('Select only one effect family')
        emitters=[('0x87005402','0x87005403'),('0x87005404','0x87005405')]
        material,texture='0x870025AC','0x870025AD'
        result=bytearray(b'OJBIRD01')
    for key,descriptor in emitters:
        obj=payload(key);link=static_links(obj)
        if link['mesh']!=descriptor or link['material_pack']!=material: raise ValueError('Rain binding mismatch')
        fields=decode(payload(descriptor))
        v=lambda offset:fields[f'{offset:03x}']['value']
        expected=(0x8000004A,5,1,0) if key=="0x87005402" else (0x80000047,10,1,0)
        if (v(0x14),v(8),v(0x1c),v(0x1d))!=((0x80001041,20,1,2) if pollen or fog else expected if birds else (0x20149,20,4,2) if splashes else (0x08020241,150,1,0)): raise ValueError('Unsupported rain mode')
        matrix=struct.unpack_from('<16f',obj,link['matrix_offset'])
        offsets=[0xdc,0x44,0x48,0x50,0x54,0x80,0x84,0x70,0x74,0x78,0x7c,0x8c,0x90,0x94,0x60,0x64,0x68,0x6c]
        result.extend(struct.pack('<16fI18f4I',*matrix,v(8),*(v(o) for o in offsets),*(v(o) for o in [0xe8,0xe0,0xe4,0xec])))
        if birds: result.extend(struct.pack("<4B",v(0xf0),v(0xf1),v(0xf2),v(0x18)))
        if pollen or fog:
            result.extend(struct.pack('<7f',*(v(o) for o in (0x40,0x58,0x5c,0xac,0xb0,0xb4,0xb8))))
        if splashes: result.extend(struct.pack('<3f',v(0x40),v(0x58),v(0x5c)))
    images=[]
    for r in rows:
        if r['key']!=texture: continue
        try: image=texture_image(raw[r['offset']+12:r['end']])
        except (ValueError,struct.error): continue
        images.append(image)
    if len(images)!=1 or images[0].size!=(side,side): raise ValueError('Ambiguous rain texture')
    result.extend(images[0].convert('RGBA').tobytes())
    assert len(result)==(16760 if fog else 16576 if pollen else 4424 if birds else 17736 if splashes else 4416)
    return bytes(result)
