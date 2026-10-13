"""Bounded menu specimen experiment; no background recreation or game fidelity claim."""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def dice(a, b):
    denominator = int(a.sum()) + int(b.sum())
    return 2 * int(np.logical_and(a, b).sum()) / denominator if denominator else 0.0


def compare(root):
    data = json.loads((root / 'experiment.json').read_text(encoding='utf-8-sig'))
    with Image.open(data['ReferenceImage']) as source:
        if source.size != (800, 600):
            raise ValueError('Only 800x600 reference captures are supported.')
        reference = source.convert('RGB')
    rgb = np.asarray(reference).astype(np.int16)
    # Heuristic gold-text segmentation, not a ground-truth alpha mask.
    gold = (rgb[:, :, 0] - rgb[:, :, 2] > 5) & (rgb[:, :, 0] >= rgb[:, :, 1]) & (rgb[:, :, 0] > 120)
    canvas = Image.new('RGBA', (800, 600))
    panels = Image.new('RGB', (850, 6 * 115), '#181c24')
    draw = ImageDraw.Draw(panels)
    results = []
    for index, row in enumerate(data['Rows']):
        spec = row['Specimen']
        with Image.open(root / row['Name'] / 'text.png') as image:
            alpha = image.getchannel('A')
        box = alpha.getbbox()
        if box is None:
            raise ValueError('Unexpected blank label.')
        scale = row['Height'] / row['FontSizeWord'] * 1.25
        mask = alpha.crop(box).resize((round((box[2]-box[0])*scale), round((box[3]-box[1])*scale)), Image.Resampling.BILINEAR)
        x_float = (row['X']+row['Left'])*1.25 + (box[0]-spec['OriginX'])*scale
        # Explicit baseline hypothesis: MGM top + HEIGHT.
        y_float = (row['Y']+row['Top']+row['Height'])*1.25 + (box[1]-spec['Baseline'])*scale
        x, y = round(x_float), round(y_float)
        color = tuple(map(int, row['Color'].split()))
        label = Image.new('RGBA', mask.size, color)
        label.putalpha(mask)
        canvas.alpha_composite(label, (x, y))
        binary = np.asarray(mask) >= 64
        # Fixed ROI ensures missing/extra text contributes to the score.
        left, top = x-6, y-6
        width, height = mask.width+12, mask.height+12
        observed = gold[top:top+height, left:left+width]
        candidates = []
        for dy in range(-4, 5):
            for dx in range(-4, 5):
                predicted = np.zeros((height, width), dtype=bool)
                predicted[6+dy:6+dy+mask.height, 6+dx:6+dx+mask.width] = binary
                candidates.append((dice(predicted, observed), dx, dy))
        best = max(candidates, key=lambda c: (c[0], -abs(c[1])-abs(c[2])))
        unadjusted = next(c[0] for c in candidates if c[1:] == (0, 0))
        sensitivity = []
        for threshold in (100, 120, 140):
            alternative = (rgb[:,:,0]-rgb[:,:,2]>5) & (rgb[:,:,0]>=rgb[:,:,1]) & (rgb[:,:,0]>threshold)
            target = alternative[top:top+height,left:left+width]
            scores=[]
            for dy in range(-4,5):
                for dx in range(-4,5):
                    test=np.zeros((height,width),dtype=bool)
                    test[6+dy:6+dy+mask.height,6+dx:6+dx+mask.width]=binary
                    scores.append((dice(test,target),dx,dy))
            peak=max(scores,key=lambda c:(c[0],-abs(c[1])-abs(c[2])))
            sensitivity.append(dict(red_threshold=threshold,dice=peak[0],translation=list(peak[1:])))
        results.append(dict(name=row['Name'], text=row['Text'], scale=scale,
                            predicted_ink_xy=[x_float,y_float], rounded_ink_xy=[x,y],
                            ink_size=list(mask.size), unadjusted_dice=unadjusted,
                            best_dice=best[0], best_translation=list(best[1:]), sensitivity=sensitivity))
        py=index*115
        draw.text((10,py+4), row['Text']+' | reference / unadjusted / best translation', fill='white')
        panels.paste(reference.crop((left,top,left+width,top+height)), (10,py+24))
        panels.paste(label, (440+6,py+24+6), label)
        # Contour diagnostic: gold mask in red; fitted specimen in cyan; overlap white.
        fit=np.zeros((height,width),dtype=bool)
        fit[6+best[2]:6+best[2]+mask.height,6+best[1]:6+best[1]+mask.width]=binary
        overlay=np.zeros((height,width,3),dtype=np.uint8)
        overlay[:,:,0]=observed*255;overlay[:,:,1]=fit*255;overlay[:,:,2]=fit*255
        panels.paste(Image.fromarray(overlay), (10,py+65))
        draw.text((440,py+70), f'Dice {unadjusted:.3f} -> {best[0]:.3f}; dx,dy={best[1:]}', fill='white')
    canvas.save(root/'menu-text.png')
    background=Image.new('RGBA',(800,600),'#181c24')
    Image.alpha_composite(background,canvas).convert('RGB').save(root/'menu-preview.png')
    panels.save(root/'comparison.png')
    report=dict(method='R-B>5, R>=G, R>120 vs alpha>=64; Dice in fixed padded ROI; sensitivity R>100/120/140',
                translation_search='-4..4 pixels on each axis; scale fixed from MGM',
                caveats=['JPEG and background affect segmentation', 'Bold flag not implemented',
                         'Baseline, filtering and font selection remain hypotheses',
                         'Reference capture build is not established'], rows=results)
    (root/'comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    for row in results:
        print(row['name'], 'Dice', round(row['unadjusted_dice'],3), 'best', round(row['best_dice'],3), row['best_translation'])


if __name__ == '__main__':
    compare(Path(sys.argv[1]))
