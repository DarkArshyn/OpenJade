"""Build Options, Graphics and Controls research scenes from MGM/MFT/DDS resources."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET
from PIL import Image
from menu_scene import Scene, MenuState


def build(assets,out):
    assets=assets.resolve()
    # Check lexical ancestors before resolving, so junctions cannot hide game paths.
    out=out.absolute()
    if 'game' in [p.lower() for p in out.parts] or out.exists(): raise ValueError('Output must be new and outside game/.')
    if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in [out,*out.parents]):raise ValueError('Reparse output path.')
    raw=(assets/'pop4common.mgm').read_bytes()
    if b'<!DOCTYPE' in raw.upper():raise ValueError('Unsupported document declaration.')
    root=ET.fromstring(raw);out.mkdir(parents=True)
    tools=Path(__file__).resolve().parents[1]/'tools'
    sources={str(assets/'pop4common.mgm'):hashlib.sha256(raw).hexdigest()}
    def run(tool,*args):
        env={k:v for k,v in os.environ.items() if k.lower()!='psmodulepath'}
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(tools/tool),*map(str,args)],env=env,check=True,stdout=subprocess.DEVNULL)
    def frame(node):return node.find("KEYFRAMES/KEYFRAME[IDX='0']")
    def page(name):return root.find(".//PAGE[NAME='"+name+"']")
    def named(parent,name):return parent.find("CHILDREN/*[NAME='"+name+"']")
    fonts={};textures={};evidence=[]
    def entry(parent,name,text=None,**metadata):
        element=named(parent,name)
        if element is None:raise ValueError('Missing node '+name)
        x=y=0
        if element.tag=='TEXT':node=element;original=element.findtext('STRING')
        else:
            definition=root.find(".//*[NAME='"+element.findtext('LINK/AREA')+"']")
            node=definition.find('CHILDREN/TEXT')
            x,y=map(float,frame(element).findtext('POSITION').split());original=element.findtext('LABEL') or ''
        if node is None:raise ValueError('Missing caption '+name)
        if text is None:text=original
        if text!=original:evidence.append(dict(page=parent.findtext('NAME'),node=name,stored=original,displayed=text,reason=metadata.pop('reason','Supplied screenshot transcription; not a game default')))
        f=frame(node);font=node.findtext('FONT')
        if font not in fonts:
            dest='font'+str(len(fonts));path=assets/'fonts'/(font+'.mft')
            run('Read-MFT.ps1','-Path',path,'-OutputDirectory',out/dest)
            fonts[font]=dest;sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        anchor=x+float(f.findtext('LEFT'))
        # Fixed-width text aligns within its bounds; autosized captions use their anchor.
        if node.findtext('AUTOSIZED')=='0':
            width=float(f.findtext('RIGHT'))-float(f.findtext('LEFT'))
            anchor+=width*(0.5 if node.findtext('ALIGNMENT')=='CENTER' else 1 if node.findtext('ALIGNMENT')=='RIGHT' else 0)
        return dict(name=name,text=text,font=font,height=float(f.findtext('HEIGHT')),x=anchor,y=y+float(f.findtext('TOP')),align=node.findtext('ALIGNMENT'),color=list(map(int,f.findtext('COLOR').split())),**metadata)
    def background(parent,key,exclude=()):
        canvas=Image.new('RGBA',(800,600),'#181c24')
        for e in parent.findall('CHILDREN/*'):
            if e.findtext('NAME') in exclude:continue
            images=[]
            if e.tag=='IMAGE':images=[(e,0,0)]
            elif e.tag in ('BUTTONINST','CHECKBOXINST'):
                link=e.findtext('LINK/AREA')
                definition=root.find(".//*[NAME='"+link+"']") if link else None
                if definition is not None:
                    x,y=map(float,frame(e).findtext('POSITION').split())
                    images=[(im,x,y) for im in definition.findall('CHILDREN/IMAGE')]
            for im,x,y in images:
                material=root.find(".//MATERIAL[NAME='"+im.findtext('MATERIAL')+"']")
                path=(assets/material.findtext('STAGE/FILE').strip('\\').replace('\\','/')).resolve()
                if not path.is_relative_to(assets):raise ValueError('Texture outside asset root.')
                if path not in textures:
                    dest=out/('texture'+str(len(textures)));run('Export-DDSPreview.ps1','-Path',path,'-OutputDirectory',dest)
                    with Image.open(dest/'texture.png') as image:textures[path]=image.convert('RGBA')
                    sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
                panel=textures[path].copy()
                region=list(map(int,material.findtext('STAGE/REGION').split()))
                panel=panel.crop(tuple(region))
                f=frame(im);tiling=list(map(float,f.findtext('TILING','1 1').split()))
                if tiling[0]<0:panel=panel.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                if tiling[1]<0:panel=panel.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                rotation=float(f.findtext('ROTATION','0'))
                if rotation==180:panel=panel.transpose(Image.Transpose.ROTATE_180)
                elif rotation:raise ValueError('Unsupported panel rotation.')
                rect=[round((float(f.findtext(k))+(x if k in ('LEFT','RIGHT') else y))*1.25) for k in ('LEFT','TOP','RIGHT','BOTTOM')]
                if rect[2]<=rect[0] or rect[3]<=rect[1]:continue
                panel=panel.resize((rect[2]-rect[0],rect[3]-rect[1]),Image.Resampling.BILINEAR)
                packed=int(f.findtext('COLOR1','-1'))&0xffffffff
                rgba=((packed>>16)&255,(packed>>8)&255,packed&255,(packed>>24)&255)
                panel=Image.merge('RGBA',tuple(c.point(lambda v,m=m:round(v*m/255)) for c,m in zip(panel.split(),rgba)))
                canvas.alpha_composite(panel,(rect[0],rect[1]))
        canvas.save(out/(key+'-background.png'))
    pages={}
    p=page('P_Options');entries=[entry(p,'Title')]
    for name,route in [('Video','effects'),('Controls','keyboard'),('Back','close')]:entries.append(entry(p,name,kind='route',route=route))
    for name in ('Sounds','Game'):entries.append(entry(p,name,disabled=True))
    background(p,'options');pages['options']=dict(entries=entries)
    video=page('P_VideoMenu')
    for key in ('effects','advanced'):
        entries=[entry(video,'Title'),entry(video,'Back',kind='route',route='options'),entry(video,'Effects',kind='route',route='effects'),entry(video,'Basic','Advanced',kind='route',route='advanced')]
        if key=='effects':groups=[('SpecialEffects',['High','Medium','Low']),('Shadow Effects',['High','Low','None']),('Water Effects',['On','Off']),('Fog',['On','Off'])]
        else:groups=[('Filtering',['Trilinear','Bilinear','None']),('V-Sync.',['Disable','Enable']),('Texture Quality',['High','Low'])]
        for i,(label,choices) in enumerate(groups,1):
            entries.append(entry(video,f'Item{i}_Label',label))
            for j,text in enumerate(choices,1):entries.append(entry(video,f'Item{i}_Choice{j}',text,kind='choice',group=f'Item{i}',value=text))
        # Static labels are kept; unresolved dynamic values are explicitly absent.
        entries.extend(entry(video,name) for name in ('Resolution','Gamma'))
        # The captures support mutually exclusive panels: short for Advanced,
        # tall for Effects. Compositing both creates an extra dark inset.
        excluded=['ShmueButton'] if key=='advanced' else ['ShmueButton2']
        background(video,key,excluded);pages[key]=dict(entries=entries,excluded_background_nodes=excluded)
    controls=page('P_ControlsMenu')
    actions=['Move Forward','Move Left','Move Backward','Move Right','Walk Toggle','Jump']
    keys=[['W','Up'],['A','Left'],['S','Down'],['D','Right'],['Shift','Num Del'],['Space','Right Ctrl']]
    pad=['Y Axis(+)','X Axis(-)','Y Axis(-)','X Axis(+)','Unassigned','B1']
    for key in ('keyboard','gamepad'):
        entries=[entry(controls,'Title','Controls - '+key.title()),entry(controls,'Back',kind='route',route='options')]
        for name,target in [('Keyboard','keyboard'),('Gamepad','gamepad')]:entries.append(entry(controls,name,kind='route',route=target))
        for name,text in [('MouseSpeed','Mouse Speed'),('FreeLook','Camera Freelook'),('Navigation','Camera Navigation')]:entries.append(entry(controls,name,text))
        for prefix in ('FL','Nav'):
            for suffix in ('Normal','Inverted'):
                entries.append(entry(controls,prefix+suffix,kind='choice',group=prefix,value=suffix))
        for i,action in enumerate(actions,1):
            entries.append(entry(controls,f'Action_{i}',action))
            for j in range(1,3 if key=='keyboard' else 2):
                text=keys[i-1][j-1] if key=='keyboard' else pad[i-1]
                entries.append(entry(controls,f'Key_{i}_{j}',text,kind='binding',reason='Screenshot sample; Unassigned denotes its empty slot. Editable research text, not device capture.'))
        exclude=['ActionUp','ActionDown','Attackkey','Element2']
        if key=='gamepad':exclude+=['BlackRectangle3']+[f'Key_{i}_2' for i in range(1,7)]
        background(controls,key,exclude);pages[key]=dict(entries=entries)
    def sprite(area):
        definition=root.find(".//*[NAME='"+area+"']")
        im=definition.find('CHILDREN/IMAGE');f=frame(im)
        material=root.find(".//MATERIAL[NAME='"+im.findtext('MATERIAL')+"']")
        path=(assets/material.findtext('STAGE/FILE').strip('\\').replace('\\','/')).resolve()
        if not path.is_relative_to(assets):raise ValueError('Texture outside asset root.')
        if path not in textures:
            dest=out/('texture'+str(len(textures)));run('Export-DDSPreview.ps1','-Path',path,'-OutputDirectory',dest)
            with Image.open(dest/'texture.png') as image:textures[path]=image.convert('RGBA')
            sources[str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
        region=tuple(map(int,material.findtext('STAGE/REGION').split()))
        size=tuple(round((float(f.findtext(b))-float(f.findtext(a)))*1.25) for a,b in [('LEFT','RIGHT'),('TOP','BOTTOM')])
        image=textures[path].crop(region).resize(size,Image.Resampling.BILINEAR)
        packed=int(f.findtext('COLOR1','-1'))&0xffffffff
        # Sprite tint is interpreted as packed ABGR: 0xFF7AA0BC -> 188,160,122.
        rgba=(packed&255,(packed>>8)&255,(packed>>16)&255,(packed>>24)&255)
        image=Image.merge('RGBA',tuple(c.point(lambda v,m=m:round(v*m/255)) for c,m in zip(image.split(),rgba)))
        filename='sprite-'+area+'.png';image.save(out/filename)
        return filename
    for key,p in [('effects',video),('advanced',video),('keyboard',controls),('gamepad',controls)]:
        widgets=[]
        for slider in p.findall('CHILDREN/SLIDER'):
            x,y=map(float,frame(slider).findtext('POSITION').split())
            widgets.append(dict(name=slider.findtext('NAME'),kind='slider',x=round(x*1.25),y=round((y+16)*1.25),
                minimum=int(slider.findtext('RANGEMIN')),maximum=int(slider.findtext('RANGEMAX')),
                sprites={part:sprite(slider.findtext(link+'/AREA')) for part,link in [('minus','HEADERLINK'),('plus','FOOTERLINK'),('handle','HANDLELINK'),('bar','SURFACELINK')]}))
        if key in ('keyboard','gamepad'):
            for name,delta in [('ActionUp',-1),('ActionDown',1)]:
                element=named(controls,name);x,y=map(float,frame(element).findtext('POSITION').split())
                widgets.append(dict(name=name,kind='row',delta=delta,x=round(x*1.25),y=round(y*1.25),sprite=sprite(element.findtext('LINK/AREA'))))
        pages[key]['widgets']=widgets
    catalog=dict(pages=pages,fonts=fonts,source_sha256=hashlib.sha256(raw).hexdigest(),sources=sources,overrides=evidence,
        screenshot_references={'advanced':'PopsotGraphics2.jpg','keyboard':'PoP_TSoT_Keyboard.png','gamepad':'PoP_TSoT_Controller.png','effects':'PopsotGraphics1.jpg'},
        limitations=['Frame zero only','Packed ARGB modulation and baseline remain experimental','No actual device bindings','Only six screenshot actions; arrows select within those six','Slider values are raw MGM units, not established resolutions or gamma','No game default settings are inferred','Navigation and widget hit areas are experimental'])
    (out/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    scene=Scene(out);state=MenuState(catalog)
    for key in pages:scene.render(key,state)[0].save(out/(key+'-preview.png'))
    for path,digest in sources.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest()!=digest:raise ValueError('Input changed during build.')
    print('Built five menu scenes:',out)

if __name__=='__main__':build(Path(sys.argv[1]),Path(sys.argv[2]))
