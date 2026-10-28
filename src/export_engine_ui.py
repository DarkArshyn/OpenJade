"""Bake local MFT/DDS menu layers and 60 Hz Camera02 poses for the native viewer."""
import argparse,json,struct,sys,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from simulation_screens import Screens,Model
from decode_camera02_tracks import decode
from sample_camera02_animation import sample_pose
from link_menu_camera_behaviors import checked_read,unique_record,MENU_HASH
from probe_menu3d import records

# Pages: main, options, credits notice, quit, feature-not-ported notice.
ACTIONS={('route','new'):0,('route','options'):1,('route','credits'):2,('route','quit'):3,
         ('route','profiles'):4,('back',):5,('answer','Yes'):7,('answer','No'):8}

def export(report,source,out):
    raw=checked_read(source,MENU_HASH);rs=records(raw)
    _,cam=unique_record(raw,rs,0x30000cf0);_,cf1=unique_record(raw,rs,0x30000cf1)
    n=struct.unpack_from('<I',cam,16)[0];capture=np.array(struct.unpack_from('<16f',cam,30+n)).reshape(4,4);capture[:,3]=[0,0,0,1]
    tracks=decode(cf1);screens=Screens(report);model=Model()
    frames=[];pages=[]
    for page in ['main','options','credits','quit','notice']:
        def render(hover):
            screens.model=model;screens.hover=hover;screens.hits=[];screens.image=Image.new('RGBA',(800,600))
            if page=='main':
                screens.image.alpha_composite(screens.logo.resize((480,120),Image.Resampling.LANCZOS),(20,20))
                for label,y,dest in [('Start New Game',162,'new'),('Load Saved Game',225,'load'),('Options',287,'options'),('Credits',350,'credits'),('Quit',412,'quit')]: screens.text(label,375,y,18,action=('route',dest),disabled=dest=='load')
                screens.text('Change Profile',62,536,18,action=('route','profiles'))
            elif page=='options':
                screens.text('Options',31,20,28)
                for label,y,dest in [('Controls',170,'keyboard'),('Game',232,'game'),('Graphics',295,'effects'),('Sound',357,'sound')]: screens.text(label,375,y,18,action=('route',dest))
                screens.text('Back',62,536,18,action=('back',))
            elif page=='quit':
                screens.box((100,225,590,153));screens.text('Quit the OpenJade preview?',400,255,18,'center')
                for label,x in [('Yes',255),('No',540)]:screens.text(label,x,343,18,'center',('answer',label))
            else:
                screens.box((90,220,620,180))
                labels=['OpenJade - independent research preview','Original game credits are not integrated.'] if page=='credits' else ['This feature is not integrated yet.','Detailed menus remain in the Python simulation.']
                for i,label in enumerate(labels):screens.text(label,400,250+45*i,15,'center',width=590)
                screens.text('Back',62,536,18,action=('back',))
            return screens.image,screens.hits
        image,hits=render(None);page_frames=[image]
        for action,_ in hits:page_frames.append(render(action)[0])
        pages.append([(ACTIONS.get(tuple(action),6),rect) for action,rect in hits])
        for frame in page_frames:
            for y in (0,512):
                for x in (0,512):
                    tile=Image.new('RGBA',(512,512));tile.paste(frame.crop((x,y,min(x+512,800),min(y+512,600))),(0,0));frames.append(tile.tobytes())
    blob=bytearray(b'OJUI0001');blob.extend(struct.pack('<I',len(pages)))
    for page in pages:
        blob.extend(struct.pack('<I',len(page)))
        for action,rect in page:blob.extend(struct.pack('<I4f',action,*rect))
    blob.extend(struct.pack('<I',len(frames)))
    for frame in frames:blob.extend(frame)
    blob.extend(struct.pack('<I',541))
    for i in range(541):
        pose=sample_pose(capture,tracks,i/60)
        values=[*pose[3,:3],*-pose[0,:3],*pose[2,:3],*-pose[1,:3],59.3790785093875]
        blob.extend(struct.pack('<13f',*values))
    out.mkdir(parents=True,exist_ok=False);(out/'menu.ojui').write_bytes(blob)
    (out/'manifest.json').write_text(json.dumps(dict(source_sha256=MENU_HASH,pages=pages,texture_layers=len(frames),camera_samples=541,sample_rate=60,duration=9,
        limitations=['UI layouts are research reconstructions','Only main/options navigation and quit confirmation are native; settings/profiles remain Python-only','Camera baked with existing native-derived sampler; UI trigger is explicitly wired by OpenJade','No gameplay or original cutscene execution']),indent=2))
    print(f'{len(pages)} pages, {len(frames)} texture layers, 541 camera samples')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('report',type=Path);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.report,a.source,a.output)
