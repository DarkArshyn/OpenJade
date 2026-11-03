"""GPU check of masked additive chain followed by the current-frame blur."""
import argparse,json,os
from pathlib import Path
import numpy as np
from PIL import Image
from integration_menu_blur import capture,sample,q,reconstruct,composite
from reconstruct_menu_additive import reconstruct as pyramid, composite as add
p=argparse.ArgumentParser(description=__doc__)
p.add_argument("scene",type=Path);p.add_argument("output",type=Path)
a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
viewer=Path(__file__).resolve().parents[1]/"engine/target/debug/jade-viewer.exe"
before=capture(viewer,a.scene.resolve(),out/"off",True)
os.environ["OPENJADE_CAPTURE_GLOW_MASK"]="1"
try: mask=capture(viewer,a.scene.resolve(),out/"mask",True)
finally: os.environ.pop("OPENJADE_CAPTURE_GLOW_MASK",None)
after=capture(viewer,a.scene.resolve(),out/"on",False,True)
assert mask.max()>0,"No visible glow mask"
rgba=np.concatenate([before,mask[:,:,:1]],axis=2)
source=q(sample(rgba,512,512))
added=add(before,pyramid(source))
predicted=q(composite(added,reconstruct(source[:,:,:3])[-1],104))
error=abs(predicted.astype(int)-after.astype(int))
result=dict(max_channel_error=int(error.max()),mean_channel_error=float(error.mean()),mask_pixels=int(np.count_nonzero(mask[:,:,0])))
Image.fromarray(predicted).save(out/"reference.png")
Image.fromarray(after).save(out/"vulkan.png")
(out/"comparison.json").write_text(json.dumps(result,indent=2))
print(result)
assert error.max()<=2
