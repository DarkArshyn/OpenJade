"""Read the frozen plante2 corner alphas and its four lower BC3 mip levels."""
import hashlib
import struct
import numpy as np
from PIL import Image
from inspect_menu_palms import HASH, records, static_links, primary_mesh
from menu_primary_geometry import instance_colors


def export_leaf(source, expanded, draw):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASH:
        raise ValueError("Unsupported leaf source")
    payload = {r["key"]: raw[r["offset"]+12:r["end"]] for r in records(raw)}
    obj = payload["0x30000CCF"]
    links = static_links(obj)
    _, _, groups, ids, count, _, _ = primary_mesh(payload[links["mesh"]])
    _, offset = instance_colors(obj, links["link_offset"], count)
    first, corners = draw[:2]
    if groups[0] != (29, 72) or corners != 216 or offset is None:
        raise ValueError("Unexpected leaf geometry")
    colors = np.frombuffer(obj, "u1", 4*count, offset).reshape(-1, 4)[ids[:corners]]
    vertices = np.asarray(expanded[first:first+corners])
    if not np.array_equal(np.rint(vertices[:, 5:8]*255), colors[:, :3]):
        raise ValueError("Leaf corner order mismatch")
    data = payload["0x30000C6A"]
    pos = 56 + 128*64
    levels = bytearray()
    for w, h in [(64,32), (32,16), (16,8), (8,4)]:
        end = pos + w*h
        levels.extend(Image.frombytes("RGBA", (w,h), data[pos:end], "bcn", (3,"DXT5")).tobytes())
        pos = end
    return b"OJLEAF01" + struct.pack("<II", first, int(vertices[0,8])) + colors[:,3].tobytes() + levels


def export_trunk(source, layer, base_rgba):
    """Preserve all six BC1 levels of the verified 0x30000C5C texture."""
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASH:
        raise ValueError("Unsupported trunk source")
    entry = max((r for r in records(raw) if r["key"] == "0x30000C5C"), key=lambda r: r["size"])
    data = raw[entry["offset"]+12:entry["end"]]
    pos = 60
    levels = bytearray()
    for size in (256, 128, 64, 32, 16, 8):
        end = pos + size*size//2
        levels.extend(Image.frombytes("RGBA", (size, size), data[pos:end], "bcn", (1, "DXT1")).tobytes())
        pos = end
    if levels[:256*256*4] != base_rgba:
        raise ValueError("Native trunk base does not match the exported texture")
    return b"OJTRNK01" + struct.pack("<II", layer, 6) + levels
