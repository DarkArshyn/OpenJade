"""Capture a prepared Prince scene and check stable frames and Vulkan validation."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import numpy as np
from PIL import Image


def verify(scene,output,viewer,seconds=0.):
    output.mkdir(parents=True,exist_ok=False)
    env=dict(os.environ,OPENJADE_CAPTURE_SECONDS=str(seconds),VK_INSTANCE_LAYERS='VK_LAYER_LUNARG_screenshot',
             VK_SCREENSHOT_FRAMES='11,21',VK_SCREENSHOT_DIR=str(output.resolve()))
    with (output/'validation.txt').open('w') as log:
        process=subprocess.Popen([str(viewer.resolve()),'--scene',str(scene.resolve()),'--color-pipeline','legacy-unorm','--validation'],cwd=output,env=env,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    image=Image.open(output/'21.ppm');image.load();break
                except OSError:
                    if process.poll() is not None:raise RuntimeError('Viewer exited before capture')
                    time.sleep(.1)
            else:raise RuntimeError('Vulkan capture timeout')
        finally:
            if process.poll() is None:process.terminate()
            process.wait()
    text=(output/'validation.txt').read_text()
    if 'VUID-' in text or 'Validation Error' in text:raise AssertionError('Vulkan validation error')
    first=np.array(Image.open(output/'11.ppm').convert('RGB'));last=np.array(image.convert('RGB'))
    assert first.shape==last.shape==(600,800,3) and np.array_equal(first,last)
    visible=np.any(last!=last[0,0],axis=2)
    assert visible.sum()>10000,'Missing visible character'
    image.save(output/'prince.png')
    result=dict(identical_fixed_time_frames=True,validation_errors=0,foreground_pixels=int(visible.sum()),
                original_game_pixel_parity_tested=False)
    (output/'validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('scene',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--viewer',type=Path,default=Path(__file__).resolve().parents[1]/'engine/target/debug/jade-viewer.exe')
    p.add_argument('--seconds',type=float,default=0.)
    a=p.parse_args();print(json.dumps(verify(a.scene,a.output,a.viewer,a.seconds),indent=2))
