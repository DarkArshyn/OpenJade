"""Compare final Vulkan pixels at fixed camera/animation poses and optionally profile."""
from pathlib import Path
import os,sys,json,struct,shutil,subprocess
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent))
from integration_prince_vulkan import verify
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('source',type=Path,help='Prepared menu folder')
parser.add_argument('poses',type=Path,help='Decoded Camera02 poses JSON')
parser.add_argument('output',type=Path)
parser.add_argument('--viewer',type=Path,required=True)
parser.add_argument('--profile',action='store_true')
args=parser.parse_args();source=args.source;out=args.output;out.mkdir(parents=True,exist_ok=False)
poses=json.loads(args.poses.read_text(encoding='utf-8'));viewer=args.viewer
assert {0,4.5,9}.issubset({p['time'] for p in poses['poses']})
results=[]
for time in [0,4.5,9]:
 pose=min(poses['poses'],key=lambda p:abs(p['time']-time));time=pose['time']
 target=out/f'camera-{time:g}';target.mkdir()
 for f in source.glob('menu.*'):shutil.copyfile(f,target/f.name)
 m=pose['matrix'];camera=m[3][:3]+[-x for x in m[0][:3]]+m[2][:3]+[-x for x in m[1][:3]]+[poses['vertical_fov']]
 path=target/'menu.ojscene';blob=bytearray(path.read_bytes());struct.pack_into('<13f',blob,24,*camera);path.write_bytes(blob)
 (target/'camera.json').write_text(json.dumps(pose,indent=2),encoding='utf-8')
 for mode in ['dynamic','frozen','off','dynamic-repeat']:
  os.environ['OPENJADE_GENERATED_LIGHT']=mode.split('-')[0]
  print(time,mode,verify(path,target/mode,viewer,2.),flush=True)
 def image(mode):return np.array(Image.open(target/mode/'prince.png').convert('RGB'))
 dynamic=image('dynamic');assert np.array_equal(dynamic,image('dynamic-repeat'))
 row=dict(camera_seconds=time,animation_seconds=2.,repeat_identical=True)
 for other in ['frozen','off']:
  diff=abs(dynamic.astype(int)-image(other).astype(int));mask=np.any(diff,axis=2)
  ys,xs=np.nonzero(mask)
  row[other]=dict(changed_pixels=int(mask.sum()),maximum_channel_difference=int(diff.max()),absolute_rgb_sum=int(diff.sum()),
                   bounds=[int(xs.min()),int(ys.min()),int(xs.max()),int(ys.max())] if len(xs) else None)
  Image.fromarray(np.minimum(diff*16,255).astype('uint8')).save(target/f'difference-{other}-x16.png')
 assert row['off']['changed_pixels']>0
 if time>0:assert row['frozen']['changed_pixels']>0
 # Per-receiver origins may already differ from the frozen shared term at time zero.
 results.append(row);print('pixel result',row,flush=True)
os.environ.pop('OPENJADE_GENERATED_LIGHT',None)
(out/'pixels.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
# Same endpoint and workload, separate processes, no screenshot layer while profiling.
for mode in (['frozen','dynamic','dynamic','frozen'] if args.profile else []):
 number=len(list(out.glob('timing-*.txt')))
 env=dict(os.environ,OPENJADE_PROFILE_FRAMES='1800',OPENJADE_PROFILE_PRESENT='fifo',OPENJADE_GENERATED_LIGHT=mode)
 for key in ['OPENJADE_CAPTURE_SECONDS','VK_INSTANCE_LAYERS','VK_SCREENSHOT_FRAMES','VK_SCREENSHOT_DIR']:env.pop(key,None)
 result=subprocess.run([str(viewer),'--scene',str(out/'camera-9/menu.ojscene'),'--color-pipeline','legacy-unorm','--validation'],env=env,capture_output=True,text=True,timeout=90,check=True)
 text=result.stdout+result.stderr;assert 'validation errors: 0' in text and 'VUID-' not in text
 (out/f'timing-{number}-{mode}.txt').write_text(text,encoding='utf-8')
 print(mode,'\n'.join(line for line in text.splitlines() if line.startswith('Timing ')),flush=True)
