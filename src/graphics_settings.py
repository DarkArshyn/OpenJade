"""Small versioned bridge between the Python controls and the native viewer."""
from pathlib import Path
import os

def parse(text):
    lines=text.splitlines()
    if len(text)>64 or len(lines)!=3 or lines[0]!='OJSET001':raise ValueError('Invalid settings header')
    if any(not s.isascii() or not s.isdecimal() for s in lines[1:]):raise ValueError('Invalid gamma')
    values=tuple(map(int,lines[1:]))
    if any(not 0<=v<=100 for v in values):raise ValueError('Gamma outside 0..100')
    return values

class SettingsBridge:
    def __init__(self,path):
        self.path=Path(path).resolve();self.last=None
        # Never use this bridge to modify installation data or unrelated files.
        game=Path(__file__).resolve().parents[1]/'game'
        if self.path==game or game in self.path.parents:raise ValueError('Game directory is read-only')
        if self.path.suffix!='.ojsettings':raise ValueError('Use an .ojsettings file')
        self.saved=0
        if self.path.exists():
            if self.path.stat().st_size>64:raise ValueError('Settings too large')
            _,self.saved=parse(self.path.read_text(encoding='ascii'))
    def publish(self,preview,saved):
        text=f'OJSET001\n{preview}\n{saved}\n';parse(text)
        if text==self.last:return
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_name(self.path.name+f'.{os.getpid()}.tmp')
        try:
            with temporary.open('x',encoding='ascii',newline='\n') as f:f.write(text)
            os.replace(temporary,self.path)
        finally:
            if temporary.exists():temporary.unlink()
        self.last=text
