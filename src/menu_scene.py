"""Resource-based research menu drawing and isolated, non-persistent settings."""
import csv
import json
from pathlib import Path
from PIL import Image, ImageDraw


class Font:
    def __init__(self, folder):
        self.info=json.loads((folder/'font.json').read_text(encoding='utf-8-sig'))
        with Image.open(folder/'atlas.png') as im: self.atlas=im.convert('L')
        self.glyphs={int(r['Code']):r for r in csv.DictReader((folder/'glyphs.csv').read_text(encoding='utf-8-sig').splitlines())}
        self.cache={}

    def render(self,text,height,color):
        key=(text,height,tuple(color))
        if key in self.cache: return self.cache[key]
        if not text or len(text)>128 or any(ord(c)<32 or ord(c)>126 for c in text):
            raise ValueError('Only bounded printable ASCII is supported.')
        pen=0;placements=[];left=top=right=bottom=0
        for char in text:
            g=self.glyphs[ord(char)]
            signed=lambda v: int(v)-256 if int(v)>=128 else int(v)
            x=pen+signed(g['Metric2Raw']);y=-signed(g['Metric3Raw'])
            w=int(g['Width']);h=int(g['Height'])
            placements.append((g,x,y,w,h))
            left=min(left,x);top=min(top,y);right=max(right,x+w);bottom=max(bottom,y+h)
            pen+=int(g['Metric4Raw'])
        mask=Image.new('L',(max(1,right-left),max(1,bottom-top)))
        for g,x,y,w,h in placements:
            if not w or not h: continue
            ax=int(g['AtlasX'])+1;ay=int(g['AtlasY'])+1
            glyph=self.atlas.crop((ax,ay,ax+w,ay+h))
            old=mask.crop((x-left,y-top,x-left+w,y-top+h))
            # Same white source-over coverage used by the original specimen tool.
            merged=Image.new('L',(w,h));merged.putdata([round(a+b*(255-a)/255) for a,b in zip(glyph.getdata(),old.getdata())])
            mask.paste(merged,(x-left,y-top))
        box=mask.getbbox()
        scale=height/self.info['SizeWord']*1.25
        if not box: box=(0,0,1,1)
        mask=mask.crop(box).resize((max(1,round((box[2]-box[0])*scale)),max(1,round((box[3]-box[1])*scale))),Image.Resampling.BILINEAR)
        ink=Image.new('RGBA',mask.size,tuple(color));ink.putalpha(mask.point(lambda v:round(v*color[3]/255)))
        result=(ink,(left+box[0])*scale,(top+box[1])*scale,pen*scale)
        # Avoid unbounded growth when inspecting many custom binding strings.
        if len(self.cache)>512: self.cache.clear()
        self.cache[key]=result
        return result


class MenuState:
    def __init__(self,catalog):
        self.catalog=catalog
        self.values={}
        self.bindings={}
        self.sliders={}
        self.rows={}
    def slider(self,page,name,value=None):
        widget=next(w for w in self.catalog['pages'][page].get('widgets',[]) if w['name']==name and w['kind']=='slider')
        key=(('graphics' if page in ('effects','advanced') else 'controls'),name)
        if value is not None:self.sliders[key]=max(widget['minimum'],min(widget['maximum'],round(value)))
        return self.sliders.get(key,widget['minimum'])
    def move_row(self,page,delta):
        self.rows[page]=max(0,min(5,self.rows.get(page,0)+delta))
        return self.rows[page]
    def choose(self,page,group,value):
        valid=[e['value'] for e in self.catalog['pages'][page]['entries'] if e.get('group')==group and e.get('kind')=='choice']
        if value not in valid: raise ValueError('Unsupported choice.')
        self.values[(page,group)]=value
    def bind(self,page,name,value):
        entry=next((e for e in self.catalog['pages'][page]['entries'] if e['name']==name and e.get('kind')=='binding'),None)
        if entry is None or not value or len(value)>24 or any(ord(c)<32 or ord(c)>126 for c in value):
            raise ValueError('Binding must be 1-24 printable ASCII characters.')
        self.bindings[(page,name)]=value
    def clear(self,page):
        self.values={k:v for k,v in self.values.items() if k[0]!=page}
        self.bindings={k:v for k,v in self.bindings.items() if k[0]!=page}
        self.rows.pop(page,None)
        domain='graphics' if page in ('effects','advanced') else 'controls'
        self.sliders={k:v for k,v in self.sliders.items() if k[0]!=domain}


class Scene:
    def __init__(self,folder):
        self.folder=Path(folder)
        self.catalog=json.loads((self.folder/'catalog.json').read_text())
        self.fonts={name:Font(self.folder/path) for name,path in self.catalog['fonts'].items()}
        self.backgrounds={}
        self.sprites={}
        for key in self.catalog['pages']:
            with Image.open(self.folder/(key+'-background.png')) as im:self.backgrounds[key]=im.convert('RGBA')
            for w in self.catalog['pages'][key].get('widgets',[]):
                for path in (w['sprites'].values() if w['kind']=='slider' else [w['sprite']]):
                    if path not in self.sprites:
                        with Image.open(self.folder/path) as im:self.sprites[path]=im.convert('RGBA')
    def render(self,page,state,hover=None):
        image=self.backgrounds[page].copy();hits=[]
        for e in self.catalog['pages'][page]['entries']:
            text=state.bindings.get((page,e['name']),e['text'])
            color=e['color']
            if e.get('disabled'):color=[102,102,102,255]
            elif e.get('kind')=='choice' and state.values.get((page,e['group']))==e['value']:color=[255,255,255,255]
            elif e['name']==hover:color=[232,220,193,255]
            ink,dx,dy,advance=self.fonts[e['font']].render(text,e['height'],color)
            anchor=e['x']*1.25
            if e['align']=='CENTER':anchor-=advance/2
            elif e['align']=='RIGHT':anchor-=advance
            x=round(anchor+dx);y=round((e['y']+e['height'])*1.25+dy)
            image.alpha_composite(ink,(x,y))
            if e.get('kind') and not e.get('disabled'):
                hits.append((e,(x-5,y-5,x+ink.width+5,y+ink.height+5)))
        for w in self.catalog['pages'][page].get('widgets',[]):
            x,y=w['x'],w['y']
            if w['kind']=='row':
                icon=self.sprites[w['sprite']]
                row=state.rows.get(page,0)
                if (row==0 and w['delta']<0) or (row==5 and w['delta']>0):
                    icon=icon.copy();icon.putalpha(icon.getchannel('A').point(lambda a:a//3))
                image.alpha_composite(icon,(x,y))
                hits.append((w,(x,y,x+icon.width,y+icon.height)))
            else:
                sprites={k:self.sprites[v] for k,v in w['sprites'].items()}
                bar=sprites['bar'];start=x+sprites['minus'].width;end=start+bar.width
                value=state.slider(page,w['name']);ratio=(value-w['minimum'])/(w['maximum']-w['minimum'])
                image.alpha_composite(bar,(start,y-bar.height//2))
                for part,px,delta in [('minus',x,-1),('plus',end,1)]:
                    icon=sprites[part];image.alpha_composite(icon,(px,y-icon.height//2))
                    hits.append((dict(name=w['name']+'-'+part,kind='step',slider=w['name'],delta=delta),(px,y-icon.height//2,px+icon.width,y+icon.height//2)))
                icon=sprites['handle'];px=round(start+ratio*bar.width-icon.width/2)
                image.alpha_composite(icon,(px,y-icon.height//2))
                hits.append((dict(w,start=start,end=end),(start,y-icon.height//2,end,y+icon.height//2)))
        return image,hits
