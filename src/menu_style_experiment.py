"""Compare explicit style hypotheses, then assemble a static logo/text prototype."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from compare_mft_menu import dice


def thicken_right(image):
    """One source-pixel max expansion to the right, with preserved origin."""
    a=np.asarray(image)
    out=np.zeros((a.shape[0],a.shape[1]+1),dtype=np.uint8)
    out[:,:-1]=a
    out[:,1:]=np.maximum(out[:,1:],a)
    return Image.fromarray(out)


def run(root):
    data=json.loads((root/'experiment.json').read_text(encoding='utf-8-sig'))
    with Image.open(data['ReferenceImage']) as im:
        rgb=np.asarray(im.convert('RGB')).astype(np.int16)
    targets=[(rgb[:,:,0]-rgb[:,:,2]>5)&(rgb[:,:,0]>=rgb[:,:,1])&(rgb[:,:,0]>t) for t in (100,120,140)]
    variants=[]
    layers={}
    for filter_name in ('NEAREST','BILINEAR','BICUBIC','LANCZOS'):
        for style in ('none','source-right-1','screen-right-1'):
            key=filter_name.lower()+'-'+style
            canvas=Image.new('RGBA',(800,600))
            scores=[]
            for row in data['Rows']:
                with Image.open(root/row['Name']/'text.png') as im:
                    alpha=im.getchannel('A')
                box=alpha.getbbox()
                mask=alpha.crop(box)
                scale=row['Height']/row['FontSizeWord']*1.25
                if style=='source-right-1':
                    mask=thicken_right(mask)
                mask=mask.resize((round(mask.width*scale),round(mask.height*scale)),getattr(Image.Resampling,filter_name))
                if style=='screen-right-1':
                    mask=thicken_right(mask)
                spec=row['Specimen']
                x=round((row['X']+row['Left'])*1.25+(box[0]-spec['OriginX'])*scale)
                y=round((row['Y']+row['Top']+row['Height'])*1.25+(box[1]-spec['Baseline'])*scale)
                label=Image.new('RGBA',mask.size,tuple(map(int,row['Color'].split())))
                label.putalpha(mask)
                canvas.alpha_composite(label,(x,y))
                # Fixed per-label ROI for all variants, no fitted translation.
                left=x-6;top=y-6
                width=round((box[2]-box[0])*scale)+16
                height=round((box[3]-box[1])*scale)+12
                pred=np.zeros((height,width),dtype=bool)
                pred[6:6+mask.height,6:6+mask.width]=np.asarray(mask)>=64
                values=[dice(pred,t[top:top+height,left:left+width]) for t in targets]
                scores.append(dict(name=row['Name'],dice_by_threshold=values))
            average=np.mean([s['dice_by_threshold'] for s in scores],axis=0).tolist()
            variants.append(dict(name=key,mean_dice_by_threshold=average,rows=scores))
            layers[key]=canvas
    # Ranking is diagnostic only. Keep the unmodified bilinear model in the main prototype.
    ranked=sorted(variants,key=lambda v:v['mean_dice_by_threshold'][1],reverse=True)
    geometry=json.loads((root/'logo-geometry.json').read_text(encoding='utf-8-sig'))
    rect=[round(geometry[k]*1.25) for k in ('Left','Top','Right','Bottom')]
    with Image.open(root/'logo'/'texture.png') as source:
        logo=source.convert('RGBA').resize((rect[2]-rect[0],rect[3]-rect[1]),Image.Resampling.BILINEAR)
    for name,key in [('prototype','bilinear-none'),('style-candidate',ranked[0]['name'])]:
        layer=Image.new('RGBA',(800,600))
        layer.alpha_composite(logo,(rect[0],rect[1]))
        layer=Image.alpha_composite(layer,layers[key])
        layer.save(root/(name+'-transparent.png'))
        bg=Image.new('RGBA',(800,600),'#181c24')
        Image.alpha_composite(bg,layer).convert('RGB').save(root/(name+'.png'))
    report=dict(variants=ranked,thresholds=[100,120,140],translations_fitted=False,
                prototype_style='bilinear-none',candidate_style=ranked[0]['name'],
                meaning='Diagnostic mask overlap only; not a validated BOLD implementation',
                logo_screen_rectangle=rect,game_rendering_validated=False)
    (root/'style-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    for v in ranked:
        print(v['name'],[round(x,3) for x in v['mean_dice_by_threshold']])


if __name__=='__main__':
    run(Path(sys.argv[1]))
