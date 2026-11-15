"""Measure vertical intersections against rendered triangles; not collision geometry."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from assemble_prince_balcony import read_scene

def intersections(scene, xy):
    hits = []
    for draw, record in enumerate(scene['draws']):
        first, count = struct.unpack_from('<2I', record)
        for index in range(first, first + count, 3):
            triangle = scene['vertices'][index:index+3, :3].astype(float)
            matrix = (triangle[1:, :2] - triangle[0, :2]).T
            if abs(np.linalg.det(matrix)) < 1e-10:
                continue
            uv = np.linalg.solve(matrix, np.asarray(xy) - triangle[0, :2])
            weights = np.r_[1 - sum(uv), uv]
            if min(weights) >= -1e-6:
                hits.append(dict(draw=draw, vertex=index, z=float(weights @ triangle[:, 2])))
    return hits

def measure(menu, package, capture, output):
    if output.exists():
        raise FileExistsError(output)
    scene = read_scene(menu)
    placement = np.frombuffer((package / 'menu.placement').read_bytes(), '<f4', 16, 12).reshape(4, 4)
    bindings = {int(o, 16): key for o, key, _ in (line.split() for line in
                (capture / (capture.name + '-bindings.txt')).read_text(encoding='utf-8').splitlines())}
    raw = (capture / (capture.name + '-prepared.bin')).read_bytes()
    if len(raw) % 88:
        raise ValueError('Truncated placement capture')
    samples = []
    for at in range(0, len(raw), 88):
        frame, obj = struct.unpack_from('<2I', raw, at)
        if bindings.get(obj) == '13008426':
            matrix = np.frombuffer(raw, '<f4', 16, at+24).reshape(4, 4)
            samples.append(dict(frame=frame, position=matrix[3, :3].tolist()))
    if not samples:
        raise ValueError('No captured body placements')
    origin = placement[3, :3].astype(float)
    heights = [x['position'][2] for x in samples]
    hits = [h for h in intersections(scene, origin[:2]) if abs(h['z'] - origin[2]) < 3]
    report = dict(scene_sha256=hashlib.sha256(scene['raw']).hexdigest(),
                  capture_sha256=hashlib.sha256(raw).hexdigest(), checkpoint=origin.tolist(),
                  native_samples=len(samples), native_z_range=[min(heights), max(heights)],
                  rendered_surface_hits=hits,
                  scope='Rendered geometry intersections only; collision surface, actor support offset and grounding routine remain unverified.')
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('menu', 'package', 'capture', 'output'):
        parser.add_argument(name, type=Path)
    a = parser.parse_args()
    print(json.dumps(measure(a.menu, a.package, a.capture, a.output), indent=2))
