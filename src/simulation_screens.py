"""800x600 screen layouts transcribed from the user's PC GOG captures.

This is an independent simulation, not recovered game logic. Defaults below are
simulation baselines based on visible selections, not verified factory defaults.
"""
from copy import deepcopy
from pathlib import Path
import json
from PIL import Image
from menu_scene import Scene

GOLD=(188,160,122,255)
WHITE=(255,255,255,255)
ACTIONS=['Move Forward','Move Left','Move Backward','Move Right','Walk Toggle','Jump',
         'Special Action','Sword Attack','Use Dagger','Cancel','Rewind',
         'First Person View','Alternate View','Reset Camera','Camera Forward',
         'Camera Backward','Camera Left','Camera Right']
KEYS=[['Z','Up'],['Q','Left'],['S','Down'],['D','Right'],['Shift','Num Del'],
      ['Space','Right Ctrl'],['Mouse 2',''],['Mouse 1',''],['E','Mouse 3'],
      ['C','Num 1'],['R','Right Shift'],['F','Delete'],['A','End'],['X',''],
      ['',''],['',''],['',''],['','']]
BASELINE={'effects':['High','High','On','On'],'advanced':['Trilinear','Enable','High'],
          'game':['Normal','Yes'],'sound':['100','100','100','None','Yes','Yes'],
          'controls':['43','Normal','Normal'],'graphics':['800x600x32','0.00'],
          'keyboard':deepcopy(KEYS),'gamepad':[['Y Axis(+)'],['X Axis(-)'],['Y Axis(-)'],['X Axis(+)'],[''],['B1']]+[[''] for _ in range(12)]}


class Model:
    def __init__(self):
        self.settings=deepcopy(BASELINE); self.saved=deepcopy(self.settings)
        self.profiles=[]; self.selected=None; self.active=None; self.offset=0

    @property
    def dirty(self):return self.settings!=self.saved
    def save(self):self.saved=deepcopy(self.settings)
    def discard(self):self.settings=deepcopy(self.saved)
    def defaults(self,page):
        groups={'effects':['effects','advanced','graphics'],'advanced':['effects','advanced','graphics'],
                'keyboard':['keyboard','gamepad','controls'],'gamepad':['keyboard','gamepad','controls']}.get(page,[page])
        for key in groups:self.settings[key]=deepcopy(BASELINE[key])
    def create(self,name):
        name=name.strip()
        if len(self.profiles)>=5:raise ValueError('This simulation supports five session profiles.')
        if not name or len(name)>20 or any(ord(c)<32 or ord(c)>126 for c in name):
            raise ValueError('Use 1-20 printable ASCII characters.')
        if name.casefold() in [n.casefold() for n in self.profiles]:raise ValueError('Profile already exists.')
        self.profiles.append(name);self.selected=self.active=name
    def scroll(self,delta):self.offset=max(0,min(len(ACTIONS)-6,self.offset+delta))


class Screens:
    def __init__(self,report):
        self.report=Path(report);self.scene=Scene(self.report/'menus-assets')
        self.font=next(iter(self.scene.fonts.values()))
        experiment=json.loads((self.report/'experiment.json').read_text(encoding='utf-8-sig'))
        self.assets=Path(next(i['Path'] for i in experiment['Inputs'] if Path(i['Path']).name.lower()=='pop4common.mgm')).parent
        self.textures={}
        panel=self.texture('shmuecopy.dds')
        self.panel=panel.crop(panel.getchannel('A').getbbox())
        self.cursor=self.texture('officialcursor_alpha2_desaturated.dds').resize((40,40),Image.Resampling.LANCZOS)
        self.logo=self.texture('pop.dds')
        self.widgets=self.scene.catalog['pages']['effects']['widgets'][0]

    def texture(self,name):
        if name not in self.textures:
            with Image.open(self.assets/'texture'/name) as im:self.textures[name]=im.convert('RGBA')
        return self.textures[name]

    def text(self,label,x,y,size=18,align='left',action=None,selected=False,disabled=False,width=None):
        if not label:return
        color=(102,102,102,255) if disabled else WHITE if selected or action is not None and action==self.hover else GOLD
        ink,_,_,_=self.font.render(label,size,color)
        if width and ink.width>width:ink=ink.resize((width,ink.height),Image.Resampling.LANCZOS)
        x=round(x-ink.width/2 if align=='center' else x-ink.width if align=='right' else x)
        self.image.alpha_composite(ink,(x,round(y)))
        if action is not None and not disabled:self.hits.append((action,(x-5,y-5,x+ink.width+5,y+max(ink.height,22))))

    def box(self,rect):
        x,y,w,h=rect
        layer=self.panel.resize((w,h),Image.Resampling.BILINEAR)
        alpha=layer.getchannel('A').point(lambda v:round(v*0.59))
        layer=Image.new('RGBA',layer.size,(0,0,0,0));layer.putalpha(alpha)
        self.image.alpha_composite(layer,(x,y))

    def choices(self,label,y,group,index,options,x=187,positions=None,disabled=False):
        self.text(label,x,y,14)
        positions=positions or ([415,540,664] if len(options)==3 else [415,540])
        for pos,value in zip(positions,options):
            self.text(value,pos,y,12,'center',('choice',group,index,value),self.model.settings[group][index]==value,disabled=disabled)

    def slider(self,label,y,group,index,values,x=187,start=440,end=704):
        value=self.model.settings[group][index]
        self.text(label,x,y-15,14);self.text(value+('%' if group in ('sound','controls') and index<3 and value.isdigit() else ''),x,y+9,12)
        sprites={k:self.scene.sprites[v] for k,v in self.widgets['sprites'].items()}
        bar=sprites['bar'].resize((end-start, sprites['bar'].height))
        self.image.alpha_composite(bar,(start,y-bar.height//2))
        ratio=values.index(value)/(len(values)-1) if value in values else 0
        for part,px in [('minus',start-36),('plus',end)]:
            im=sprites[part];self.image.alpha_composite(im,(px,y-im.height//2))
            self.hits.append((('step',group,index,values,-1 if part=='minus' else 1),(px,y-22,px+im.width,y+22)))
        im=sprites['handle'];self.image.alpha_composite(im,(round(start+ratio*(end-start)-im.width/2),y-im.height//2))
        self.hits.append((('slider',group,index,values,start,end),(start,y-24,end,y+24)))

    def render(self,page,model,hover=None,modal=None,typed='',editing=None):
        self.model=model;self.hover=hover;self.hits=[]
        self.image=Image.new('RGBA',(800,600),'#181c24')
        if modal:
            if modal=='settings':
                self.box((130,205,540,190))
                for line,y in [('Game options have been modified.',225),('Would you like to keep',266),('these changes?',307)]:self.text(line,400,y,18,'center')
                for label,x in [('Yes',255),('No',400),('Cancel',535)]:self.text(label,x,363,18,'center',('answer',label))
            else:
                self.box((100,225,590,153))
                self.text('Delete this simulation profile?' if modal=='delete' else 'Do you really want to quit',400,244,18,'center')
                self.text(model.selected or '' if modal=='delete' else 'Prince of Persia: The Sands of Time?',400,284,18,'center',width=570)
                for label,x in [('Yes',255),('No',540)]:self.text(label,x,343,18,'center',('answer',label))
            return self.image,self.hits
        titles={'options':'Options','effects':'Graphics','advanced':'Graphics','keyboard':'Controls - Keyboard',
                'gamepad':'Controls - Gamepad','game':'Game Options','sound':'Sound','create':'Create a new profile:', 'profiles':'Choose your profile'}
        if page in titles:self.text(titles[page],31,20,28 if page not in ('profiles','create') else 21)
        if page=='main':
            logo=self.logo.resize((480,120),Image.Resampling.LANCZOS);self.image.alpha_composite(logo,(20,20))
            for label,y,dest in [('Start New Game',162,'new'),('Load Saved Game',225,'load'),('Options',287,'options'),('Credits',350,'credits'),('Quit',412,'quit')]:
                self.text(label,375,y,18,action=('route',dest),disabled=dest=='load')
            self.text('Change Profile',62,536,18,action=('route','profiles'))
        elif page=='options':
            for label,y,dest in [('Controls',170,'keyboard'),('Game',232,'game'),('Graphics',295,'effects'),('Sound',357,'sound')]:self.text(label,375,y,18,action=('route',dest))
        elif page in ('effects','advanced'):
            self.box((155,95,590,180));self.box((148,296,598,220 if page=='effects' else 170))
            self.slider('Resolution',155,'graphics',0,['640x480x32','800x600x32','1024x768x32','1280x960x32','1600x1200x32'],start=427,end=691)
            self.slider('Gamma',217,'graphics',1,[f'{i/10:.2f}' for i in range(11)],start=427,end=691)
            self.text('Effects',31,323,16 if page=='effects' else 12,action=('route','effects'))
            self.text('Advanced',31,354,16 if page=='advanced' else 12,action=('route','advanced'))
            groups=([('Special Effects',['High','Medium','Low']),('Shadow Effects',['High','Medium','None']),('Water Effects',['On','Off']),('Fog',['On','Off'])] if page=='effects' else [('Filtering',['Trilinear','Bilinear','None']),('V-Sync.',['Disable','Enable']),('Texture Quality',['High','Low'])])
            for i,(label,values) in enumerate(groups):self.choices(label,323+i*50,page,i,values)
        elif page=='game':
            self.box((150,190,645,154))
            self.slider('Frequency of hints',245,'game',0,['None','Few','Normal','Many'],start=477,end=742)
            self.choices('Tutorials',291,'game',1,['Yes','No'],positions=[563,688])
        elif page=='sound':
            self.box((155,64,615,250));self.box((160,321,610,180))
            for i,label in enumerate(['Music Volume','Voice Volume','Sound FX Volume']):self.slider(label,117+i*63,'sound',i,[str(n) for n in range(101)],start=451,end=716)
            self.choices('Audio Virtualization',367,'sound',3,['None','Partial','Full'],positions=[474,576,677])
            self.choices('3D Accelerator',405,'sound',4,['Yes','No'],positions=[563,688])
            self.image.alpha_composite(self.texture('eax.dds').resize((104,33)),(187,431))
            self.choices('',445,'sound',5,['Yes','No'],positions=[563,688],disabled=True)
        elif page in ('keyboard','gamepad'):
            self.text('Gamepad',31,72,16 if page=='gamepad' else 12,action=('route','gamepad'))
            self.text('Keyboard',31,104,16 if page=='keyboard' else 12,action=('route','keyboard'))
            self.box((180,63,205,252));self.box((413,63,173,252))
            if page=='keyboard':self.box((605,63,175,252))
            for row in range(6):
                i=model.offset+row;y=97+row*31
                self.text(ACTIONS[i],283,y,13,'center',width=192)
                for col,x in enumerate([500,695] if page=='keyboard' else [500]):
                    tile=Image.new('RGBA',(122,22),(65,65,65,130));self.image.alpha_composite(tile,(x-61,y-3))
                    label=typed if editing==('binding',page,i,col) else model.settings[page][i][col]
                    self.text(label or ' ',x,y,12,'center',width=114)
                    self.hits.append((('binding',page,i,col),(x-61,y-3,x+61,y+23)))
            for name,y,delta in [('b_list_up.dds',66,-5),('b_list_down.dds',282,5)]:
                im=self.texture(name)
                im=im.crop(im.getchannel('A').getbbox()).resize((16,22))
                disabled=model.offset==0 if delta<0 else model.offset==len(ACTIONS)-6
                if disabled:im=im.copy();im.putalpha(im.getchannel('A').point(lambda a:a//3))
                self.image.alpha_composite(im,(272,y))
                if not disabled:self.hits.append((('scroll',delta),(267,y-4,299,y+26)))
            self.box((165,320,625,177))
            self.slider('Mouse Speed',363,'controls',0,[str(n) for n in range(101)],start=477,end=742)
            self.choices('Camera Freelook',411,'controls',1,['Normal','Inverted'],positions=[470,626])
            self.choices('Camera Navigation',462,'controls',2,['Normal','Inverted'],positions=[470,626])
        elif page=='create':
            self.box((175,241,450,84));self.text(typed+'_',216,281,20,width=390)
            self.hits.append((('input',),(190,250,610,320)))
            self.text('Quit' if not model.profiles else 'Back',62,536,18,action=('route','quit' if not model.profiles else 'profiles'))
            self.text('Create',720,536,18,'right',('create',))
        elif page=='profiles':
            self.box((84,134,330,245))
            for i,name in enumerate(model.profiles[:5]):self.text(name,250,186+i*33,18,'center',('profile',name),model.selected==name,width=295)
            arrow=self.texture('b_list_down.dds')
            arrow=arrow.crop(arrow.getchannel('A').getbbox()).resize((16,22))
            arrow.putalpha(arrow.getchannel('A').point(lambda a:a//3))
            self.image.alpha_composite(arrow,(242,344))
            self.text('New Profile',250,444,18,'center',('route','create'),disabled=len(model.profiles)>=5)
            for label,x,action in [('Quit',62,('route','quit')),('Delete',312,('delete',)),('Select',550,('select',))]:self.text(label,x,536,18,action=action,disabled=label!='Quit' and not model.selected)
        elif page in ('new','credits'):
            self.text('Simulation only - no game runtime',400,280,18,'center')
        if page not in ('main','create','profiles'):
            self.text('Back',62,536,18,action=('back',))
        if page in ('effects','advanced','keyboard','gamepad','game','sound'):
            self.text('Default Settings',748,536,18,'right',('defaults',))
        return self.image,self.hits


class CompleteSimulation:
    def __init__(self,root,report):
        import tkinter as tk
        self.root=root;self.screens=Screens(report);self.model=Model()
        self.page='create';self.modal=None;self.editing=None;self.typed='';self.hover=None
        self.focus=0;self.pressed=None;self.drag=None;self.mouse=None;self.closed=False
        root.title('OpenJade - menu simulation');root.resizable(False,False)
        self.canvas=tk.Canvas(root,width=800,height=600,highlightthickness=0,cursor='none');self.canvas.pack()
        self.status=tk.StringVar(value='Session-only simulation. Defaults are research baselines; the 3D background is not rendered.')
        tk.Label(root,textvariable=self.status,wraplength=790).pack()
        self.canvas.bind('<Motion>',self.motion);self.canvas.bind('<ButtonPress-1>',self.press)
        self.canvas.bind('<ButtonRelease-1>',self.release)
        self.canvas.bind('<Leave>',lambda e:self.leave())
        self.canvas.bind('<MouseWheel>',lambda e:self.scroll(-1 if e.delta>0 else 1))
        root.bind('<KeyPress>',self.key)
        root.bind('<FocusOut>',lambda e:self.cancel_drag())
        root.protocol('WM_DELETE_WINDOW',lambda:self.prompt('quit'))
        self.redraw();self.canvas.focus_set()

    def redraw(self):
        from PIL import ImageTk
        image,self.hits=self.screens.render(self.page,self.model,self.hover,self.modal,self.typed,self.editing)
        self.picture=ImageTk.PhotoImage(image);self.canvas.delete('all');self.canvas.create_image(0,0,image=self.picture,anchor='nw')
        if self.hits:
            self.focus%=len(self.hits)
        if self.mouse:
            self.cursor_picture=ImageTk.PhotoImage(self.screens.cursor)
            self.canvas.create_image(*self.mouse,image=self.cursor_picture,anchor='nw')

    def hit(self,x,y):return next((a for a,r in self.hits if r[0]<=x<r[2] and r[1]<=y<r[3]),None)
    def motion(self,event):
        self.mouse=(event.x,event.y);self.hover=self.hit(event.x,event.y)
        if self.drag:self.slide(self.drag,event.x)
        self.redraw()
    def leave(self):self.mouse=None;self.hover=None;self.redraw()
    def cancel_drag(self):self.drag=self.pressed=None
    def press(self,event):
        self.pressed=self.hit(event.x,event.y)
        if self.pressed and self.pressed[0]=='slider':self.drag=self.pressed;self.slide(self.drag,event.x);self.redraw()
    def release(self,event):
        if self.drag:self.slide(self.drag,event.x);self.cancel_drag();self.redraw();return
        action=self.hit(event.x,event.y);pressed=self.pressed;self.pressed=None
        if action and action==pressed:self.activate(action)
    def slide(self,action,x):
        _,group,index,values,start,end=action
        self.model.settings[group][index]=values[round(max(0,min(1,(x-start)/(end-start)))*(len(values)-1))]
    def show(self,page):
        self.page=page;self.modal=None;self.editing=None;self.typed='';self.hover=None;self.focus=0;self.cancel_drag();self.redraw()
    def prompt(self,kind):self.modal=kind;self.hover=None;self.focus=0;self.cancel_drag();self.redraw()
    def scroll(self,delta):
        if self.page in ('keyboard','gamepad') and not self.modal and not self.editing:self.model.scroll(delta);self.redraw()
    def back(self):
        if self.modal:self.modal=None;self.redraw();return
        if self.editing:self.editing=None;self.typed='';self.redraw();return
        if self.page in ('main','profiles') or self.page=='create' and not self.model.profiles:self.prompt('quit');return
        dest='main' if self.page in ('options','new','credits') else 'profiles' if self.page=='create' else 'options'
        if self.page in ('effects','advanced','keyboard','gamepad','game','sound','options') and self.model.dirty:
            self.destination=dest;self.prompt('settings')
        else:self.show(dest)

    def activate(self,action):
        if self.modal and action[0]!='answer':return
        kind=action[0]
        if kind=='answer':
            answer=action[1];modal=self.modal
            if modal=='settings':
                if answer=='Yes':self.model.save();self.show(self.destination)
                elif answer=='No':self.model.discard();self.show(self.destination)
                else:self.modal=None;self.redraw()
            elif modal=='quit' and answer=='Yes':self.closed=True;self.root.destroy()
            elif modal=='delete' and answer=='Yes':
                self.model.profiles.remove(self.model.selected)
                if self.model.active==self.model.selected:self.model.active=None
                self.model.selected=next(iter(self.model.profiles),None)
                self.show('profiles' if self.model.profiles else 'create')
            else:self.modal=None;self.redraw()
            return
        if kind=='route':
            if action[1]=='quit':self.prompt('quit')
            else:self.show(action[1])
        elif kind=='back':self.back()
        elif kind=='choice':self.model.settings[action[1]][action[2]]=action[3];self.redraw()
        elif kind=='step':
            _,group,index,values,delta=action;old=self.model.settings[group][index]
            self.model.settings[group][index]=values[max(0,min(len(values)-1,values.index(old)+delta))];self.redraw()
        elif kind=='defaults':
            self.model.defaults(self.page);self.status.set('Simulation baseline restored. Original factory defaults have not been verified.');self.redraw()
        elif kind=='scroll':self.scroll(action[1])
        elif kind=='binding':
            self.editing=action;self.typed=self.model.settings[action[1]][action[2]][action[3]]
            self.status.set('Edit an ASCII binding label: Enter saves, Escape cancels. This does not capture or bind hardware.');self.redraw()
        elif kind=='create':
            try:self.model.create(self.typed)
            except ValueError as error:self.status.set(str(error));return
            self.show('main')
        elif kind=='profile':self.model.selected=action[1];self.redraw()
        elif kind=='delete' and self.model.selected:self.prompt('delete')
        elif kind=='select' and self.model.selected:self.model.active=self.model.selected;self.show('main')

    def key(self,event):
        if event.keysym=='Escape':self.back();return 'break'
        if (self.page=='create' or self.editing) and not self.modal:
            if event.keysym=='Return':
                if self.editing:
                    _,page,row,col=self.editing;self.model.settings[page][row][col]=self.typed;self.editing=None;self.typed='';self.redraw()
                else:self.activate(('create',))
            elif event.keysym=='BackSpace':self.typed=self.typed[:-1];self.redraw()
            elif event.char and len(event.char)==1 and 32<=ord(event.char)<=126 and len(self.typed)<(24 if self.editing else 20):self.typed+=event.char;self.redraw()
            return 'break'
        if not self.hits:return 'break'
        if event.keysym in ('Tab','Up','Down'):
            self.focus=(self.focus+(-1 if event.keysym=='Up' or event.keysym=='Tab' and event.state&1 else 1))%len(self.hits)
            self.hover=self.hits[self.focus][0];self.redraw()
        elif event.keysym in ('Return','space'):self.activate(self.hits[self.focus][0])
        elif event.keysym in ('Left','Right'):
            action=self.hits[self.focus][0]
            if action[0]=='slider':self.activate(('step',*action[1:4],-1 if event.keysym=='Left' else 1))
        return 'break'


def smoke_test(viewer):
    v=viewer
    v.typed='Prince';v.activate(('create',));assert v.page=='main'
    v.show('game');v.activate(('choice','game',1,'No'));v.back();assert v.modal=='settings'
    v.activate(('answer','Cancel'));assert v.page=='game' and v.model.dirty
    v.back();v.activate(('answer','Yes'));assert not v.model.dirty
    v.show('game');v.activate(('defaults',));v.back();v.activate(('answer','No'))
    assert v.model.settings['game'][1]=='No'
    for page in ('options','effects','advanced','keyboard','gamepad','game','sound','profiles','create','main'):
        v.show(page);v.root.update();assert v.hits
    v.show('keyboard');v.scroll(100);assert v.model.offset==12
    v.activate(('binding','keyboard',17,1));v.typed='K'
    from types import SimpleNamespace
    v.key(SimpleNamespace(keysym='Return',char='',state=0));assert v.model.settings['keyboard'][17][1]=='K'
    v.show('profiles');v.activate(('delete',));v.activate(('answer','No'));assert v.model.profiles==['Prince']
    v.activate(('delete',));v.activate(('answer','Yes'));assert v.page=='create'
    v.prompt('quit');v.activate(('answer','No'));assert not v.closed
    import tkinter as tk
    assert not any(isinstance(child,tk.Toplevel) for child in v.root.winfo_children())
    v.prompt('quit');v.activate(('answer','Yes'));assert v.closed
    print('Complete simulation smoke test passed: ten screens, profiles, editing, scrolling, transactions and quit.')
