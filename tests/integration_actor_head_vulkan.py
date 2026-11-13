"""Compare a frozen head diagnostic against its isolated native GPU reference."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from PIL import Image, ImageDraw


def verify(scene, reference, output, viewer):
    output.mkdir(parents=True, exist_ok=False)
    env=dict(os.environ,OPENJADE_CAPTURE_SECONDS='0',VK_INSTANCE_LAYERS='VK_LAYER_LUNARG_screenshot',
             VK_SCREENSHOT_FRAMES='11,21',VK_SCREENSHOT_DIR=str(output.resolve()))
    with (output/'validation.txt').open('w') as log:
        proc=subprocess.Popen([str(viewer.resolve()),'--scene',str(scene.resolve()),
                               '--color-pipeline','legacy-unorm','--validation'],
                              cwd=output,env=env,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    with Image.open(output/'21.ppm') as image:
                        image.load(); actual=np.asarray(image.convert('RGB'))
                    break
                except OSError:
                    if proc.poll() is not None: raise RuntimeError('Viewer exited; inspect validation.txt')
                    time.sleep(.1)
            else: raise RuntimeError('Vulkan screenshot timed out')
        finally:
            if proc.poll() is None: proc.terminate()
            proc.wait()
    log=(output/'validation.txt').read_text()
    assert 'VUID-' not in log and 'Validation Error' not in log
    assert np.array_equal(np.asarray(Image.open(output/'11.ppm').convert('RGB')),actual)
    native=np.asarray(Image.open(reference).convert('RGB'))
    assert native.shape==actual.shape==(600,800,3)
    native_mask=np.any(native!=0,axis=2); actual_mask=np.any(actual!=0,axis=2)
    union=native_mask|actual_mask
    assert union.any()
    delta=np.abs(native.astype(int)-actual.astype(int))
    result=dict(mean_absolute_rgb=float(delta[union].mean()),max_channel_delta=int(delta.max()),
                changed_pixels=int(np.any(delta!=0,axis=2).sum()),
                silhouette_iou=float((native_mask&actual_mask).sum()/union.sum()),
                native_pixels=int(native_mask.sum()),vulkan_pixels=int(actual_mask.sum()),
                identical_fixed_time_frames=True,validation_errors=0)
    Image.fromarray(actual).save(output/'vulkan.png')
    canvas=Image.new('RGB',(1600,630),'#182028')
    canvas.paste(Image.fromarray(native),(0,30));canvas.paste(Image.fromarray(actual),(800,30))
    draw=ImageDraw.Draw(canvas);draw.text((20,8),'GOG: isolated native draw',fill='white')
    draw.text((820,8),'OpenJade Vulkan: frozen reconstructed sample',fill='white')
    canvas.save(output/'comparison.png')
    (output/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    assert result['mean_absolute_rgb']<.5 and result['silhouette_iou']>.995
    assert result['max_channel_delta']<=64
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('scene',type=Path);parser.add_argument('reference',type=Path);parser.add_argument('output',type=Path)
    parser.add_argument('--viewer',type=Path,default=Path(__file__).resolve().parents[1]/'engine/target/debug/jade-viewer.exe')
    args=parser.parse_args()
    print(json.dumps(verify(args.scene,args.reference,args.output,args.viewer),indent=2))
