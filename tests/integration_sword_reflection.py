"""Validate native sword reflection resources and sampled UV constants."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from prince_resources import Resources


def verify(capture, manifest, camera=None):
    prefix = capture.name
    resources = Resources([Path(item["path"]) for item in
                           json.loads(manifest.read_text(encoding="utf-8"))["sources"]])
    material = resources.get(0x13006BBB)
    assert struct.unpack_from("<I", material, 44)[0] == 0x13006B64
    assert struct.unpack_from("<I", material, 68)[0] == 0x2E011834
    packed=struct.unpack_from("<I",material,8)[0]
    tint=np.array([(packed>>shift&255)/255 for shift in (0,8,16)])
    constants=np.fromfile(capture / f"{prefix}-draw-000.pixelconstants","<f4").reshape(8,4)
    assert np.allclose(tint,constants[0,:3],atol=1e-7,rtol=0)
    levels, _ = resources.texture(0x2E011834)
    raw = (capture / f"mask-00-000-{prefix}-stage1.bgra").read_bytes()
    rgba = np.frombuffer(raw, np.uint8).reshape(32, 32, 4)[:, :, [2, 1, 0, 3]]
    assert np.array_equal(rgba, levels[0])
    meta = (capture / f"{prefix}-draw-000.txt").read_text()
    assert "texcopy 1 00000000 00000000" in meta
    for state, value in [(1, 3), (2, 3), (5, 2), (6, 2), (7, 0)]:
        assert f"sampler 1 {state} {value} hr 00000000" in meta
    data = (capture / f"{prefix}-draws.bin").read_bytes()
    stride = 20 + 256 * 16
    assert len(data) % stride == 0
    samples = {}
    for offset in range(0, len(data), stride):
        frame, owner, triangles, indexed, ambient = struct.unpack_from("<5I", data, offset)
        if triangles != 61:
            continue
        c = np.frombuffer(data, "<f4", 1024, offset + 20).reshape(256, 4).astype(float)
        expected = np.column_stack((-.5 * c[4:6, :3], np.full(2, .5)))
        error = float(np.max(np.abs(c[17:19] - expected)))
        samples.setdefault(frame, []).append(error)
    assert sorted(samples) == list(range(0, 121, 12))
    # The first draw is the visible pass; the following offscreen pass retains
    # reflection constants while changing its position matrix.
    assert all(len(errors) == 2 and errors[0] == 0 for errors in samples.values())
    groups = []
    for number, triangles in [(1,8),(2,24)]:
        path = capture / f"{prefix}-draw-{number:03}.txt"
        lines = path.read_text().splitlines()
        assert int(lines[0].split()[3]) == triangles
        assert not path.with_suffix(".ps").exists()
        assert next(x for x in lines if x.startswith("texture 0 ")).split()[2] == next(x for x in meta.splitlines() if x.startswith("texture 0 ")).split()[2]
        for line in ["texture 1 00000000","tss 0 1 5","tss 0 3 0","state 7 1","state 14 1","state 27 0"]:
            assert line in lines
        groups.append({"triangles":triangles,"texture":"13006B64","mode":"texture times diffuse times two"})
    transition = None
    if camera is not None:
        raw = (camera / f"{camera.name}-draws.bin").read_bytes()
        assert len(raw) % stride == 0
        pairs = {}
        for offset in range(0,len(raw),stride):
            frame,owner,count,indexed,ambient=struct.unpack_from("<5I",raw,offset)
            if count != 61: continue
            constants=np.frombuffer(raw,"<f4",1024,offset+20).reshape(256,4).astype(float)
            pairs.setdefault(frame,[]).append(constants)
        assert len(pairs)==275 and all(len(value)==2 for value in pairs.values())
        matrices=[]
        for pair in pairs.values():
            constants=pair[0]
            expected=np.column_stack((-.5*constants[4:6,:3],np.full(2,.5)))
            assert np.array_equal(constants[17:19],expected)
            matrices.append(constants[17:19,:3])
        variation=float(np.ptp(matrices,axis=0).max())
        assert variation>0.01
        transition={"poses":len(pairs),"max_constant_error":0.0,"maximum_coefficient_span":variation,
                    "draws_sha256":hashlib.sha256(raw).hexdigest()}
    return {"secondary_groups":groups,"camera02":transition,"frames": len(samples), "visible_uv_constant_max_error": 0.0,
            "reflection_texture": "2E011834", "dimensions": [32, 32],
            "texture_exact": True, "capture_sha256": hashlib.sha256(data).hexdigest(),
            "scope": "Native constants and material states; not final-pixel parity"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--camera", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.capture, args.manifest, args.camera), indent=2))
