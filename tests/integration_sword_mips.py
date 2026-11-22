"""Compare every captured sword texture level with original resource pixels."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from prince_resources import Resources


def verify(capture, manifest):
    resources=Resources([Path(x["path"]) for x in json.loads(manifest.read_text(encoding="utf-8"))["sources"]])
    metadata=(capture/f"{capture.name}-draw-000.txt").read_text()
    result=[]
    for stage,key in [(0,0x13006B64),(1,0x2E011834)]:
        levels,info=resources.texture(key)
        for level,image in enumerate(levels):
            width=max(1,info["sizes"][0][0]>>level)
            height=max(1,info["sizes"][0][1]>>level)
            assert f"mip {stage} {level} {width} {height} 21 00000000 00000000 00000000" in metadata
            path=capture/f"mask-00-000-{capture.name}-stage{stage}-level{level}.bgra"
            raw=path.read_bytes()
            native=np.frombuffer(raw,np.uint8).reshape(height,width,4)[:,:,[2,1,0,3]]
            expected=image[:height,:width]
            assert np.array_equal(native,expected),(stage,level)
            result.append(dict(resource=f"{key:08X}",level=level,stored_size=info["sizes"][level],
                               gpu_size=[width,height],exact=True,readback_sha256=hashlib.sha256(raw).hexdigest()))
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture",type=Path);parser.add_argument("manifest",type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.capture,args.manifest),indent=2))
