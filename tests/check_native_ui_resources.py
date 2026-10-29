from pathlib import Path
import struct,json,hashlib
from PIL import Image
import argparse
p=argparse.ArgumentParser(description='Check original logo/cursor pixels in a local OJUI0003 bundle')
p.add_argument('report',type=Path);p.add_argument('textures',type=Path)
a=p.parse_args();report=a.report
b=(report/'menu.ojui').read_bytes();assert b[:8]==b'OJUI0003'
layers,size,count=struct.unpack_from('<IfI',b,8);offset=20
dims=[]
for _ in range(layers):dims.append(struct.unpack_from('<2I',b,offset));offset+=8
n,=struct.unpack_from('<I',b,offset);offset+=4
sizes=struct.unpack_from('<'+'I'*n,b,offset);offset+=n*4;entries={}
for _ in range(count):
 length,=struct.unpack_from('<I',b,offset);offset+=4;name=b[offset:offset+length].decode();offset+=length
 entries[name]=struct.unpack_from('<5I3f',b,offset);offset+=32
results={}
for name,source in [('logo','pop.dds'),('cursor','officialcursor_alpha2_desaturated.dds')]:
 layer,x,y,w,h,*_=entries[name];tw,th=dims[layer];start=offset+layer*512*512*4
 atlas=Image.frombytes('RGBA',(tw,th),b[start:start+tw*th*4]);actual=atlas.crop((x,y,x+w,y+h))
 with Image.open(a.textures/source) as im:expected=im.convert('RGBA')
 assert expected.size==actual.size and expected.tobytes()==actual.tobytes(),name
 results[name]={'dimensions':actual.size,'pixel_identical':True,'rgba_sha256':hashlib.sha256(actual.tobytes()).hexdigest()}
assert sizes==(10,12,14,16,18,20,22,24,26,28,36,48)
print(json.dumps(dict(assets=results,font_sizes=sizes,images=dims),indent=2))
