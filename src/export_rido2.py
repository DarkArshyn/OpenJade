"""Export the bounded rido2 component beside a matching OJSCN005 menu."""
import struct
from pathlib import Path
import numpy as np
from inspect_menu_palms import HASH, hashlib, records, static_links, primary_mesh


def export_rido2(source, vertices, draws, audit, *, instance=2):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASH:
        raise ValueError("Unsupported curtain scene")
    payloads = {row["key"]: raw[row["offset"]+12:row["end"]] for row in records(raw)}
    key, name, pairs, planes = {
        1: ("0x30000CDE", "Menu3D_rido.gao", 2530, 1),
        2: ("0x30000CDF", "Menu3D_rido2.gao", 2531, 1),
        3: ("0x3000FCF8", "Menu3D_rido03.gao", 2432, 0),
        4: ("0x30000D37", "Menu3D_rido4.gao", 2531, 0),
    }[instance]
    obj = payloads[key]
    links = static_links(obj)
    mesh = payloads[links["mesh"]]
    layout = primary_mesh(mesh)[-1]
    rest = np.frombuffer(mesh, "<f4", 75, layout["vertex_offset"]).reshape(25, 3)
    matrix = np.frombuffer(obj, "<f4", 16, links["matrix_offset"]).reshape(4, 4)
    if instance != 2:
        matrix = matrix.copy()
        matrix[:, 3] = (0, 0, 0, 1)
    if struct.unpack_from("<9I", obj, pairs - 500) != (18, 0x1000000, 3, 0, 2, 2, 25, 40, planes):
        raise ValueError("Unsupported curtain component")
    world = rest.astype(float) @ matrix[:3,:3] + matrix[3,:3]
    first, count = [draw[:2] for entry, draw in zip(audit, draws, strict=True)
                    if entry["object"] == name][0]
    coords = np.asarray(vertices[first:first+count])[:,:3]
    distances = np.linalg.norm(coords[:,None]-world, axis=2)
    ids = distances.argmin(axis=1)
    if count != 96 or len(set(ids)) != 25 or distances.min(axis=1).max() > .0001:
        raise ValueError("Curtain corner mapping mismatch")
    wind = obj[pairs-448:pairs-424]
    parameters = obj[pairs+480:pairs+496] if planes else b""
    if instance == 2:
        header = b"OJRIDO01"
    else:
        header = b"OJRIDO05" if planes else b"OJRIDO04"
        parameters += wind
    return (header + struct.pack("<I", first) + matrix.tobytes() + rest.tobytes()
            + obj[pairs-400:pairs+480] + parameters + ids.astype("u1").tobytes())

