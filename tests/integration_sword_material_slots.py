"""Match source face-group slots to original-game selected material identities."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from prince_resources import Resources, material_slot

def verify(capture,manifest):
    r=Resources([Path(x["path"]) for x in json.loads(manifest.read_text(encoding="utf-8"))["sources"]])
    component=r.component(0x057CC7FF)
    path=capture/f"{capture.name}-selection.txt"
    lines=path.read_text().splitlines()
    assert len(lines)==3
    result=[]
    for group,line in zip(component["geometry"]["groups"],lines):
        words=line.split()
        assert words[0::2]==["mesh","triangles","index","selected"]
        assert int(words[1],16)==int(component["mesh"],16)
        assert int(words[3])==group["count"] and int(words[5])==group["slot"]
        resolved=material_slot(component["materials"],group["slot"])
        selected=component["materials"][resolved]
        assert selected==int(words[7],16)
        result.append(dict(triangles=group["count"],requested=group["slot"],resolved=resolved,material=f"{selected:08X}"))
    return dict(groups=result,selection_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                sources=r.sources,resources=r.used)

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture",type=Path);parser.add_argument("manifest",type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.capture,args.manifest),indent=2))
