"""Validate native fog lifecycle, draw appearance and MGM cursor alpha tracks.

Requires local original resources and the bounded fog-life capture.
No game resources are modified.
"""
from pathlib import Path
import struct,collections,json,sys,argparse,hashlib
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from menu_rain_parameters import f32,decode
from probe_menu3d import records
from inspect_menu_scene_links import static_links
parser=argparse.ArgumentParser(description="Replay local native fog and cursor observations")
parser.add_argument('captures',type=Path)
parser.add_argument('menu',type=Path)
parser.add_argument('scene',type=Path)
parser.add_argument('mgm',type=Path)
args=parser.parse_args()
raw=args.menu.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb'
by={r['key']:raw[r['offset']+12:r['end']] for r in records(raw)}
d=decode(by['0x30000D27']);v=lambda i:d[f'{i:03x}']['value'];h=struct.unpack('<f',bytes.fromhex('3b89883c'))[0]
root=args.captures
def particle(b):
 q=list(struct.unpack('<I11f',b));q[7]=struct.unpack_from('<I',b,28)[0];return q
callbacks={};b=(root/'fog-life-callback.bin').read_bytes();off=0
while off<len(b):
 e,f,phase,dt,rem,n=struct.unpack_from('<II IffI',b,off);off+=24;p=[particle(b[off+i*48:off+(i+1)*48]) for i in range(n)];off+=48*n;callbacks[e,f,phase]=(dt,rem,p)
rng=collections.defaultdict(list)
for e,f,r in struct.iter_unpack('<III',(root/'fog-life-rng.bin').read_bytes()):rng[e,f].append(f32(r/32767))
b=(root/'fog-life-states.bin').read_bytes();off=0;counts=collections.Counter();errs=collections.defaultdict(float);phases=collections.Counter();trans=collections.Counter();birthcounts=collections.Counter();deaths=collections.Counter();durations=collections.defaultdict(list)
while off<len(b):
 e,f,dt,old,new,rem=struct.unpack_from('<IIfIIf',b,off);off+=24;p=[particle(b[off+i*48:off+(i+1)*48]) for i in range(new)];off+=48*new
 if (e,f,0) not in callbacks: assert f>max(k[1] for k in callbacks if k[0]==e);continue
 before=callbacks[e,f,0];previous={tuple(q[4:7]):q for q in before[2]};steps=int(f32(before[1]+dt)*60);elapsed=f32(steps*h)
 for q in p[:old]:
  a=previous[tuple(q[4:7])];phase=a[0]&3;phase2=q[0]&3;phases[e,phase2]+=1
  pos=a[1:4].copy()
  for _ in range(steps):pos=[f32(pos[i]+f32(a[i+4]*h)) for i in range(3)]
  errs['position']=max(errs['position'],max(abs(pos[i]-q[i+1]) for i in range(3)))
  spin=(a[7]&32767)<<16;rot=(a[7]+(-spin if a[7]&32768 else spin))&0xffffffff
  assert q[7]==rot,(f,hex(q[7]),hex(rot))
  if phase==phase2:
   errs['timer']=max(errs['timer'],abs(f32(a[9]-elapsed)-q[9]));assert a[8]==q[8];counts[e]+=1
  else:
   trans[e,phase,phase2]+=1;assert (phase,phase2) in [(1,0),(0,2)]
   assert a[9]<elapsed
   duration=1/q[8];lo,hi=(v(0x70),v(0x74)) if phase2==0 else (v(0x78),v(0x7c))
   assert min(lo,hi)-1e-5<=duration<=max(lo,hi)+1e-5
   errs['transition_timer']=max(errs['transition_timer'],abs(f32(duration-elapsed)-q[9]));durations[e,phase2].append(duration)
 gone=set(previous)-{tuple(q[4:7]) for q in p[:old]}
 for key in gone:assert previous[key][0]&3 in (0,2) and previous[key][9]<elapsed,(e,f,old,new,steps,elapsed,previous[key],p[:2])
 deaths[e]+=len(gone)
 # Births consume ten random values, including initial timer and spin.
 assert len(rng[e,f])==10*(new-old)
 mat=np.array(struct.unpack_from('<16f',by[['0x30000D26','0x30000D28'][e]],static_links(by[['0x30000D26','0x30000D28'][e]])['matrix_offset'])).reshape(4,4)
 wave=lambda a,k:f32(np.sin(((round(f32(a*f32(1024/(2*np.pi))))+k)%1024)*f32(2*np.pi/1024)))
 for j,q in enumerate(p[old:]):
  u=rng[e,f][10*j:10*j+10];sample=lambda i,a,b:f32((b-a)*u[i]+a)
  timer=sample(0,v(0x80),v(0x84));assert q[0]&3==1
  sizes=[sample(1,v(0x60),v(0x64)),sample(2,v(0x68),v(0x6c))]
  x=sample(3,-v(0x44),v(0x44));z=sample(4,-v(0x48),v(0x48));a=sample(5,-v(0x58),v(0x58));bb=sample(6,-v(0x58),v(0x5c));speed=sample(7,v(0x50),v(0x54))
  pos=mat[3,:3]+x*mat[0,:3]+z*mat[2,:3]-v(0x40)*mat[1,:3]
  vel=speed*(wave(a,0)*wave(bb,256)*mat[0,:3]-wave(a,256)*wave(bb,256)*mat[1,:3]+wave(bb,0)*mat[2,:3])
  ang=int(f32(sample(8,v(0xac),v(0xb0))*f32(1024/(2*np.pi))));spin=int(f32(sample(9,v(0xb4),v(0xb8))*f32(10430.3779296875)))
  rot=((ang<<22)|(abs(spin)&32767)|(32768 if spin<0 else 0))&0xffffffff
  assert q[7]==rot
  for key,err in [('birth_position',np.max(abs(pos-q[1:4]))),('birth_velocity',np.max(abs(vel-q[4:7]))),('birth_timer',abs(timer-q[9])),('birth_size',np.max(abs(np.array(sizes)-q[10:12])))]:errs[key]=max(errs[key],float(err))
  birthcounts[e]+=1
print('births',birthcounts,'updates',counts,'transitions',trans,'deaths',deaths,'phases',phases,'errors',dict(errs))
print('duration ranges',{str(k):(min(a),max(a)) for k,a in durations.items()})





assert sum(birthcounts.values())>=100 and sum(counts.values())>80000
assert errs['position']==0 and errs['timer']==0 and errs['birth_timer']==0
assert errs['birth_position']<0.00001 and errs['birth_velocity']<0.0000001
assert errs['transition_timer']<0.000001

from menu_rain_appearance import packed_lerp
cam=np.frombuffer(args.scene.read_bytes(),'<f4',12,24)
w=lambda i:f32(np.sin((i%1024)*f32(2*np.pi/1024)))
phases=collections.Counter();mx=0.;draws=0
for f in root.glob('*.particles'):
 vb=f.with_suffix('.vb').read_bytes();ps=[particle(b) for b in [f.read_bytes()[i:i+48] for i in range(0,f.stat().st_size,48)]]
 assert len(vb)==len(ps)*6*36
 for j,p in enumerate(ps):
  flag=p[0]&3;phases[flag]+=1;t=f32(p[8]*p[9]);sx,sy=p[10:12]
  if flag==1:t=f32(1-t);c=packed_lerp(v(0xe8),v(0xe0),t)
  else:c=packed_lerp(v(0xec if flag==2 else 0xe4),v(0xe4 if flag==2 else 0xe0),t)
  argb=c&0xff00ff00|(c&255)<<16|(c>>16)&255
  u=cam[3:6]*sx;vv=-cam[6:9]*sy;i=p[7]>>22
  if p[7]:u,vv=u*w((i+256)%1023)+vv*w(i),vv*w((i+256)%1023)-u*w(i)
  for k,(sa,sb,uv) in enumerate([(-1,-1,(0,1)),(-1,1,(0,0)),(1,1,(1,0)),(1,1,(1,0)),(1,-1,(1,1)),(-1,-1,(0,1))]):
   q=struct.unpack_from('<6fI2f',vb,(6*j+k)*36);assert q[6]==argb,(f,flag,hex(q[6]),hex(argb));assert q[7:]==uv
   mx=max(mx,np.max(abs(np.array(p[1:4])+sa*u+sb*vv-q[:3])))
 draws+=1
print('draws',draws,'phases',phases,'corners',sum(phases.values())*6,'maxXYZ',mx)


assert draws>=200 and all(phases[p]>300 for p in (0,1,2)) and mx<0.00001

# The cursor track comes directly from C_Default, including its reset action.
import xml.etree.ElementTree as ET
text=args.mgm.read_text(encoding='utf-8-sig')
start=text.index('<CURSOR>');end=text.index('</CURSOR>',start)+len('</CURSOR>')
cursor=ET.fromstring(text[start:end]);rate=float(cursor.findtext('FRAMERATE'))
assert cursor.findtext('NAME')=='C_Default' and rate==10
tracks=[]
for image in cursor.findall('./CHILDREN/IMAGE'):
    keys=image.findall('./KEYFRAMES/KEYFRAME')
    points=[(int(k.findtext('IDX')),(int(k.findtext('COLOR1'))&0xffffffff)>>24) for k in keys]
    assert all(len({k.findtext('COLOR'+str(i)) for i in range(1,5)})==1 for k in keys)
    assert keys[-1].findtext('./ACTIONS/GotoFrame/FRAMEIDX')=='0'
    tracks.append((image.findtext('MATERIAL'),points))
assert tracks==[('officialcursor_alpha2_desaturated',[(0,255),(25,250),(50,255),(60,255)]),('test',[(0,255),(25,50),(50,255),(60,255)])]
samples=collections.defaultdict(list)
for frame,dt,color in struct.iter_unpack('<IfI',(root/'fog-life-cursor.bin').read_bytes()):samples[frame].append((dt,color>>24))
phase=0.;last=None;errors=[0,0];reset_frames=[];count=0
for frame,values in samples.items():
    assert len(values)==2
    if last is not None:phase+=values[0][0]*rate
    # Align the observed menu activation restart, separately from the periodic GotoFrame.
    if last is not None and values[1][1]-last>15:phase=0.;reset_frames.append(frame)
    if phase>=60:phase=0.
    for i,(_,points) in enumerate(tracks):
        segment=next(((a,b) for a,b in zip(points,points[1:]) if a[0]<=phase<b[0]))
        (a,x),(b,y)=segment
        predicted=int(x+(y-x)*(phase-a)/(b-a))
        errors[i]=max(errors[i],abs(predicted-values[i][1]))
    last=values[1][1];count+=1
assert count>2400 and max(errors)<=1
print('Cursor pairs',count,'max alpha errors',errors,'observed activation restarts',reset_frames)
