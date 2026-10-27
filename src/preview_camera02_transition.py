"""Render a bounded Camera02 timeline with a local HTML frame viewer."""
import argparse,json,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import assemble_menu_scene as assembly
from menu_colored_raster import raster
from decode_camera02_tracks import decode
from sample_camera02_animation import sample_pose
from link_menu_camera_behaviors import checked_read,unique_record,MENU_HASH
from probe_menu3d import records
from menu_native_camera_math import projection_angles


def export(source,out):
    raw=checked_read(source,MENU_HASH);rs=records(raw)
    _,cam=unique_record(raw,rs,0x30000cf0)
    _,cf1=unique_record(raw,rs,0x30000cf1)
    n=struct.unpack_from('<I',cam,16)[0]
    capture=np.array(struct.unpack_from('<16f',cam,30+n)).reshape(4,4)
    capture[:,3]=[0,0,0,1]
    tracks=decode(cf1)
    out.mkdir(parents=True,exist_ok=False)
    # Reuse the existing assembler; retain its final fully assembled scene.
    scene={}
    def collect(objects,textures,position,basis,fov,*args,**kwargs):
        scene.update(objects=objects,textures=textures)
        return Image.new('RGB',(800,600)),0,0
    previous=assembly.raster
    try:
        assembly.raster=collect
        assembly.export(source,out/'assembly',yaw=0,pitch=0,fov=59.38)
    finally: assembly.raster=previous
    times=[0,1.5,3,4.5,6,7.5,9]
    fov=projection_angles(1.2999910116195679,800,600)['vertical_degrees']
    poses=[];sheet=Image.new('RGB',(1600,4*630),(24,28,36))
    for i,t in enumerate(times):
        pose=sample_pose(capture,tracks,t)
        img,coverage,count=raster(scene['objects'],scene['textures'],pose[3,:3],pose[:3,:3],fov)
        img.save(out/f'frame-{i}.png')
        x,y=(i%2)*800,(i//2)*630
        sheet.paste(img,(x,y+30));ImageDraw.Draw(sheet).text((x+12,y+8),f'Camera02 / t={t:g}s / diagnostic lighting',fill='white')
        poses.append(dict(time=t,matrix=pose.tolist(),coverage=coverage,triangles=count))
        print('Rendered',t,flush=True)
    sheet.save(out/'contact-sheet.png')
    (out/'poses.json').write_text(json.dumps(dict(source_sha256=MENU_HASH,vertical_fov=fov,poses=poses,
        limitations=['Stored pose used as activation pose','Fog and fixture phase held at zero','No actor or runtime events','Native-like math, not bit-exact x87 replay']),indent=2)+'\n')
    (out/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>Camera02 transition study</title>
<style>body{background:#181c24;color:#ddd;font:16px system-ui;max-width:850px;margin:30px auto}img{width:100%}input{width:65%}button{padding:8px}</style>
<h1>Camera02 — transition study</h1><p>Diagnostic reconstruction. Lighting incomplete; scene animation frozen. Seven sampled poses, not continuous playback.</p>
<img id="frame" src="frame-0.png"><p><button id="play">Play samples</button> <input id="seek" type="range" min="0" max="6" value="0" step="1"> <output id="time">0 s</output></p>
<script>const seek=document.getElementById('seek'),frame=document.getElementById('frame'),time=document.getElementById('time');let timer=null;
function show(){frame.src='frame-'+seek.value+'.png';time.value=(Number(seek.value)*1.5)+' s'}seek.oninput=()=>{clearInterval(timer);timer=null;show()};
document.getElementById('play').onclick=()=>{if(timer){clearInterval(timer);timer=null;return}seek.value=0;show();timer=setInterval(()=>{seek.value=Number(seek.value)+1;show();if(Number(seek.value)===6){clearInterval(timer);timer=null}},1500)};</script>''',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
