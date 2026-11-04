"""Compare exported vegetation controls with local GOG vertex-buffer captures."""
import argparse
import json
import struct
from pathlib import Path

import numpy as np

OBJECTS=("Menu3D_Plante3.gao","Menu3D_plante1.gao","Menu3D_plante2.gao","Menu3D_liane.gao")
CONTROL=np.dtype([("index","<u4"),("quarter","<u4"),("values","<f4",(9,))])


def scene_data(path):
    raw=path.read_bytes()
    if raw[:8]!=b"OJSCN005":
        raise ValueError("Expected an animated scene")
    n,w,h,l=struct.unpack_from("<4I",raw,8)
    vertices=np.frombuffer(raw,"<f4",n*9,76).reshape(n,9)
    camera=np.frombuffer(raw,"<f4",12,24)
    table=76+n*36+w*h*l*4
    count,=struct.unpack_from("<I",raw,table)
    audit=json.loads(path.with_name("manifest.json").read_text())["draws"]
    assert count==len(audit)
    groups={}
    for i,row in enumerate(audit):
        if row["object"] in OBJECTS:
            first,size=struct.unpack_from("<2I",raw,table+4+48*i)
            groups[OBJECTS.index(row["object"]),size]=first
    ncontrols,=struct.unpack_from("<I",raw,len(raw)-4)
    controls=np.frombuffer(raw[-4-44*ncontrols:-4],CONTROL)
    return camera,vertices,groups,controls


def compare(scene,directory):
    camera,vertices,groups,controls=scene_data(scene)
    view=camera[3:].reshape(3,3).copy()
    view[1]*=-1
    clock=np.fromfile(directory/"plant-motion-clock.bin","<f4")
    raw=(directory/"plant-motion-vb.bin").read_bytes()
    table=np.sin(np.arange(1024)*float(np.float32(2*np.pi/1024))).astype("f")
    offset=0
    results={name:dict(corners=0,max_world_error=0.) for name in OBJECTS}
    while offset<len(raw):
        frame,key,triangles,indexed,count,stride=struct.unpack_from("<6I",raw,offset)
        assert not indexed and triangles*3==count and stride==36
        model_view=np.frombuffer(raw,"<f4",16,offset+24).reshape(4,4)
        local=np.frombuffer(raw,"<f4",count*9,offset+88).reshape(count,9)
        offset+=88+count*36
        first=groups[key,count]
        assert np.array_equal(local[:,7:9],vertices[first:first+count,3:5])
        sel=controls[(controls["index"]>=first)&(controls["index"]<first+count)]
        assert np.array_equal(sel["index"],np.arange(first,first+count))
        params=sel["values"]
        phase=np.zeros(count,dtype="f")
        for dt in clock[:frame+1]:
            phase=(phase+params[:,2]*30*dt)%np.float32(2*np.pi)
        idx=np.rint((params[:,:2]+phase[:,None]).astype(float)*float(np.float32(1024/(2*np.pi)))).astype(int)
        idx[:,1]+=sel["quarter"].astype(int)*256
        sine=table[idx%1024]
        expected=vertices[first:first+count,:3]+params[:,3:6]*sine[:,0,None]+params[:,6:]*sine[:,1,None]
        actual=(local[:,:3]@model_view[:3,:3].T+model_view[:3,3])@view+camera[:3]
        row=results[OBJECTS[key]]
        row["corners"]+=count
        row["max_world_error"]=max(row["max_world_error"],float(np.max(np.abs(actual-expected))))
    assert all(r["corners"] and r["max_world_error"]<0.00005 for r in results.values()),results
    return results


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene",type=Path)
    parser.add_argument("capture_directory",type=Path)
    args=parser.parse_args()
    print(json.dumps(compare(args.scene,args.capture_directory),indent=2))
