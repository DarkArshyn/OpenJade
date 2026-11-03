"""Measured current-frame masked additive pyramid; byte-domain reference."""
import numpy as np
from reconstruct_menu_blur import sample, q

def reconstruct(rgba):
    s=sample(rgba,256,256)
    v=q(np.minimum(s[:,:,:3]*256/255,255)*s[:,:,3:4]/255)
    levels=[v]
    for size in [128,64,32,16,8]:
        v=q(sample(v,size,size)*256/255)
        for offsets in [[(-1,0),(0,0),(1,0)],[(0,-1),(0,0),(0,1)]]:
            v=q(sum(sample(v,size,size,1,o)*.365234405 for o in offsets))
        levels.append(v)
    return levels

def composite(scene, levels):
    h,w=scene.shape[:2]
    result=scene
    for a,b in [(5,4),(3,2),(1,0)]:
        result=q(result.astype(float)+(sample(levels[a],w,h)+sample(levels[b],w,h))*256/255)
    return result
