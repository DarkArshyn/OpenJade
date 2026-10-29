"""Exercise real Python handlers and observe the native settings consumer."""
from pathlib import Path
import sys,subprocess,time,json,tkinter as tk
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'src'))
from graphics_settings import SettingsBridge,parse
from simulation_screens import CompleteSimulation
folder=root/'reports/engine-gamma-20261028';path=folder/'menu.ojsettings'
bridge=SettingsBridge(path);bridge.publish(0,0)
window=tk.Tk();window.withdraw()
sim=CompleteSimulation(window,root/'reports/menu-effects-fix-8796132f9b234657a4a88218be9cb644',bridge)
sim.show('advanced')
log=folder/'integration.log'
with log.open('w') as stream:
    process=subprocess.Popen([str(root/'engine/target/debug/jade-viewer.exe'),'--scene',str(root/'reports/engine-textures-20261028/menu.ojscene'),'--menu',str(root/'reports/engine-ui-20261028/menu.ojui'),'--settings',str(path),'--validation','--smoke'],stdout=stream,stderr=subprocess.STDOUT)
    def wait(text):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if text in log.read_text():return
            if process.poll() is not None:raise AssertionError(log.read_text())
            time.sleep(.02)
        raise AssertionError('Timeout: '+text)
    wait('Swapchain 800x600')
    values=[f'{i/100:.2f}' for i in range(101)]
    sim.activate(('step','graphics',1,values,100))
    wait('Gamma preview: 100 (saved 0)')
    sim.back();sim.activate(('answer','Cancel'));assert parse(path.read_text())==(100,0)
    sim.back();sim.activate(('answer','No'))
    wait('Gamma preview: 0 (saved 0)')
    sim.show('advanced');sim.activate(('step','graphics',1,values,42));sim.back();sim.activate(('answer','Yes'))
    wait('Gamma preview: 42 (saved 42)')
    sim.show('advanced');sim.activate(('defaults',));sim.back();sim.activate(('answer','Yes'))
    assert parse(path.read_text())==(0,0)
    assert process.wait(timeout=20)==0
window.destroy()
assert 'validation errors: 0' in log.read_text()
(folder/'integration.json').write_text(json.dumps(dict(passed=True,preview=[100,0,42],transactions=['Cancel retains preview','No restores saved','Yes commits','Defaults previews zero then Yes commits'],validation_errors=0),indent=2))
print(log.read_text())
