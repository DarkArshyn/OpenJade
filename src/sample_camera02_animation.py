"""Bounded Camera02 sampling, using native row-matrix quaternion conventions."""
import math
import numpy as np
from compose_camera02_pose import compose_pose


def quaternion_matrix(q):
    x,y,z,w=q
    return np.array([[1-2*y*y-2*z*z,2*x*y+2*w*z,2*x*z-2*w*y],
                     [2*x*y-2*w*z,1-2*x*x-2*z*z,2*y*z+2*w*x],
                     [2*x*z+2*w*y,2*y*z-2*w*x,1-2*x*x-2*y*y]])


def native_slerp(a,b,t):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    dot=float(a@b)
    if dot<0: b=-b;dot=-dot
    dot=min(1.,dot)
    if abs(dot-1.)<=1.0000000116860974e-7: return a.copy()
    angle=math.acos(dot)
    q=(math.sin((1-t)*angle)*a+math.sin(t*angle)*b)/math.sqrt(1-dot*dot)
    return q/np.linalg.norm(q)


def sample_track(track,time):
    keys=track['keys']
    rotation=track['kind']=='packed_rotation'
    def value(k): return np.array(k['values'],dtype=float)/(32768 if rotation else 1)
    if time>=keys[-1]['start_seconds']: return value(keys[-1])
    i=max(i for i,k in enumerate(keys[:-1]) if k['start_seconds']<=time)
    a,b=value(keys[i]),value(keys[i+1])
    t=(time-keys[i]['start_seconds'])/keys[i]['duration_seconds']
    return native_slerp(a,b,t) if rotation else a+(b-a)*t


def sample_pose(captured,decoded,time):
    if not math.isfinite(time) or not 0<=time<=9: raise ValueError('Time must be in [0,9]')
    rotation,vector=decoded['tracks']
    return compose_pose(captured,sample_track(vector,time),quaternion_matrix(sample_track(rotation,time)))
