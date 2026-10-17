"""Five resource-based pages with explicit research-only interactions."""
import json
from pathlib import Path
import tkinter as tk
from tkinter import simpledialog
from PIL import ImageTk
from menu_scene import Scene,MenuState


class StyledMenuPages:
    def __init__(self,parent,directory,on_close,embedded=False):
        self.directory=Path(directory)
        self.scene=Scene(self.directory/'menus-assets')
        report=json.loads((self.directory/'experiment.json').read_text(encoding='utf-8-sig'))
        common=next(i for i in report['Inputs'] if Path(i['Path']).name.lower()=='pop4common.mgm')
        if self.scene.catalog['source_sha256'].lower()!=common['SHA256'].lower():
            raise ValueError('Menu assets do not match the prototype report.')
        self.model=MenuState(self.scene.catalog)
        self.on_close=on_close;self.closed=False;self.page='options';self.focus=0;self.hover=None
        self.window=parent if embedded else tk.Toplevel(parent)
        self.window.title('OpenJade - resource menu research')
        self.window.resizable(False,False)
        if not embedded:self.window.transient(parent)
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.canvas=tk.Canvas(self.window,width=800,height=600,highlightthickness=0)
        self.canvas.pack()
        self.status=tk.StringVar(value='Research choices only. No game settings or device bindings are written.')
        tk.Label(self.window,textvariable=self.status,wraplength=790).pack(fill='x')
        tk.Label(self.window,text='Tab/arrows: focus | Enter/Space: choose/edit | Esc: back | C: clear page').pack()
        self.window.bind('<Escape>',lambda event:self.back())
        self.canvas.bind('<Tab>',lambda event:self.move(-1 if event.state&1 else 1))
        for key,delta in [('Up',-1),('Down',1)]:
            self.canvas.bind('<'+key+'>',lambda event,d=delta:self.move(d))
        for key,delta in [('Left',-1),('Right',1)]:
            self.canvas.bind('<'+key+'>',lambda event,d=delta:self.adjust(d))
        self.canvas.bind('<Return>',lambda event:self.activate())
        self.canvas.bind('<space>',lambda event:self.activate())
        self.canvas.bind('<Key-c>',lambda event:self.clear())
        self.canvas.bind('<Motion>',self.motion)
        self.canvas.bind('<Leave>',lambda event:self.leave())
        self.canvas.bind('<ButtonPress-1>',self.press)
        self.canvas.bind('<ButtonRelease-1>',self.release)
        self.window.bind('<FocusOut>',lambda event:self.cancel_drag())
        self.pressed=None
        self.dragging=None
        self.window.grab_set();self.show('options');self.canvas.focus_set()

    def show(self,page):
        if page not in self.scene.catalog['pages']:raise ValueError('Unknown page.')
        self.page=page;self.focus=0;self.hover=None;self.pressed=None;self.dragging=None
        notices={
            'options':'Sounds and Game are not implemented (grey).',
            'effects':'MGM shadows: High / Low / None. Sliders use raw research units; no graphics settings applied.',
            'advanced':'Screenshot labels in MGM slots. Sliders use raw research units, not verified resolution or gamma.',
            'keyboard':'Six screenshot sample actions. Click a binding to edit research text; no key capture.',
            'gamepad':'Screenshot sample bindings. Text editing only; no controller detection or input capture.'}
        self.status.set(notices[page]);self.redraw()
    def show_options(self):self.show('options')
    def show_effects(self):self.show('effects')
    def redraw(self):
        image,self.hits=self.scene.render(self.page,self.model,self.hover)
        self.picture=ImageTk.PhotoImage(image)
        self.canvas.delete('all');self.canvas.create_image(0,0,image=self.picture,anchor='nw')
        if self.hits:
            self.focus%=len(self.hits)
            self.canvas.create_rectangle(*self.hits[self.focus][1],outline='#e8dcc1')
    def hit(self,x,y):
        return next((i for i,(_,r) in enumerate(self.hits) if r[0]<=x<r[2] and r[1]<=y<r[3]),None)
    def motion(self,event):
        if self.dragging is not None:
            self.set_slider_from_x(self.dragging,event.x);return
        index=self.hit(event.x,event.y)
        hover=self.hits[index][0]['name'] if index is not None else None
        if hover!=self.hover:
            self.hover=hover
            if index is not None:self.focus=index
            self.redraw()
    def leave(self):
        self.hover=None
        if self.dragging is None:self.pressed=None
        self.redraw()
    def cancel_drag(self):
        self.dragging=None;self.pressed=None
    def press(self,event):
        self.pressed=self.hit(event.x,event.y)
        if self.pressed is not None:
            self.focus=self.pressed
            e=self.hits[self.pressed][0]
            if e['kind']=='slider':
                self.dragging=e;self.set_slider_from_x(e,event.x)
    def release(self,event):
        if self.dragging is not None:
            self.set_slider_from_x(self.dragging,event.x);self.dragging=None;self.pressed=None;return
        index=self.hit(event.x,event.y)
        pressed=self.pressed;self.pressed=None
        if index is not None and pressed==index:self.focus=index;self.activate()
    def move(self,delta):
        self.focus=(self.focus+delta)%len(self.hits);self.hover=None;self.pressed=None;self.redraw()
        return 'break'
    def set_slider_from_x(self,entry,x):
        ratio=max(0,min(1,(x-entry['start'])/(entry['end']-entry['start'])))
        self.model.slider(self.page,entry['name'],entry['minimum']+ratio*(entry['maximum']-entry['minimum']))
        self.slider_status(entry['name']);self.redraw()
    def slider_status(self,name):
        self.status.set(name+': '+str(self.model.slider(self.page,name))+' (raw MGM research value; not applied to the game)')
    def adjust(self,delta):
        entry=self.hits[self.focus][0]
        if entry['kind']=='slider':
            self.model.slider(self.page,entry['name'],self.model.slider(self.page,entry['name'])+delta)
            self.slider_status(entry['name']);self.redraw();return 'break'
        return self.move(delta)
    def activate(self):
        self.activate_entry(self.hits[self.focus][0]['name'])
        return 'break'
    def activate_entry(self,name,binding_text=None):
        entry=next((e for e,_ in self.hits if e['name']==name),None)
        if entry is None:return
        if entry.get('disabled'):return
        kind=entry.get('kind')
        if kind=='row':
            row=self.model.move_row(self.page,entry['delta'])
            self.focus=next(i for i,(e,_) in enumerate(self.hits) if e['name']==f'Key_{row+1}_1')
            self.status.set(f'Research action row {row+1}/6. Additional actions have not been established.')
            self.redraw()
        elif kind=='step':
            name=entry['slider'];self.model.slider(self.page,name,self.model.slider(self.page,name)+entry['delta'])
            self.slider_status(name);self.redraw()
        elif kind=='slider':self.slider_status(entry['name'])
        elif kind=='route':
            if entry['route']=='close':self.close()
            else:self.show(entry['route'])
        elif kind=='choice':
            self.model.choose(self.page,entry['group'],entry['value']);self.redraw()
        elif kind=='binding':
            self.model.rows[self.page]=int(name.split('_')[1])-1
            value=binding_text
            if value is None:
                value=simpledialog.askstring('Research binding label','Printable ASCII label (1-24 characters). This does not bind a device.',
                    initialvalue=self.model.bindings.get((self.page,name),entry['text']),parent=self.window)
                self.window.grab_set();self.canvas.focus_set()
            if value is not None:
                try:self.model.bind(self.page,name,value)
                except ValueError as error:self.status.set(str(error));return
                self.redraw()
    def clear(self):
        self.model.clear(self.page);self.status.set('Research changes cleared for this page; screenshot samples restored. Not game defaults.');self.redraw()
        return 'break'
    def back(self):
        if self.page=='options':self.close()
        else:self.show_options()
        return 'break'
    def close(self):
        if not self.closed:
            self.closed=True;self.window.grab_release();self.window.destroy();self.on_close()
