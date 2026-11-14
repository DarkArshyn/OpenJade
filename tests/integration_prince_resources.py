"""Differentially validate original Prince geometry against native GPU input buffers."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import sys
import tempfile
import shutil
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from prince_resources import Resources, COMPONENTS
from export_prince_preview import capture_draws, export


def triangle_set(corners):
    # Ignore triangle order and cyclic starting corner, but preserve winding.
    result=[]
    for tri in corners.reshape(-1,3,corners.shape[1]):
        rows=[tuple(v) for v in tri]
        result.append(min(tuple(rows[i:]+rows[:i]) for i in range(3)))
    return Counter(result)


def verify(sources,capture):
    r=Resources(sources);cs={c['mesh'][2:]:c for c in (r.component(k) for k in COMPONENTS)}
    pending={key:list(c['geometry']['groups']) for key,c in cs.items()};results=[]
    for row in capture_draws(capture):
        mesh=cs[row['mesh']]['geometry'];group=pending[row['mesh']].pop(0)
        assert group['count']==row['count']
        path=row['path'];lines=path.read_text().splitlines();h=lines[0].split()
        stream=next(l.split() for l in lines if l.startswith('stream 0 '))
        offset,stride=int(stream[3]),int(stream[5]);raw=path.with_suffix('.stream0').read_bytes()
        ids=np.fromfile(path.with_suffix('.indices'),'<u2')[int(h[5]):int(h[5])+int(h[3])*3].astype(int)+int(h[7])
        native=[];weight_error=0.;normal_error=0.
        for i in ids:
            at=offset+int(i)*stride;pos=np.array(struct.unpack_from('<3f',raw,at));normal=np.array(struct.unpack_from('<3f',raw,at+12))
            matches=np.flatnonzero(np.all(mesh['position']==pos,axis=1));assert len(matches)
            nerrors=np.max(abs(mesh['normals'][matches]-normal),axis=1);j=int(matches[nerrors.argmin()]);normal_error=max(normal_error,float(nerrors.min()))
            uv=struct.unpack_from('<2f',raw,at+(44 if stride==52 else 24));native.append([*pos,*normal,*uv])
            if stride==52:
                indices=np.array(struct.unpack_from('<4h',raw,at+24))[:3]//3;w=struct.unpack_from('<3f',raw,at+32)
                weights=np.zeros(len(mesh['bones']))
                for k,value in zip(indices,w):weights[k]+=value
                weight_error=max(weight_error,float(np.max(abs(weights-mesh['weights'][j]))))
        face=mesh['faces'][group['first']:group['first']+group['count']];vi=face[:,:3].ravel();ui=face[:,3:6].ravel()
        original=np.c_[mesh['position'][vi],mesh['normals'][vi],mesh['uv'][ui]]
        equal=triangle_set(np.array(native))==triangle_set(original)
        results.append(dict(draw=path.stem,component=cs[row['mesh']]['name'],triangles=group['count'],
                            same_oriented_triangles=equal,normal_max_error=normal_error,weight_max_error=weight_error))
    assert all(x['same_oriented_triangles'] and x['normal_max_error']==0 and x['weight_max_error']==0 for x in results),results
    # Prove export succeeds without captured vertex/index/texture data.
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp);minimal=root/capture.name;minimal.mkdir()
        for pattern in ('*-bindings.txt','*-draw-*.txt','*-draw-*.constants','*-draw-*.ps'):
            for source in capture.glob(pattern):shutil.copyfile(source,minimal/source.name)
        a=export(sources,capture,root/'full')
        b=export(sources,minimal,root/'minimal')
        assert a['scene_sha256']==b['scene_sha256']
    return dict(no_captured_geometry_or_texture_dependency=True,draws=len(results),triangles=sum(x['triangles'] for x in results),results=results)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('--sources',type=Path,nargs='+',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=verify(a.sources,a.capture)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print('PASS',result['draws'],'draws,',result['triangles'],'oriented triangles; exact normals and skin weights')
