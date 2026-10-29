"""Single-window menu simulation; settings live only for this session."""
import argparse
from copy import deepcopy
from pathlib import Path
import tkinter as tk
from PIL import Image, ImageTk
from styled_menu_pages import StyledMenuPages


class SettingsSession:
    fields = ('values', 'bindings', 'sliders')

    def __init__(self, model):
        self.model = model
        self.commit()

    def snapshot(self):
        return {key: deepcopy(getattr(self.model, key)) for key in self.fields}

    @property
    def dirty(self):
        return self.snapshot() != self.saved

    def commit(self):
        self.saved = self.snapshot()

    def discard(self):
        for key, value in self.saved.items():
            setattr(self.model, key, deepcopy(value))


from simulation_screens import CompleteSimulation as Simulation, smoke_test


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report',type=Path)
    parser.add_argument('--smoke-test',action='store_true')
    parser.add_argument('--settings',type=Path,help='OpenJade .ojsettings bridge for live native gamma')
    args=parser.parse_args()
    from graphics_settings import SettingsBridge
    bridge=SettingsBridge(args.settings) if args.settings else None
    root=tk.Tk()
    if args.smoke_test:root.withdraw()
    viewer=Simulation(root,args.report,bridge)
    if args.smoke_test:smoke_test(viewer)
    else:root.mainloop()


if __name__=='__main__':main()
