"""Export the observed menu3D ground as a hypothesis-labelled OBJ and SVG.

This fixed-sample research tool is not a general mesh decoder. It never applies
an inferred material, UV mapping, world transform or camera projection.
"""
import argparse
import hashlib
import json
import math
import struct
from pathlib import Path
from probe_menu3d import records

EXPECTED='96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'


def ground(payload):
    if len(payload)!=280:raise ValueError('Expected the observed 280-byte record')
    if struct.unpack_from('<II',payload,176)!=(4,20):raise ValueError('Vertex count/stride mismatch')
    vertices=[struct.unpack_from('<3f',payload,44+12*i) for i in range(4)]
    repeated=[struct.unpack_from('<3f',payload,184+20*i) for i in range(4)]
    if vertices!=repeated or not all(math.isfinite(x) for v in vertices for x in v):raise ValueError('Coordinate arrays mismatch')
    if struct.unpack_from('<I',payload,264)[0]!=12:raise ValueError('Index byte count mismatch')
    indices=struct.unpack_from('<6H',payload,268)
    if any(i>=4 for i in indices):raise ValueError('Out-of-range index')
    triangles=[indices[:3],indices[3:]]
    areas=[]
    for tri in triangles:
        a,b,c=[vertices[i] for i in tri]
        area=((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]))/2
        if abs(area)<1e-6:raise ValueError('Degenerate XY triangle')
        areas.append(area)
    if areas[0]*areas[1]<=0:raise ValueError('Inconsistent winding')
    if len(set(triangles[0])&set(triangles[1]))!=2:raise ValueError('Expected shared edge')
    xs=[v[0] for v in vertices];ys=[v[1] for v in vertices]
    rectangle=(max(xs)-min(xs))*(max(ys)-min(ys))
    if not math.isclose(sum(abs(a) for a in areas),rectangle,rel_tol=1e-6):raise ValueError('Area mismatch')
    return dict(vertices=vertices,triangles=triangles,signed_xy_areas=areas,rectangle_xy_area=rectangle,
                unknown_vertex_words=[payload[196+20*i:204+20*i].hex() for i in range(4)])


def export(source,out):
    data=source.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if digest!=EXPECTED:raise ValueError('This probe is limited to the verified menu3D sample')
    by={r['key']:r for r in records(data)}
    r=by['0x30000C80'];result=ground(data[r['offset']+12:r['end']])
    result.update(source_sha256=digest,record_key=r['key'],record_offset=r['offset'],
                  interpretation='Candidate triangle list, validated on one record only; no material or UV interpretation')
    out.mkdir(parents=True,exist_ok=False)
    (out/'ground.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    lines=['# OpenJade research hypothesis: local-space ground, untextured',
           '# Two candidate triangles; no verified world transform or material']
    lines+=['v '+' '.join(format(x,'.9g') for x in v) for v in result['vertices']]
    lines+=['f '+' '.join(str(i+1) for i in t) for t in result['triangles']]
    (out/'ground-candidate.obj').write_text('\n'.join(lines)+'\n',encoding='ascii')
    verts=result['vertices'];xmin=min(v[0] for v in verts);ymin=min(v[1] for v in verts)
    scale=420/max(max(v[0] for v in verts)-xmin,max(v[1] for v in verts)-ymin)
    points=[(100+(v[0]-xmin)*scale,540-(v[1]-ymin)*scale) for v in verts]
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="760" height="650" viewBox="0 0 760 650">',
         '<rect width="760" height="650" fill="#181c24"/>',
         '<g font-family="sans-serif" fill="#e8dcc1">',
         '<text x="35" y="40" font-size="22">Menu3D ground - candidate topology</text>',
         '<text x="35" y="70" font-size="15">Local XY projection; no texture, camera or world transform</text>']
    for tri,color in zip(result['triangles'],['#315870','#58713d']):
        coords=' '.join(f'{points[i][0]:.3f},{points[i][1]:.3f}' for i in tri)
        svg.append(f'<polygon points="{coords}" fill="{color}" stroke="#e8dcc1" stroke-width="2"/>')
    for i,(x,y) in enumerate(points):
        svg.append(f'<circle cx="{x}" cy="{y}" r="4"/><text x="{x+9}" y="{y-9}">{i}</text>')
    svg+=['<text x="35" y="590">Triangles: (2, 0, 3) and (1, 3, 0)</text>',
          '<text x="35" y="620">One-sample hypothesis - not the rendered game scene</text></g></svg>']
    (out/'ground-preview.svg').write_text('\n'.join(svg),encoding='utf8')
    print(out)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();export(a.source,a.output)
