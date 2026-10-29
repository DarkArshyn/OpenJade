"""Prepare DDS/MFT sprites for Rust menus; no Python process is needed at runtime."""
import argparse
import json
import struct
from pathlib import Path
from PIL import Image
from simulation_screens import Screens
from menu_scene import Font


def export(report, legacy, output, fonts):
    screens = Screens(report)
    # Reuse the already validated Camera02 samples, not the baked menu images.
    data = legacy.read_bytes()
    if data[:8] != b'OJUI0001' or data[-28136:-28132] != struct.pack('<I', 541):
        raise ValueError('Expected an OJUI0001 bundle with 541 camera samples')
    sprites = []
    def add(name, image, dx=0, dy=0, advance=0):
        sprites.append((name, image.convert('RGBA'), dx, dy, advance))
    sizes = [10,12,14,16,18,20,22,24,26,28,36,48]
    for size in sizes:
        font = Font(fonts / str(size))
        if font.info['SizeWord'] != size:
            raise ValueError('Font size does not match directory')
        signed = lambda n: int(n) - 256 if int(n) >= 128 else int(n)
        for code in range(32, 127):
            g = font.glyphs[code]
            x, y = int(g['AtlasX']) + 1, int(g['AtlasY']) + 1
            w, h = int(g['Width']), int(g['Height'])
            mask = font.atlas.crop((x, y, x + max(1, w), y + max(1, h)))
            if not w or not h:
                mask = Image.new('L', (1, 1))
            box = mask.getbbox() or (0, 0, 1, 1)
            mask = mask.crop(box)
            image = Image.new('RGBA', mask.size, 'white'); image.putalpha(mask)
            add(f'f{size}_c{code}', image, signed(g['Metric2Raw']) + box[0],
                -signed(g['Metric3Raw']) + box[1], int(g['Metric4Raw']))
    panel = Image.new('RGBA', screens.panel.size)
    panel.putalpha(screens.panel.getchannel('A').point(lambda v: round(v * .59)))
    add('panel', panel.resize((500, 500), Image.Resampling.BILINEAR))
    add('logo', screens.logo)
    add('cursor', screens.texture('officialcursor_alpha2_desaturated.dds'))
    add('eax', screens.texture('eax.dds').resize((104, 33)))
    add('field', Image.new('RGBA', (2, 2), (65, 65, 65, 130)))
    for name in ('up', 'down'):
        im = screens.texture(f'b_list_{name}.dds')
        add(name, im.crop(im.getchannel('A').getbbox()).resize((16, 22)))
    for name, key in screens.widgets['sprites'].items():
        add(name, screens.scene.sprites[key])
    # Shelf packing with two transparent texels between entries.
    atlases = [Image.new('RGBA', (512, 512))]
    entries = []; x = y = 2; row = 0
    for name, im, dx, dy, advance in sprites:
        if max(im.size) > 508:
            if im.width * im.height > 512 * 512 or max(im.size) > 2048:
                raise ValueError(f'Oversized sprite: {name} {im.size}')
            atlases.append(im)
            entries.append((name, len(atlases)-1, 0, 0, im.width, im.height, dx, dy, advance))
            atlases.append(Image.new('RGBA', (512,512))); x = y = 2; row = 0
            continue
        if x + im.width + 2 > 512:
            x = 2; y += row + 4; row = 0
        if y + im.height + 2 > 512:
            atlases.append(Image.new('RGBA', (512, 512))); x = y = 2; row = 0
        if name.startswith('f') and '_c' in name:
            # Transparent white gutter avoids black fringes during linear filtering.
            atlases[-1].paste((255,255,255,0),(x-2,y-2,x+im.width+2,y+im.height+2))
        atlases[-1].paste(im, (x, y))
        entries.append((name, len(atlases)-1, x, y, im.width, im.height, dx, dy, advance))
        x += im.width + 4; row = max(row, im.height)
    blob = bytearray(b'OJUI0003')
    blob.extend(struct.pack('<IfI', len(atlases), 36.0, len(entries)))
    for atlas in atlases: blob.extend(struct.pack('<2I', *atlas.size))
    blob.extend(struct.pack('<I',len(sizes)))
    blob.extend(struct.pack('<'+'I'*len(sizes),*sizes))
    for name, *values in entries:
        encoded = name.encode('ascii')
        blob.extend(struct.pack('<I', len(encoded))); blob.extend(encoded)
        blob.extend(struct.pack('<5I3f', *values))
    for atlas in atlases:
        raw = atlas.tobytes(); blob.extend(raw); blob.extend(bytes(512*512*4-len(raw)))
    blob.extend(data[-28136:])
    output.mkdir(parents=True, exist_ok=False)
    (output/'menu.ojui').write_bytes(blob)
    (output/'manifest.json').write_text(json.dumps(dict(format='OJUI0003', font_sizes=sizes, logo_size=screens.logo.size, cursor_size=screens.texture('officialcursor_alpha2_desaturated.dds').size,
        atlas_layers=len(atlases), sprites=len(entries), camera_samples=541,
        provenance=str(report), camera_bundle=str(legacy),
        limitations=['Independent reconstructed layouts and session profiles',
                     'No original save format, audio or gameplay systems']), indent=2))
    for i, atlas in enumerate(atlases): atlas.save(output/f'atlas-{i}.png')
    print(f'{len(entries)} sprites in {len(atlases)} atlases; 541 camera samples')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('report', type=Path); p.add_argument('legacy', type=Path); p.add_argument('output', type=Path)
    p.add_argument('--fonts', required=True, type=Path, help='Directory of Read-MFT exports named by size')
    a = p.parse_args(); export(a.report, a.legacy, a.output, a.fonts)
