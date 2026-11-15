"""Append the source actor diagnostic to a prepared menu, preserving menu sidecars."""
import argparse,hashlib,json,shutil,struct
from pathlib import Path
import numpy as np
from prince_resources import Resources
from prince_animation import node
from prince_ground import grounded_placement

def read_scene(path):
    raw=path.read_bytes();original=raw;magic=raw[:8];palms=b''
    if magic==b'OJSCN005':
        count=struct.unpack_from('<I',raw,len(raw)-4)[0]
        if not 0<count<=1000000 or len(raw)<80+count*44:raise ValueError('Invalid palm trailer')
        palms=raw[-4-count*44:];raw=raw[:-4-count*44]
    if magic not in (b'OJSCN003',b'OJSCN004',b'OJSCN005'):raise ValueError('Unsupported scene revision')
    nv,w,h,nl=struct.unpack_from('<4I',raw,8);end=76+nv*36+w*h*nl*4
    if len(raw)<end+4:raise ValueError('Truncated scene')
    nd=struct.unpack_from('<I',raw,end)[0];tail=end+4+nd*48
    if tail+nl*8+(nd*8 if magic!=b'OJSCN003' else 0)!=len(raw):raise ValueError('Invalid scene extent')
    return dict(raw=original,palms=palms,nv=nv,w=w,h=h,nl=nl,nd=nd,
        vertices=np.frombuffer(raw,'<f4',nv*9,76).reshape(nv,9).copy(),
        pixels=np.frombuffer(raw,np.uint8,w*h*nl*4,76+nv*36).reshape(nl,h,w,4),
        draws=[bytearray(raw[end+4+i*48:end+4+(i+1)*48]) for i in range(nd)],
        sizes=raw[tail:tail+nl*8],rates=raw[tail+nl*8:] if magic!=b'OJSCN003' else bytes(nd*8))

def assemble(menu,actor,source,output):
    if output.exists():raise FileExistsError(output)
    scene=read_scene(menu);prince=read_scene(actor);r=Resources([source]);placement,parent,name=node(r,0x0F0053D9)
    if parent is not None or name!='Menu3D_TEC_Checkpoint.gao':raise ValueError('Unexpected checkpoint')
    placement,grounding=grounded_placement(r)
    w=max(scene['w'],prince['w']);h=max(scene['h'],prince['h']);layers=scene['nl']+prince['nl']
    if layers>128 or w*h*layers*4>240*1024*1024:raise ValueError('Texture transport limit')
    pixels=np.zeros((layers,h,w,4),np.uint8)
    pixels[:scene['nl'],:scene['h'],:scene['w']]=scene['pixels']
    pixels[scene['nl']:,:prince['h'],:prince['w']]=prince['pixels']
    vertices=prince['vertices'];vertices[:,:3]=(np.c_[vertices[:,:3],np.ones(prince['nv'])]@placement)[:,:3];vertices[:,8]+=scene['nl']
    for draw in prince['draws']:
        first,count,blend,flags=struct.unpack_from('<4I',draw)
        struct.pack_into('<4I',draw,0,first+scene['nv'],count,blend,flags+2) # Native-range vertex fog.
    draws=scene['draws']+prince['draws'];header=bytearray(scene['raw'][:76]);header[:8]=b'OJSCN005' if scene['palms'] else b'OJSCN004'
    struct.pack_into('<4I',header,8,scene['nv']+prince['nv'],w,h,layers)
    raw=header+scene['vertices'].astype('<f4').tobytes()+vertices.astype('<f4').tobytes()+pixels.tobytes()+struct.pack('<I',len(draws))+b''.join(draws)+scene['sizes']+prince['sizes']+scene['rates']+prince['rates']+scene['palms']
    output.mkdir(parents=True);(output/'menu.ojscene').write_bytes(raw)
    for path in menu.parent.glob(menu.stem+'.*'):
        if path.suffix!='.ojscene':shutil.copyfile(path,output/('menu'+path.suffix))
    for suffix in ('.actor','.sheath','.actorlight'):
        shutil.copyfile(actor.with_suffix(suffix),output/('menu'+suffix))
    (output/'menu.placement').write_bytes(b'OJAPL001'+struct.pack('<I16f',scene['nv'],*placement.ravel()))
    report=dict(menu=str(menu.resolve()),actor=str(actor.resolve()),menu_sha256=hashlib.sha256(scene['raw']).hexdigest(),actor_sha256=hashlib.sha256(prince['raw']).hexdigest(),
                scene_sha256=hashlib.sha256(raw).hexdigest(),checkpoint='0F0053D9',placement=placement.tolist(),grounding=grounding,source=r.sources,records=r.used,
                actor_vertex_range=[scene['nv'],scene['nv']+prince['nv']],
                limitations=['Initial menu placement uses the unique source collision intersection; continuous actor collision and movement are not implemented.',
                             'Animation repeats as an isolated diagnostic; no gameplay or native actor activation.',
                             'Animated normals use captured fixed light parameters, not a general scene-light system.'])
    (output/'actor-integration.json').write_text(json.dumps(report,indent=2),encoding='utf-8');return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('menu',type=Path);p.add_argument('actor',type=Path);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();print(json.dumps(assemble(a.menu,a.actor,a.source,a.output),indent=2))
