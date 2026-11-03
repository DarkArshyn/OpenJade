"""Optional GPU regression: compare Vulkan menu blur to the independent reference.

Requires a prepared native menu scene, a built viewer and the Vulkan SDK
screenshot layer. Captures contain local game-derived data; keep outputs ignored.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from reconstruct_menu_blur import reconstruct,sample,q
from compare_menu_postprocess import composite


def capture(viewer,scene,directory,disabled,additive=False):
    directory.mkdir()
    env=dict(os.environ,OPENJADE_CAPTURE_SECONDS="0",VK_INSTANCE_LAYERS="VK_LAYER_LUNARG_screenshot",
             VK_SCREENSHOT_FRAMES="11,21",VK_SCREENSHOT_DIR=str(directory))
    with (directory/"validation.txt").open("w") as log:
        proc=subprocess.Popen([str(viewer),"--scene",str(scene),"--color-pipeline","legacy-unorm","--validation",
                               *(["--no-menu-blur"] if disabled else []), *([] if additive else ["--no-menu-additive"])],cwd=directory,env=env,stdout=log,stderr=log)
        try:
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    with Image.open(directory/"21.ppm") as image:
                        image.load()
                        result=np.array(image.convert("RGB"))
                    break
                except (OSError,FileNotFoundError):
                    if proc.poll() is not None:
                        raise RuntimeError("Viewer exited before capture; inspect validation.txt")
                    time.sleep(.1)
            else:raise RuntimeError("Capture timeout; check Vulkan screenshot layer availability")
        finally:
            if proc.poll() is None:proc.terminate()
            proc.wait()
    with Image.open(directory/"11.ppm") as earlier:
        if not np.array_equal(np.asarray(earlier.convert("RGB")),result):
            raise AssertionError("Fixed-time output changed between frames 11 and 21")
    text=(directory/"validation.txt").read_text()
    if "VUID-" in text or "Validation Error" in text:raise AssertionError("Vulkan validation error")
    expected="disabled" if disabled else "enabled"
    if f"Native menu blur: {expected}" not in text:raise AssertionError("Expected native blur state unavailable")
    if result.shape!=(600,800,3):raise AssertionError("Expected 800x600 research viewport")
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("scene",type=Path);p.add_argument("output",type=Path)
    p.add_argument("--viewer",type=Path,default=Path(__file__).resolve().parents[1]/"engine/target/debug"/("jade-viewer.exe" if os.name=="nt" else "jade-viewer"))
    a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
    before=capture(a.viewer.resolve(),a.scene.resolve(),out/"off",True)
    after=capture(a.viewer.resolve(),a.scene.resolve(),out/"on",False)
    blurred=reconstruct(q(sample(before,512,512)))[-1]
    predicted=q(composite(before,blurred,104))
    error=np.abs(predicted.astype(int)-after.astype(int))
    result=dict(max_channel_error=int(error.max()),mean_channel_error=float(error.mean()),
                channels_within_one=float(np.mean(error<=1)))
    Image.fromarray(predicted).save(out/"reference.png")
    (out/"comparison.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))
    if error.max()>2:raise AssertionError("GPU output differs from the measured chain")

if __name__=="__main__":main()
