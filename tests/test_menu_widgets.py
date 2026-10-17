"""Real widget bounds, shared state and pointer/keyboard interaction checks."""
import sys
from pathlib import Path
from types import SimpleNamespace
import tkinter as tk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_scene import Scene,MenuState
from styled_menu_pages import StyledMenuPages

report=Path(sys.argv[1]);scene=Scene(report/'menus-assets');state=MenuState(scene.catalog)
assert state.slider('effects','ResolutionSlider',500)==10
assert state.slider('advanced','ResolutionSlider')==10
assert state.slider('keyboard','MouseSlider',-20)==0
assert state.slider('keyboard','MouseSlider',43)==43
assert state.slider('gamepad','MouseSlider')==43
assert state.move_row('keyboard',-1)==0
assert state.move_row('keyboard',100)==5
for page in ('effects','advanced','keyboard','gamepad'):
    image,hits=scene.render(page,state)
    for e,r in hits:assert 0<=r[0]<r[2]<=800 and 0<=r[1]<r[3]<=600,(page,e['name'],r)
root=tk.Tk();root.withdraw()
try:
    viewer=StyledMenuPages(root,report,lambda:None);viewer.show('advanced');root.update()
    slider=next(e for e,_ in viewer.hits if e['name']=='GammaSlider')
    y=slider['y'];x=round((slider['start']+slider['end'])/2)
    viewer.press(SimpleNamespace(x=x,y=y));viewer.motion(SimpleNamespace(x=slider['end']+100,y=y));viewer.release(SimpleNamespace(x=slider['end']+100,y=y))
    assert viewer.model.slider('advanced','GammaSlider')==100
    viewer.activate_entry('GammaSlider-minus');assert viewer.model.slider('advanced','GammaSlider')==99
    viewer.focus=next(i for i,(e,_) in enumerate(viewer.hits) if e['name']=='GammaSlider')
    viewer.adjust(-1);assert viewer.model.slider('advanced','GammaSlider')==98
    viewer.show('effects');assert viewer.model.slider('effects','GammaSlider')==98
    viewer.show('keyboard');viewer.activate_entry('ActionDown')
    assert viewer.model.rows['keyboard']==1
    assert viewer.hits[viewer.focus][0]['name']=='Key_2_1'
    viewer.activate_entry('ActionUp');assert viewer.model.rows['keyboard']==0
    viewer.clear();assert not viewer.model.rows
    viewer.close()
finally:root.destroy()
print('DDS widget checks passed: bounds, clamping, shared sliders, dragging, steps, keyboard and action arrows.')
