"""Interactive research viewer. Input behavior is experimental, not game logic."""
import argparse
import json
import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
import tkinter as tk
from types import SimpleNamespace
from PIL import Image, ImageTk


def state_for(index, selected, hover, pressed, disabled=False):
    if disabled:
        return 'DISABLED'
    if index == pressed and index == selected:
        return 'PRESSED'
    if index == hover:
        return 'OVER'
    return 'SELECTED' if index == selected else 'ENABLED'


def load_state_colors(directory):
    experiment=json.loads((directory/'experiment.json').read_text(encoding='utf-8-sig'))
    documents={}
    for name in ('pop4mainmenu.mgm','pop4common.mgm'):
        entry=next(item for item in experiment['Inputs'] if Path(item['Path']).name.lower()==name)
        raw=Path(entry['Path']).read_bytes()
        if hashlib.sha256(raw).hexdigest().upper()!=entry['SHA256'].upper():
            raise ValueError('MGM changed since prototype generation: '+name)
        if b'<!DOCTYPE' in raw.upper():
            raise ValueError('Document type declarations are unsupported.')
        documents[name]=ET.fromstring(raw)
    page=documents['pop4mainmenu.mgm'].find(".//PAGE[NAME='P_MainMenu']")
    colors=[]
    for row in experiment['Rows']:
        button=page.find("./CHILDREN/BUTTONINST[NAME='"+row['Name']+"']")
        area=button.findtext('LINK/AREA')
        definition=documents['pop4common.mgm'].find(".//BUTTON[NAME='"+area+"']")
        palette={}
        for state in ('ENABLED','SELECTED','OVER','PRESSED','DISABLED'):
            frame=definition.findtext('TIMINGS/'+state)
            value=definition.findtext("CHILDREN/TEXT/KEYFRAMES/KEYFRAME[IDX='"+frame+"']/COLOR")
            rgba=tuple(map(int,value.split()))
            if len(rgba)!=4 or any(v<0 or v>255 for v in rgba):
                raise ValueError('Invalid state color.')
            palette[state]=rgba
        colors.append(palette)
    return colors


class Selection:
    def __init__(self, count):
        if count < 1:
            raise ValueError('At least one entry is required.')
        self.count = count
        self.index = 0

    def move(self, delta):
        self.index = (self.index + delta) % self.count
        return self.index

    def choose(self, index):
        if not 0 <= index < self.count:
            raise ValueError('Invalid entry index.')
        self.index = index


def load_assets(directory):
    report = json.loads((directory / 'comparison.json').read_text(encoding='utf-8'))
    rows = report['rows']
    if [r['name'] for r in rows] != ['NewGame', 'LoadGame', 'Options', 'Credits', 'Quit', 'Back']:
        raise ValueError('Expected a six-entry OpenJade menu prototype report.')
    with Image.open(directory / 'prototype.png') as source:
        if source.size != (800, 600):
            raise ValueError('Expected an 800x600 prototype.')
        background = source.convert('RGB')
    for row in rows:
        x, y = row['rounded_ink_xy']
        w, h = row['ink_size']
        if not (0 <= x < x+w <= 800 and 0 <= y < y+h <= 600):
            raise ValueError('Invalid entry bounds.')
    return rows, background


class Viewer:
    def __init__(self, root, directory):
        self.root = root
        self.rows, background = load_assets(directory)
        self.selection = Selection(len(self.rows))
        self.hover = None
        self.pressed = None
        self.closed = False
        self.key_down = None
        self.colors = load_state_colors(directory)
        root.title('OpenJade - experimental menu viewer')
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=800, height=600, highlightthickness=0)
        self.canvas.pack()
        self.picture = ImageTk.PhotoImage(background)
        self.canvas.create_image(0, 0, image=self.picture, anchor='nw')
        self.state_images=[]
        self.label_items=[]
        for index,row in enumerate(self.rows):
            with Image.open(directory/row['name']/'text.png') as source:
                alpha=source.getchannel('A')
            alpha=alpha.crop(alpha.getbbox()).resize(tuple(row['ink_size']),Image.Resampling.BILINEAR)
            pictures={}
            for state,rgba in self.colors[index].items():
                layer=Image.new('RGBA',alpha.size,rgba)
                layer.putalpha(alpha.point(lambda a: round(a*rgba[3]/255)))
                solid=Image.new('RGBA',alpha.size,'#181c24')
                pictures[state]=ImageTk.PhotoImage(Image.alpha_composite(solid,layer))
            self.state_images.append(pictures)
            self.label_items.append(self.canvas.create_image(*row['rounded_ink_xy'],image=pictures['ENABLED'],anchor='nw'))
        self.box = self.canvas.create_rectangle(0,0,0,0,outline='#e8dcc1',width=1)
        tk.Label(root, text='Research controls: Up/Down or Tab | Enter/Space: simulate | Esc: close | Mouse: select/click').pack()
        self.status = tk.StringVar(value='Experimental focus outline. Actions are simulated; no game is launched.')
        tk.Label(root, textvariable=self.status, anchor='w').pack(fill='x')
        self.disabled=tk.BooleanVar(value=False)
        tk.Checkbutton(root,text='Research: preview disabled state (blocks simulated actions)',variable=self.disabled,command=self.reset_input).pack()
        root.bind('<Up>', lambda event: self.navigate(-1))
        root.bind('<Down>', lambda event: self.navigate(1))
        root.bind('<Tab>', lambda event: self.navigate(-1 if event.state & 1 else 1))
        for key in ('Return','space'):
            root.bind('<KeyPress-'+key+'>', self.key_press)
            root.bind('<KeyRelease-'+key+'>', self.key_release)
        root.bind('<FocusOut>',lambda event:self.reset_input())
        root.bind('<Escape>', lambda event: self.close())
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.canvas.bind('<Motion>', self.motion)
        self.canvas.bind('<Leave>', lambda event: self.leave())
        self.canvas.bind('<ButtonPress-1>', self.press)
        self.canvas.bind('<ButtonRelease-1>', self.release)
        self.canvas.focus_set()
        self.refresh()

    def hit(self, x, y):
        for index, row in enumerate(self.rows):
            left, top = row['rounded_ink_xy']
            w, h = row['ink_size']
            if left-5 <= x < left+w+5 and top-5 <= y < top+h+5:
                return index
        return None

    def refresh(self):
        for index,item in enumerate(self.label_items):
            state=state_for(index,self.selection.index,self.hover,self.pressed,self.disabled.get())
            self.canvas.itemconfigure(item,image=self.state_images[index][state])
        row = self.rows[self.selection.index]
        x, y = row['rounded_ink_xy']
        w, h = row['ink_size']
        self.canvas.coords(self.box, x-5, y-5, x+w+5, y+h+5)
        self.canvas.itemconfigure(self.box, outline='#ffffff' if self.pressed is not None else '#e8dcc1')

    def navigate(self, delta):
        self.pressed = None
        self.key_down = None
        self.hover = None
        self.selection.move(delta)
        self.refresh()
        return 'break'

    def motion(self, event):
        self.hover = self.hit(event.x, event.y)
        if self.hover is not None:
            self.selection.choose(self.hover)
        self.refresh()

    def reset_input(self):
        self.key_down=None
        self.pressed=None
        self.hover=None
        self.refresh()

    def key_press(self,event):
        if self.key_down is None and not self.disabled.get():
            self.key_down=event.keysym
            self.pressed=self.selection.index
            self.hover=None
            self.refresh()
        return 'break'

    def key_release(self,event):
        if self.key_down==event.keysym:
            target=self.pressed
            self.key_down=None
            self.pressed=None
            self.refresh()
            if target==self.selection.index:
                self.activate()
        return 'break'

    def leave(self):
        self.hover = None
        self.pressed = None
        self.refresh()

    def press(self, event):
        self.pressed = self.hit(event.x, event.y)
        if self.pressed is not None:
            self.selection.choose(self.pressed)
        self.refresh()

    def release(self, event):
        target = self.hit(event.x, event.y)
        activate = target is not None and target == self.pressed
        self.pressed = None
        self.refresh()
        if activate:
            self.activate()

    def activate(self):
        if self.disabled.get():
            return 'break'
        row = self.rows[self.selection.index]
        self.status.set('Simulated action: '+row['text']+' ['+row['name']+']. No game action performed.')
        return 'break'

    def close(self):
        if not self.closed:
            self.closed = True
            self.root.destroy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('--smoke-test', action='store_true')
    args = parser.parse_args()
    root = tk.Tk()
    if args.smoke_test:
        root.withdraw()
    viewer = Viewer(root, args.report)
    if args.smoke_test:
        root.update()
        viewer.navigate(-1)
        assert viewer.selection.index == 5
        viewer.activate()
        assert '[Back]' in viewer.status.get()
        assert viewer.hit(0, 0) is None
        x,y=viewer.rows[0]['rounded_ink_xy']
        event=SimpleNamespace(x=x,y=y)
        viewer.motion(event)
        assert viewer.selection.index==0
        viewer.press(event)
        viewer.release(SimpleNamespace(x=0,y=0))
        assert '[Back]' in viewer.status.get()
        viewer.press(event)
        viewer.release(event)
        assert '[NewGame]' in viewer.status.get()
        viewer.leave()
        assert viewer.pressed is None
        viewer.key_press(SimpleNamespace(keysym='Return'))
        assert viewer.pressed==0
        viewer.key_release(SimpleNamespace(keysym='Return'))
        assert viewer.pressed is None
        previous=viewer.status.get()
        viewer.disabled.set(True)
        viewer.navigate(1)
        viewer.activate()
        assert viewer.status.get()==previous
        viewer.close()
        print('GUI smoke test passed: assets, widgets, navigation, simulated action and disposal.')
    else:
        root.mainloop()


if __name__ == '__main__':
    main()
