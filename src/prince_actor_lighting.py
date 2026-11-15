"""Prepare animated-normal lighting with explicit native-capture parameter provenance."""
import copy,json,struct
from pathlib import Path
import numpy as np
from prince_resources import Resources,COMPONENTS
from prince_animation import Skeleton
from export_prince_preview import capture_draws

def prepare(sources,capture,output):
    from export_prince_animation import influences
    r=Resources(sources);s=Skeleton(r);report=json.loads((output/'manifest.json').read_text())
    rows=capture_draws(capture);native={row['path'].name:row for row in rows}
    body=next(row for row in rows if row['mesh']=='13008426')['constants']
    model_view=body[4:8].T;rotation=model_view[:3,:3];inverse=np.linalg.inv(model_view)
    values=list(body[25,:3])
    for direction,color in [(27,28),(39,40)]:values.extend(body[direction,:3]@rotation.T);values.extend(body[color,:3])
    for position,color,attenuation in [(30,32,33),(34,36,37)]:
        values.extend((np.r_[body[position,:3],1.]@inverse)[:3]);values.extend(body[color,:3]);values.extend(body[attenuation,:2])
    components={c['mesh']:c for c in (r.component(k) for k in COMPONENTS)}
    pending={k:list(c['geometry']['groups']) for k,c in components.items()}
    normal_cache={};records=[]
    for item in report['draws']:
        c=components[item['mesh']];mesh=c['geometry'];group=pending[item['mesh']].pop(0)
        native_row=native[item['capture']];fixed=native_row['tss'][0,3]==3
        if item['mesh'] not in normal_cache:
            trial=copy.deepcopy(c);trial['geometry']['position']=np.zeros_like(mesh['position']);origins=influences(r,s,trial)
            trial['geometry']['position']=mesh['normals'];tips=influences(r,s,trial)
            normal_cache[item['mesh']]=[[np.asarray(t[2])-o[2] for t,o in zip(ts,os)] for ts,os in zip(tips,origins)]
        ids=mesh['faces'][group['first']:group['first']+group['count'],:3].ravel()
        for vid in ids:
            record=struct.pack('<I',0 if fixed else 1)
            if not fixed:
                for n in normal_cache[item['mesh']][vid]:record+=struct.pack('<3f',*n)
            records.append(record)
    blob=b'OJALIT01'+struct.pack('<I31f',len(records),*values)+b''.join(records)
    (output/'prince.actorlight').write_bytes(blob)
    return dict(parameters='Frozen native light parameters transformed into actor coordinates; normals and positions update at runtime.',vertices=len(records),fixed_material_vertices=sum(struct.unpack_from('<I',x)[0]==0 for x in records))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('capture',type=Path);p.add_argument('output',type=Path);p.add_argument('--sources',type=Path,nargs='+',required=True);a=p.parse_args();print(json.dumps(prepare(a.sources,a.capture,a.output),indent=2))
