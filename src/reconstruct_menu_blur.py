"""Bounded independent reconstruction of the measured GOG menu blur.

This is a research reference, not the runtime Vulkan postprocess. It reproduces
four observed RGB passes from the current frame's 512x512 scene copy.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image

def sample(tex,w,h,span=1.,offset=(0.,0.)):
    th,tw=tex.shape[:2];x=(np.arange(w)+.5)*span*tw/w-.5+offset[0];y=(np.arange(h)+.5)*span*th/h-.5+offset[1]
    ix=np.floor(x).astype(int);iy=np.floor(y).astype(int);fx=(x-ix)[None,:,None];fy=(y-iy)[:,None,None];a=np.clip(ix,0,tw-1);b=np.clip(ix+1,0,tw-1);c=np.clip(iy,0,th-1);d=np.clip(iy+1,0,th-1);t=tex.astype(float)
    return (t[c[:,None],a]*(1-fx)+t[c[:,None],b]*fx)*(1-fy)+(t[d[:,None],a]*(1-fx)+t[d[:,None],b]*fx)*fy

def q(v):return np.clip(np.rint(v),0,255).astype('uint8')
def reconstruct(current):
    """Reconstruct RGB from one current 512-square capture; no history input.

    Preserve the captured partial-write behavior: A starts as the current image,
    while unused B padding is black. Alpha is not read by the final composite.
    """
    current = np.asarray(current)
    if current.shape != (512,512,3) or current.dtype != np.uint8:
        raise ValueError("Expected a 512x512 RGB8 current-frame image")
    a=q(current*(256/255));states=[a.copy()]
    b=np.zeros_like(a);b[:256,:256]=q(sample(a,256,256)*(256/255));states.append(b.copy())
    a[:128,:128]=q(sum(sample(b,128,128,.5,o)*.333332986 for o in [(-1,-1),(1,0),(0,1)]));states.append(a.copy())
    b[:256,:256]=q(sum(sample(a,256,256,.25,o)*.333332986 for o in [(-1,-1),(1,0),(0,1)]));states.append(b.copy())
    return states


def read_bgra(path, width=512, height=512):
    data = Path(path).read_bytes()
    if len(data) != width*height*4:
        raise ValueError("Unexpected captured surface extent")
    return np.frombuffer(data,"u1").reshape(height,width,4)[:,:,[2,1,0]]


def validate(folder, output):
    """Validate the bounded three-frame trace, including same-frame links."""
    output.mkdir(parents=True,exist_ok=False)
    report=[]
    for frame in (20,21,22):
        def load(pass_id,kind,width=512,height=512):
            return read_bgra(folder/f"chain-{frame}-{pass_id:03}-{kind}.bgra",width,height)
        source=load(24,"after")
        states=reconstruct(source)
        comparisons=[]
        for pass_id,predicted in zip(range(44,48),states):
            expected=load(pass_id,"after")
            size={44:512,45:256,46:128,47:256}[pass_id]
            error=np.abs(predicted[:size,:size].astype(int)-expected[:size,:size].astype(int))
            comparisons.append(dict(pass_id=pass_id,written_size=size,
                max_error=int(error.max()),mean_error=float(error.mean()),
                within_one=float(np.mean(error<=1))))
        links=[dict(source=a,destination=b,equal=bool(np.array_equal(load(a,"after"),load(b,"tex0"))))
               for a,b in ((24,44),(44,45),(45,46),(46,47),(47,48))]
        padding=load(46,"tex0").copy();padding[:256,:256]=0
        copied=q(sample(load(24,"source",800,600),512,512))
        copy_error=np.abs(copied.astype(int)-source.astype(int))
        report.append(dict(frame=frame,passes=comparisons,same_frame_links=links,
            unused_padding_is_black=bool(np.all(padding==0)),copy_linear_max_error=int(copy_error.max())))
        Image.fromarray(states[-1][:256,:256]).save(output/f"frame-{frame}-reconstructed.png")
    (output/"validation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))

if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_directory",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    validate(args.capture_directory,args.output)
