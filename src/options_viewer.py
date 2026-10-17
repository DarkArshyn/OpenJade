"""MGM-backed research navigation. Widgets and transitions are experimental."""
import hashlib
import json
from pathlib import Path
import tkinter as tk
import xml.etree.ElementTree as ET
from PIL import Image,ImageTk


def load_options(directory):
    report=json.loads((directory/'experiment.json').read_text(encoding='utf-8-sig'))
    entry=next(i for i in report['Inputs'] if Path(i['Path']).name.lower()=='pop4common.mgm')
    raw=Path(entry['Path']).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper()!=entry['SHA256'].upper():
        raise ValueError('Common MGM changed since report generation.')
    if b'<!DOCTYPE' in raw.upper():
        raise ValueError('Unsupported document declaration.')
    return parse_options(raw)


def parse_options(raw):
    root=ET.fromstring(raw)
    options=root.find(".//PAGE[NAME='P_Options']")
    page=root.find(".//PAGE[NAME='P_VideoMenu']")
    if options is None or page is None:
        raise ValueError('Required options pages are missing.')
    groups=[]
    for index in range(1,5):
        prefix='Item'+str(index)
        label=page.findtext("CHILDREN/TEXT[NAME='"+prefix+"_Label']/STRING")
        choices=[]
        for choice in range(1,4):
            name=prefix+'_Choice'+str(choice)
            node=page.find("CHILDREN/CHECKBOXINST[NAME='"+name+"']")
            text=node.findtext('LABEL') if node is not None else None
            if text:
                choices.append(dict(name=name,text=text))
        if not label or not choices:
            raise ValueError('Incomplete effects group: '+prefix)
        groups.append(dict(name=prefix,label=label,choices=choices))
    return dict(title=options.findtext("CHILDREN/TEXT[NAME='Title']/STRING"),groups=groups)


class EffectsModel:
    def __init__(self,groups):
        self.groups=groups
        self.values={g['name']:None for g in groups}

    def choose(self,group,value):
        definition=next((g for g in self.groups if g['name']==group),None)
        if definition is None or value not in [c['name'] for c in definition['choices']]:
            raise ValueError('Unknown effects choice.')
        self.values[group]=value

    def clear(self):
        self.values={g['name']:None for g in self.groups}


class OptionsWindow:
    def __init__(self,parent,directory,on_close):
        self.data=load_options(directory)
        self.directory=directory
        self.model=EffectsModel(self.data['groups'])
        self.on_close=on_close
        self.window=tk.Toplevel(parent)
        self.window.title('OpenJade - Options research')
        self.window.geometry('800x600')
        self.window.resizable(False,False)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.protocol('WM_DELETE_WINDOW',self.close)
        self.window.bind('<Escape>',lambda event:self.back())
        self.body=tk.Frame(self.window,bg='#181c24')
        self.body.pack(fill='both',expand=True)
        self.page='options'
        self.variables={}
        self.show_options()

    def heading(self,title):
        for widget in self.body.winfo_children(): widget.destroy()
        tk.Label(self.body,text=title,font=('Arial',24),fg='#bca07a',bg='#181c24').pack(pady=22)
        tk.Label(self.body,text='Research widgets - MGM labels, experimental navigation; no game settings are written.',
                 fg='white',bg='#181c24',wraplength=750).pack(pady=8)

    def show_options(self):
        self.page='options'
        self.heading(self.data['title'])
        button=tk.Button(self.body,text='Graphics / Effects',command=self.show_effects,width=28)
        button.pack(pady=35)
        tk.Label(self.body,text='Controls, Sounds and Game are not implemented in this viewer.',fg='white',bg='#181c24').pack()
        tk.Button(self.body,text='Back to main menu',command=self.close).pack(pady=35)
        button.focus_set()

    def show_effects(self):
        if (self.directory/'effects-assets'/'layout.json').exists():
            return self.show_styled_effects()
        self.page='effects'
        self.heading('Graphics / Effects')
        self.variables={}
        first=None
        for group in self.data['groups']:
            line=tk.Frame(self.body,bg='#181c24')
            line.pack(fill='x',padx=35,pady=12)
            tk.Label(line,text=group['label'],width=22,anchor='w',fg='#bca07a',bg='#181c24').pack(side='left')
            variable=tk.StringVar(value=self.model.values[group['name']] or '')
            self.variables[group['name']]=variable
            for choice in group['choices']:
                button=tk.Radiobutton(line,text=choice['text'],variable=variable,value=choice['name'],
                    command=lambda g=group['name'],v=variable:self.model.choose(g,v.get()),
                    indicatoron=False,width=12)
                button.pack(side='left',padx=4)
                first=first or button
        tk.Label(self.body,text='No initial selection: game defaults are unknown. Choices persist only while this window is open.\n'
                 'Shadow Effects: MGM says High / Low / None; supplied screenshot says High / Medium / None.',
                 fg='white',bg='#181c24',wraplength=730).pack(pady=15)
        tk.Button(self.body,text='Clear research choices',command=self.clear).pack(pady=5)
        tk.Button(self.body,text='Back to Options',command=self.show_options).pack(pady=10)
        first.focus_set()

    def show_styled_effects(self):
        self.page='effects'
        for widget in self.body.winfo_children(): widget.destroy()
        folder=self.directory/'effects-assets'
        layout=json.loads((folder/'layout.json').read_text())
        report=json.loads((self.directory/'experiment.json').read_text(encoding='utf-8-sig'))
        common=next(i for i in report['Inputs'] if Path(i['Path']).name.lower()=='pop4common.mgm')
        if layout['source_sha256'].lower()!=common['SHA256'].lower():
            raise ValueError('Effects layout belongs to a different MGM revision.')
        self.variables={g['name']:tk.StringVar(value=self.model.values[g['name']] or '') for g in self.data['groups']}
        canvas=tk.Canvas(self.body,width=800,height=600,highlightthickness=0)
        canvas.pack()
        with Image.open(folder/'background.png') as im: background=im.copy()
        self.styled_images=[ImageTk.PhotoImage(background)]
        canvas.create_image(0,0,image=self.styled_images[0],anchor='nw')
        controls=[]
        for entry in layout['entries']:
            if not entry['interactive']: continue
            name=entry['name'];pictures={}
            with Image.open(folder/name/'mask.png') as im: alpha=im.copy()
            for state,color in [('normal',tuple(entry['color'])),('chosen',(255,255,255,255)),('hover',(232,220,193,255))]:
                ink=Image.new('RGBA',alpha.size,color);ink.putalpha(alpha)
                image=ImageTk.PhotoImage(ink);self.styled_images.append(image);pictures[state]=image
            group=name.split('_')[0]
            selected=self.model.values.get(group)==name
            item=canvas.create_image(entry['x'],entry['y'],image=pictures['chosen' if selected else 'normal'],anchor='nw')
            controls.append((entry,item,pictures))
        self.styled_controls=controls
        focus=[0]
        outline=canvas.create_rectangle(0,0,0,0,outline='#e8dcc1')
        def redraw():
            for e,item,pictures in controls:
                chosen=self.model.values.get(e['name'].split('_')[0])==e['name']
                canvas.itemconfigure(item,image=pictures['chosen' if chosen else 'normal'])
            e=controls[focus[0]][0]
            canvas.coords(outline,e['x']-3,e['y']-3,e['x']+e['width']+3,e['y']+e['height']+3)
        def activate(index):
            e=controls[index][0]
            if e['name']=='Back': self.show_options();return
            group=e['name'].split('_')[0]
            self.model.choose(group,e['name']);self.variables[group].set(e['name']);redraw()
        def move(delta):
            focus[0]=(focus[0]+delta)%len(controls);redraw();return 'break'
        self.activate_styled=activate
        for index,(e,item,pictures) in enumerate(controls):
            canvas.tag_bind(item,'<Button-1>',lambda event,i=index:activate(i))
            canvas.tag_bind(item,'<Enter>',lambda event,i=index:(focus.__setitem__(0,i),redraw(),canvas.itemconfigure(controls[i][1],image=controls[i][2]['hover'])))
            canvas.tag_bind(item,'<Leave>',lambda event:redraw())
        canvas.bind('<Tab>',lambda event:move(-1 if event.state&1 else 1))
        canvas.bind('<Right>',lambda event:move(1))
        canvas.bind('<Left>',lambda event:move(-1))
        canvas.bind('<Down>',lambda event:move(1))
        canvas.bind('<Up>',lambda event:move(-1))
        canvas.bind('<Return>',lambda event:activate(focus[0]))
        canvas.bind('<space>',lambda event:activate(focus[0]))
        canvas.bind('<Key-c>',lambda event:self.clear())
        canvas.create_text(400,580,text='Research: Tab/arrows, Enter, Esc back, C clear | No game settings changed',fill='#aaa',font=('Arial',10))
        canvas.focus_set();redraw()

    def clear(self):
        self.model.clear()
        self.show_effects()

    def back(self):
        if self.page=='effects': self.show_options()
        else: self.close()
        return 'break'

    def close(self):
        self.window.grab_release()
        self.window.destroy()
        self.on_close()
