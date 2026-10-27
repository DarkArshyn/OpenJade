import math
import numpy as np
from PIL import Image
from menu_fog_state import sample_fog
from menu_fixture_materials import composite_fixture

def clip_polygon(poly,near=.1):
    result=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ia=a[2]>=near;ib=b[2]>=near
        if ia:result.append(a)
        if ia!=ib:result.append(a+(b-a)*((near-a[2])/(b[2]-a[2])))
    return result


def raster(objects,textures,position,basis,fov,flip=False,blend_enabled=True):
    width,height=800,600
    rgb=np.zeros((height,width,3),dtype=np.uint8);rgb[:]=[24,28,36]
    depth=np.full((height,width),np.inf)
    focal=height/(2*math.tan(math.radians(fov)/2));drawn=0
    opaque=[o for o in objects if not (blend_enabled and o.get('blend',False))]
    transparent=[o for o in objects if blend_enabled and o.get('blend',False)]
    transparent.sort(key=lambda o:float(-((o['vertices'].mean(axis=0)-position)@basis.T)[1]),reverse=True)
    for obj in opaque+transparent:
        blend=blend_enabled and obj.get('blend',False)
        local=(obj['vertices']-position)@basis.T
        # Native -B0 view axis; -B2 and the negative projection Y cancel.
        view=np.column_stack((-local[:,0],local[:,2],-local[:,1],obj['uv'],obj['colors']))
        cursor=0
        for slot,count in obj['groups']:
            material=textures[slot]
            passes=[dict(material,stages=[stage]) for stage in material['stages']] if isinstance(material,dict) else [material]
            for pass_index,tex in enumerate(passes):
                for tri in obj['triangles'][cursor:cursor+count]:
                    poly=clip_polygon([view[i].copy() for i in tri])
                    for k in range(1,len(poly)-1):
                        t=np.array([poly[0],poly[k],poly[k+1]])
                        pts=np.column_stack((400+focal*t[:,0]/t[:,2],300-focal*t[:,1]/t[:,2]))
                        x0=max(0,int(np.floor(pts[:,0].min())));x1=min(width,int(np.ceil(pts[:,0].max()))+1)
                        y0=max(0,int(np.floor(pts[:,1].min())));y1=min(height,int(np.ceil(pts[:,1].max()))+1)
                        if x0>=x1 or y0>=y1:continue
                        a,b,c=pts;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
                        if abs(den)<1e-8:continue
                        xx,yy=np.meshgrid(np.arange(x0,x1)+.5,np.arange(y0,y1)+.5)
                        w0=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
                        w1=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;w2=1-w0-w1
                        inside=(w0>=-1e-8)&(w1>=-1e-8)&(w2>=-1e-8)
                        inverse=w0/t[0,2]+w1/t[1,2]+w2/t[2,2]
                        safe=np.where(inverse>0,inverse,1)
                        z=1/safe;mask=inside&(inverse>0)&(z<=depth[y0:y1,x0:x1] if isinstance(tex,dict) else z<depth[y0:y1,x0:x1])
                        if not mask.any():continue
                        uv=(w0[...,None]*t[0,3:5]/t[0,2]+w1[...,None]*t[1,3:5]/t[1,2]+w2[...,None]*t[2,3:5]/t[2,2])/safe[...,None]
                        if flip:uv[...,1]=1-uv[...,1]
                        if isinstance(tex,dict):
                            lighting=(w0[...,None]*t[0,5:]/t[0,2]+w1[...,None]*t[1,5:]/t[1,2]+w2[...,None]*t[2,5:]/t[2,2])/safe[...,None]
                            region=rgb[y0:y1,x0:x1]
                            composed=composite_fixture(region,uv,lighting,tex)
                            region[mask]=composed[mask]
                            if any(s['depth_write'] for s in tex['stages']):
                                depth[y0:y1,x0:x1][mask]=z[mask]
                            drawn+=1
                            continue
                        if obj.get('fog_sampler',False):
                            samples=sample_fog(tex,uv)
                        else:
                            uv%=1
                            tx=np.minimum((uv[...,0]*tex.shape[1]).astype(int),tex.shape[1]-1)
                            ty=np.minimum((uv[...,1]*tex.shape[0]).astype(int),tex.shape[0]-1)
                            samples=tex[ty,tx]
                        mask&=samples[...,3]>0 if blend else samples[...,3]>=128
                        lighting=(w0[...,None]*t[0,5:]/t[0,2]+w1[...,None]*t[1,5:]/t[1,2]+w2[...,None]*t[2,5:]/t[2,2])/safe[...,None]
                        shaded=np.clip(samples[...,:3]*lighting,0,255).astype(np.uint8)
                        if blend:
                            alpha=samples[...,3:4]/255.0
                            composite=np.clip(shaded*alpha+rgb[y0:y1,x0:x1]*(1-alpha),0,255).astype(np.uint8)
                            rgb[y0:y1,x0:x1][mask]=composite[mask]
                        else:
                            rgb[y0:y1,x0:x1][mask]=shaded[mask]
                            depth[y0:y1,x0:x1][mask]=z[mask]
                        drawn+=1
            cursor+=count
    return Image.fromarray(rgb),int(np.isfinite(depth).sum()),drawn

