"""Local GPU check: deterministic rain poses and visible contribution, not fidelity proof."""
import argparse,json,os,subprocess,time
from pathlib import Path
import numpy as np
from PIL import Image

def capture(viewer,scene,directory,seconds,disabled,effect="rain"):
    directory.mkdir()
    env=dict(os.environ,OPENJADE_CAPTURE_SECONDS=str(seconds),VK_INSTANCE_LAYERS='VK_LAYER_LUNARG_screenshot',VK_SCREENSHOT_FRAMES='11,21',VK_SCREENSHOT_DIR=str(directory))
    with (directory/'validation.txt').open('w') as log:
        proc=subprocess.Popen([str(viewer),'--scene',str(scene),'--color-pipeline','legacy-unorm','--validation',*(['--no-'+effect] if disabled else [])],cwd=directory,env=env,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    with Image.open(directory/'21.ppm') as image:
                        image.load();result=np.asarray(image.convert('RGB'))
                    break
                except OSError:
                    if proc.poll() is not None: raise RuntimeError('Viewer exited; inspect validation.txt')
                    time.sleep(.1)
            else:raise RuntimeError('Screenshot layer timeout')
        finally:
            if proc.poll() is None:proc.terminate()
            proc.wait()
    with Image.open(directory/'11.ppm') as first:
        if not np.array_equal(np.asarray(first.convert('RGB')),result):raise AssertionError('Fixed-time pose changed')
    text=(directory/'validation.txt').read_text()
    if 'VUID-' in text or 'Validation Error' in text:raise AssertionError('Vulkan validation error')
    label='Native menu rain: ' if effect=='rain' else 'Menu '+effect+': '
    if label+('disabled' if disabled else 'enabled') not in text:raise AssertionError('Unexpected rain state')
    Image.fromarray(result).save(directory/'capture.png')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--viewer',type=Path,default=Path(__file__).resolve().parents[1]/'engine/target/debug/jade-viewer.exe')
    p.add_argument('--effect',choices=['rain','splashes','birds','flight','pollen'],default='rain')
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);rows=[]
    for seconds in ((0,4,8,12) if a.effect=='flight' else (0,1,2)):
        off=capture(a.viewer.resolve(),a.scene.resolve(),out/f'{seconds}-off',seconds,True,a.effect)
        on=capture(a.viewer.resolve(),a.scene.resolve(),out/f'{seconds}-on',seconds,False,a.effect)
        error=np.abs(on.astype(int)-off.astype(int));changed=int(np.any(error,axis=2).sum())
        if a.effect!='flight' and ((seconds==0 and changed!=0) or (seconds>0 and changed==0)):raise AssertionError('Unexpected particle contribution')
        Image.fromarray(np.minimum(error*8,255).astype('uint8')).save(out/f'{seconds}-difference-x8.png')
        rows.append(dict(seconds=seconds,changed_pixels=changed,max_channel_change=int(error.max())))
    if a.effect=='flight' and not any(row['changed_pixels'] for row in rows):raise AssertionError('No visible mesh flight contribution')
    (out/'comparison.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows,indent=2))
