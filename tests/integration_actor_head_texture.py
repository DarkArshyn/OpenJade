"""Compare original face pixels and scene bytes against the GOG diagnostic."""
import argparse
from pathlib import Path
import sys
import tempfile
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from actor_head_texture import load_head_texture
from export_actor_head_preview import export
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path);p.add_argument('capture',type=Path);p.add_argument('baseline',type=Path)
a=p.parse_args()
levels,info=load_head_texture(a.source)
gpu=np.fromfile(a.capture/'mask-00-000-actor-head2-texture.bgra',np.uint8).reshape(512,512,4)[:,:,[2,1,0,3]]
assert np.array_equal(levels[0],gpu)
assert [x.shape for x in levels]==[(512>>i,512>>i,4) for i in range(7)]
with tempfile.TemporaryDirectory() as tmp:
    out=Path(tmp)/'scene'
    export(a.capture,out,a.source)
    assert (out/'head.ojscene').read_bytes()==a.baseline.read_bytes()
print('PASS: exact RGBA match; seven mip levels; byte-identical scene')
