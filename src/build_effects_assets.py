"""Prepare an experimental MGM/MFT/DDS Effects canvas using existing decoders."""
import json
import subprocess
import sys
import csv
import os
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image

def build(assets,out):
    assets=assets.resolve();out=out.resolve()
    if 'game' in [p.lower() for p in out.parts]:
        raise ValueError('Output in game directory is forbidden.')
    if out.exists(): raise ValueError('Output must be new.')
    if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in [out,*out.parents]):
        raise ValueError('Reparse paths are unsupported.')
    raw=(assets/'pop4common.mgm').read_bytes()
    root=ET.fromstring(raw);page=root.find(".//PAGE[NAME='P_VideoMenu']")
    tools=Path(__file__).resolve().parents[1]/'tools'
    out.mkdir(parents=True)
    def run(tool,*args):
        environment={k:v for k,v in os.environ.items() if k.lower()!='psmodulepath'}
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(tools/tool),*map(str,args)],env=environment,check=True,stdout=subprocess.DEVNULL)
    background=Image.new('RGBA',(800,600),'#181c24')
    # Resolve direct and instanced panel images, preserving MGM draw order.
    images=[]
    for element in page.findall('CHILDREN/*'):
        if element.tag=='IMAGE': images.append((element,0,0))
        if element.tag=='BUTTONINST' and not element.findtext('LABEL'):
            definition=root.find(".//BUTTON[NAME='"+element.findtext('LINK/AREA')+"']")
            if definition is not None:
                x,y=map(float,element.findtext('KEYFRAMES/KEYFRAME/POSITION').split())
                images.extend((im,x,y) for im in definition.findall('CHILDREN/IMAGE'))
    for i,(element,x,y) in enumerate(images):
        material=root.find(".//MATERIAL[NAME='"+element.findtext('MATERIAL')+"']")
        path=assets/material.findtext('STAGE/FILE').strip('\\').replace('\\','/')
        folder=out/('panel'+str(i));run('Export-DDSPreview.ps1','-Path',path,'-OutputDirectory',folder)
        f=element.find('KEYFRAMES/KEYFRAME')
        rect=[round((float(f.findtext(k))+(x if k in ('LEFT','RIGHT') else y))*1.25) for k in ('LEFT','TOP','RIGHT','BOTTOM')]
        with Image.open(folder/'texture.png') as im: panel=im.convert('RGBA').resize((rect[2]-rect[0],rect[3]-rect[1]),Image.Resampling.BILINEAR)
        packed=int(f.findtext('COLOR1','-1'))&0xffffffff
        # Experimental packed ARGB modulation; uniform corner color only.
        channels=panel.split();rgba=((packed>>16)&255,(packed>>8)&255,packed&255,(packed>>24)&255)
        panel=Image.merge('RGBA',tuple(c.point(lambda v,m=m:round(v*m/255)) for c,m in zip(channels,rgba)))
        background.alpha_composite(panel,(rect[0],rect[1]))
    entries=[]
    for element in page.findall('CHILDREN/*'):
        name=element.findtext('NAME');text=None;x=y=0
        if element.tag=='TEXT' and (name=='Title' or name.startswith('Item')):
            node=element;text=element.findtext('STRING')
        elif element.tag in ('CHECKBOXINST','BUTTONINST') and (name.startswith('Item') or name in ('Back','Effects')):
            text=element.findtext('LABEL')
            definition=root.find(".//*[NAME='"+element.findtext('LINK/AREA')+"']")
            node=definition.find('CHILDREN/TEXT') if definition is not None else None
            x,y=map(float,element.findtext('KEYFRAMES/KEYFRAME/POSITION').split())
        else: continue
        if not text or node is None: continue
        f=node.find('KEYFRAMES/KEYFRAME');height=float(f.findtext('HEIGHT'));scale=height/36*1.25
        folder=out/name
        run('Export-MFTTextPreview.ps1','-Path',assets/'fonts'/(node.findtext('FONT')+'.mft'),'-OutputDirectory',folder,'-Text',text)
        spec=json.loads((folder/'specimen.json').read_text(encoding='utf-8-sig'))
        with Image.open(folder/'text.png') as im: alpha=im.getchannel('A')
        box=alpha.getbbox();alpha=alpha.crop(box).resize((max(1,round((box[2]-box[0])*scale)),max(1,round((box[3]-box[1])*scale))),Image.Resampling.BILINEAR)
        rows=list(csv.DictReader((folder/'placements.csv').open(encoding='utf-8-sig')))
        advance=int(rows[-1]['PenX'])+int(rows[-1]['Advance'])
        alignment=node.findtext('ALIGNMENT');shift=advance*scale*(0.5 if alignment=='CENTER' else 1 if alignment=='RIGHT' else 0)
        px=round((x+float(f.findtext('LEFT')))*1.25+(box[0]-spec['OriginX'])*scale-shift)
        py=round((y+float(f.findtext('TOP'))+height)*1.25+(box[1]-spec['Baseline'])*scale)
        alpha.save(folder/'mask.png')
        color=tuple(map(int,f.findtext('COLOR').split()))
        entry=dict(name=name,text=text,x=px,y=py,width=alpha.width,height=alpha.height,color=color,interactive=element.tag!='TEXT' and name!='Effects')
        entries.append(entry)
        if not entry['interactive']:
            ink=Image.new('RGBA',alpha.size,color);ink.putalpha(alpha);background.alpha_composite(ink,(px,py))
    background.save(out/'background.png')
    preview=background.copy()
    for e in entries:
        if e['interactive']:
            with Image.open(out/e['name']/'mask.png') as alpha:
                ink=Image.new('RGBA',alpha.size,tuple(e['color']));ink.putalpha(alpha);preview.alpha_composite(ink,(e['x'],e['y']))
    preview.save(out/'preview.png')
    (out/'layout.json').write_text(json.dumps(dict(entries=entries,source_sha256=hashlib.sha256(raw).hexdigest(),experimental=True),indent=2))
    print('Effects assets:',out)

if __name__=='__main__': build(Path(sys.argv[1]),Path(sys.argv[2]))
