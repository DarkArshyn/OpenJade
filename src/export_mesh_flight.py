"""Decode the closed bird waypoint lists, weighted wing mesh and compact GAO modifiers."""
import hashlib
import struct

import numpy as np

from assemble_menu_scene import texture_image
from inspect_menu_palms import HASH, records, static_links
from menu_primary_geometry import primary_mesh


def export_mesh_flight(source):
    raw=source.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH:
        raise ValueError("Unsupported flight source")
    by={}
    for record in records(raw):
        by.setdefault(int(record["key"],16),[]).append(record)
    def payload(key):
        record,=by[key]
        return raw[record["offset"]+12:record["end"]]
    def u32(data,offset):
        return struct.unpack_from("<I",data,offset)[0]

    geometry=payload(0x30000F2E)
    vertices,_,groups,indices,count,_,layout=primary_mesh(geometry)
    if groups!=[(0,22)] or count!=18 or layout["vertex_offset"]!=44:
        raise ValueError("Unexpected flight mesh")
    normals=u32(geometry,40)
    color_start=44+count*12*(1+normals)
    weights=np.frombuffer(geometry,"u1",count*4,color_start).reshape(count,4)[indices,3]
    mat=payload(0x30000D90)
    if len(mat)!=48 or u32(mat,44)!=0x30000C67:
        raise ValueError("Unexpected flight material")
    images=[]
    for rec in by[0x30000C67]:
        try: images.append(texture_image(raw[rec["offset"]+12:rec["end"]]))
        except (ValueError,struct.error):continue
    if len(images)!=1 or images[0].size!=(32,32):
        raise ValueError("Expected one flight texture")
    result=bytearray(b"OJFLT001"+mat[8:12]+images[0].convert("RGBA").tobytes())
    for vertex,weight in zip(vertices,weights,strict=True):
        result.extend(struct.pack("<6f",*vertex,float(weight)/256))

    for key in (0x30000F2D,0x30000F38,0x30000F44):
        obj=payload(key)
        link=static_links(obj)
        if link["mesh"]!="0x30000F2E" or link["material_pack"]!="0x30000D90":
            raise ValueError("Flight mesh binding mismatch")
        scales=[struct.unpack_from("<f",obj,link["matrix_offset"]+i)[0] for i in (12,28,44)]
        kind,header,version,flags,phase,amplitude,spatial,rate,group,end=struct.unpack_from("<4I4f2I",obj,len(obj)-40)
        if (kind,header,version,flags,group,end)!=(1,0,25,28,0xffffffff,0xffffffff) or len(set(scales))!=1:
            raise ValueError("Unsupported wing modifier or scale")
        model,params=struct.unpack("<2I",payload(u32(obj,len(obj)-44)))
        settings=payload(params)
        if model!=0x010000A6 or len(settings)!=116:
            raise ValueError("Unsupported flight behavior")
        path,speed,turn=struct.unpack_from("<Iff",settings,84)
        node,one=struct.unpack("<2I",payload(path))
        first=node
        result.extend(struct.pack("<7f",speed,turn,scales[0],phase,amplitude,spatial,rate))
        visited=set()
        for _ in range(3):
            if node in visited or one!=1:raise ValueError("Invalid flight route")
            visited.add(node)
            obj=payload(node)
            matrix=u32(obj,16)+30
            if obj[:4]!=b".gao" or u32(obj,matrix+64)!=2:
                raise ValueError("Expected waypoint box")
            center=struct.unpack_from("<3f",obj,matrix+48)
            bounds=struct.unpack_from("<6f",obj,matrix+68)
            result.extend(struct.pack("<9f",*center,*bounds))
            links=payload(u32(obj,len(obj)-4))
            if len(links)!=21 or u32(links,4)!=path:raise ValueError("Invalid waypoint link")
            node=u32(links,14)
        if node!=first:raise ValueError("Flight route did not close")
    assert len(result)==6100
    return bytes(result)
