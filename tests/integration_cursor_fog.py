"""Check local GOG cursor and dynamic-fog captures against extracted resources."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from assemble_menu_scene import texture_image
from inspect_menu_scene_links import static_links
from probe_menu3d import records

SOURCE_HASH = "96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb"
CURSORS = ("officialcursor_alpha2_desaturated.dds", "test.dds")


def rgb(path):
    raw = path.read_bytes()
    if len(raw) != 800 * 600 * 4:
        raise ValueError("Expected an 800x600 BGRA readback")
    return np.frombuffer(raw, np.uint8).reshape(600, 800, 4)[:, :, 2::-1].astype(np.int16)


def compare(directory, source, textures):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_HASH:
        raise ValueError("Unsupported frozen menu")
    payloads = {r["key"]: raw[r["offset"] + 12:r["end"]] for r in records(raw)}
    origins = {}
    for key in ("0x30000D26", "0x30000D28"):
        obj = payloads[key]
        links = static_links(obj)
        assert links["mesh"] == "0x30000D27"
        assert links["material_pack"] == "0x2E0051F1"
        origins[links["name"]] = struct.unpack_from("<3f", obj, links["matrix_offset"] + 48)
    assert struct.unpack_from("<I", payloads["0x2E0051F1"], 44)[0] == 0x2E004FE4
    fog = np.array(texture_image(payloads["0x2E004FE4"]))
    refs = {n: np.array(Image.open(textures / n).convert("RGBA")) for n in CURSORS}
    results = []
    for f in sorted(directory.glob("cursor-fog-normal-*.txt")):
        if not f.with_suffix(".dds").exists():
            continue
        lines = [line.split() for line in f.read_text().splitlines()]
        states = {int(l[1]): int(l[2]) for l in lines if l[0] == "rs"}
        stages = {int(l[1]): int(l[2]) for l in lines if l[0] == "tss"}
        pixels = np.array(Image.open(f.with_suffix(".dds")).convert("RGBA"))
        matrix = next((list(map(float, l[1:])) for l in lines if l[0] == "matrix"), None)
        name = None
        if matrix:
            name = next((n for n, origin in origins.items() if np.max(np.abs(np.array(matrix[12:15]) - origin)) < 1e-4), None)
            if name:
                assert np.array_equal(pixels, fog), "Bound fog texture differs"
        else:
            name = next((n for n, ref in refs.items() if np.array_equal(pixels, ref)), None)
        if name is None:
            continue
        assert all(states[k] == v for k, v in {27: 1, 19: 5, 20: 6, 14: 0, 15: 0, 168: 7, 171: 1}.items())
        assert stages == {1: 5, 2: 2, 3: 0, 4: 4, 5: 2, 6: 0}
        assert states[7] == states[28] == (1 if matrix else 0)
        before = rgb(f.with_name(f.stem + "-before.bgra"))
        after = rgb(f.with_name(f.stem + "-after.bgra"))
        delta = after - before
        mask = np.any(delta != 0, axis=2)
        y, x = np.where(mask)
        row = dict(capture=f.stem, name=name, triangles=int(lines[0][1]), pixels=int(mask.sum()), max_abs=int(np.abs(delta).max()), rgb_min=delta.min(axis=(0, 1)).tolist(), rgb_max=delta.max(axis=(0, 1)).tolist(), bounds=[int(x.min()), int(y.min()), int(x.max()), int(y.max())] if len(x) else None)
        if matrix:
            row["origin"] = matrix[12:15]
        else:
            vertices = list(struct.iter_unpack("<4fI2f", f.with_suffix(".vb").read_bytes()))
            assert len(vertices) == 4 and all(v[4] == vertices[0][4] for v in vertices)
            row["diffuse_argb"] = f"{vertices[0][4]:08x}"
            assert (vertices[0][4] & 0xffffff) == 0x7f7f7f
            if name == "test.dds":
                frame = f.stem.split("-")[-2]
                final = rgb(directory / f"cursor-fog-normal-{frame}-999-final.bgra")
                assert np.array_equal(final[mask], after[mask]), "Cursor contribution changes after its final pass"
        results.append(row)
    assert len(results) == 12, "Expected two cursor passes and two fog emitters in each of three frames"
    assert all(sum(r["name"] == n for r in results) == 3 for n in [*CURSORS, *origins])
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("captures", type=Path)
    parser.add_argument("menu", type=Path)
    parser.add_argument("textures", type=Path)
    args = parser.parse_args()
    print(json.dumps(compare(args.captures, args.menu, args.textures), indent=2))
