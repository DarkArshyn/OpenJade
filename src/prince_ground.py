"""Focused balcony collision query, independently matched to native contacts.

Only the measured 30000D19 layout is supported; this is not a general collision engine.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from prince_resources import Resources
from prince_animation import node

def inspect(resources):
    checkpoint = node(resources, 0x0F0053D9)[0]
    obj = resources.get(0x30000CD9)
    if len(obj) < 24 or obj[:4] != b'.gao':
        raise ValueError('Invalid collision owner')
    if struct.unpack_from('<I', obj, len(obj)-4)[0] != 0x30000D18:
        raise ValueError('Unexpected balcony collision reference')
    ref = resources.get(0x30000D18)
    if ref != struct.pack('<2I', 0xff01, 0x30000D19):
        raise ValueError('Unexpected collision indirection')
    data = resources.get(0x30000D19)
    if len(data) != 4614 or data[:6] != bytes.fromhex('280200cc0509'):
        raise ValueError('Unsupported balcony collision layout')
    nv = struct.unpack_from('<I', data, 6)[0]
    if nv != 84:
        raise ValueError('Unexpected vertex count')
    vertices = np.frombuffer(data, '<f4', nv*3, 10).reshape(-1, 3).astype(float)
    at = 10 + nv*12
    nf = struct.unpack_from('<I', data, at)[0]
    if nf != 130:
        raise ValueError('Unexpected normal count')
    normals = np.frombuffer(data, '<f4', nf*3, at+4).reshape(-1, 3)
    at += 4 + nf*12
    if struct.unpack_from('<3I', data, at) != (1, nf, 368):
        raise ValueError('Unsupported face section')
    faces = np.frombuffer(data, '<u2', nf*3, at+12).reshape(-1, 3)
    if faces.max() >= nv or not np.isfinite(vertices).all() or not np.isfinite(normals).all():
        raise ValueError('Invalid collision geometry')
    name_length = struct.unpack_from('<I', obj, 16)[0]
    if name_length > len(obj)-94:
        raise ValueError('Truncated collision owner transform')
    if obj[20:20+name_length].rstrip(b'\0') != b'Menu3D_FarahRoom_Balcony.gao':
        raise ValueError('Unexpected owner')
    # Only the affine XYZ lanes are interpreted; the remaining serialized lanes are not decoded.
    stored = np.frombuffer(obj, '<f4', 16, name_length+30).reshape(4, 4)
    if not np.isfinite(stored[:, :3]).all() or not np.array_equal(stored[:3, :3], np.eye(3)):
        raise ValueError('Unsupported collision owner basis')
    if not np.isfinite(checkpoint).all():
        raise ValueError('Nonfinite checkpoint')
    world = vertices @ stored[:3, :3] + stored[3, :3]
    hits = []
    for index, ids in enumerate(faces):
        tri = world[ids]
        matrix = (tri[1:, :2] - tri[0, :2]).T
        if abs(np.linalg.det(matrix)) < 1e-10:
            continue
        uv = np.linalg.solve(matrix, checkpoint[3, :2]-tri[0, :2])
        weights = np.r_[1-sum(uv), uv]
        if min(weights) >= -1e-6:
            hits.append(dict(triangle=index, indices=ids.tolist(), point=[*checkpoint[3,:2].tolist(),float(weights @ tri[:,2])], normal=normals[index].tolist()))
    return dict(owner='30000CD9', reference='30000D18', geometry='30000D19', vertices=nv,
                triangles=nf, hits=hits, checkpoint_z=float(checkpoint[3,2]),
                geometry_sha256=hashlib.sha256(data).hexdigest(),
                unparsed_tail_bytes=len(data)-(at+12+nf*6),
                scope='Selected geometry and vertical intersection only; trailing collision data and general grounding remain unimplemented.')


def grounded_placement(resources):
    """Resolve the unique measured support surface for the static menu spawn."""
    report = inspect(resources)
    placement = node(resources, 0x0F0053D9)[0].copy()
    if len(report['hits']) != 1:
        raise ValueError('Menu grounding requires exactly one collision intersection')
    hit = report['hits'][0]
    if not np.allclose(hit['normal'], [0., 0., 1.], atol=1e-6, rtol=0):
        raise ValueError('Menu grounding requires the measured upward support plane')
    if not np.isfinite(hit['point']).all() or hit['point'][2] > placement[3, 2]:
        raise ValueError('Collision intersection is not below the checkpoint')
    placement[3, 2] = hit['point'][2]
    report['placement_z'] = float(placement[3, 2])
    report['checkpoint_delta_z'] = float(placement[3, 2] - report['checkpoint_z'])
    return placement, report

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path); parser.add_argument('output',type=Path)
    args=parser.parse_args()
    if args.output.exists():raise FileExistsError(args.output)
    report=inspect(Resources([args.source]))
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
