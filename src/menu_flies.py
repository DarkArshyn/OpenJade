"""Decode the two fixed-menu fly meshes and their measured scrolling material."""
import hashlib
import struct

import numpy as np
from PIL import Image

from assemble_menu_scene import material_keys, texture_image
from inspect_menu_palms import HASH, records, static_links
from menu_fog_state import transform_fog_points
from menu_primary_geometry import primary_mesh


def append_flies(source, image_directory, materials, accepted, groups):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != HASH:
        raise ValueError("Unsupported fly source")
    rows = records(raw)

    def payload(key):
        matches = [r for r in rows if r["key"] == key]
        if len(matches) != 1:
            raise ValueError("Ambiguous fly record " + key)
        row = matches[0]
        return raw[row["offset"]+12:row["end"]]

    slot, = [i for i, m in materials.items() if m["key"] == "0x2E005242"]
    mat = payload("0x2E005242")
    flags, u, v, _, texture = struct.unpack_from("<5I", mat, 28)
    if flags != 0xC0014207 or texture != 0x2E005240:
        raise ValueError("Unsupported fly material")
    def unpack(word):
        return struct.unpack("<f", struct.pack("<I", word & 0xffffffff))[0]
    scales = [unpack(word & 0xfffe0000) for word in (u,v)]
    rates = [unpack(word << 16)*scale for word,scale in zip((u,v),scales)]
    image_record, = [r for r in rows if r["key"] == "0x2E005240" and r["size"] > 56]
    image = texture_image(raw[image_record["offset"]+12:image_record["end"]]).convert("RGBA")
    with Image.open(image_directory/f"material-{slot}.png") as existing:
        if existing.size != image.size or existing.convert("RGBA").tobytes() != image.tobytes():
            raise ValueError("Prepared fly texture differs from native image")
    vertices, triangles, mesh_groups, *_ = primary_mesh(payload("0x30000F50"))
    if mesh_groups != [(0,54)]:
        raise ValueError("Unexpected fly geometry")
    for key in ("0x30000F4F","0x30000F52"):
        obj = payload(key)
        link = static_links(obj)
        if link["mesh"] != "0x30000F50" or material_keys(payload(link["material_pack"]))[0] != 0x2E005242:
            raise ValueError("Unexpected fly binding")
        name = link["name"]
        if name in accepted:
            raise ValueError("Duplicate fly geometry")
        matrix = np.array(struct.unpack_from("<16f",obj,link["matrix_offset"])).reshape(4,4)
        world = transform_fog_points(vertices[:,:3],matrix)
        expanded = [[*world[i],*vertices[i,3:5],1.,1.,1.] for i in triangles.ravel()]
        groups.append(dict(name=name,slot=slot,vertices=expanded))
        accepted[name] = dict(key=key,triangles=54,fog_states=[],fly_uv=(scales,rates),
                              color_groups=[dict(material="0x2E005242",**materials[slot]["color_state"])])
