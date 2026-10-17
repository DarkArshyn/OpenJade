"""Exercise real styled controls and their in-memory state without game writes."""
import sys
from pathlib import Path
import tkinter as tk
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from options_viewer import OptionsWindow

root=tk.Tk();root.withdraw()
try:
    window=OptionsWindow(root,Path(sys.argv[1]),lambda:None)
    window.show_effects();root.update()
    assert len(window.styled_controls)==11
    index=next(i for i,(e,_,_) in enumerate(window.styled_controls) if e['name']=='Item1_Choice2')
    window.activate_styled(index)
    assert window.model.values['Item1']=='Item1_Choice2'
    assert window.variables['Item1'].get()=='Item1_Choice2'
    back=next(i for i,(e,_,_) in enumerate(window.styled_controls) if e['name']=='Back')
    window.activate_styled(back);assert window.page=='options'
    window.show_effects();assert window.variables['Item1'].get()=='Item1_Choice2'
    window.clear();assert all(v is None for v in window.model.values.values())
    window.close()
    print('Styled Effects checks passed: 11 controls, choice, return, persistence and clear.')
finally:
    root.destroy()
