"""Validate the measured fullscreen composite without generating a substitute blur.

Inputs are local GPU captures, not distributable game fixtures. Sampling follows
captured -0.5 screen vertices and the texture UV extent of the measured quad.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image


def composite(before, texture, alpha_byte, uv_extent=0.5):
    """Sample the captured texture and evaluate source-over in stored RGB values."""
    if before.ndim != 3 or texture.ndim != 3 or before.shape[2] != 3 or texture.shape[2] != 3:
        raise ValueError("Expected RGB images")
    if not 0 <= alpha_byte <= 255 or not 0 < uv_extent <= 1:
        raise ValueError("Invalid captured composite parameters")
    h, w = before.shape[:2]
    th, tw = texture.shape[:2]
    x = (np.arange(w) + .5) * uv_extent * tw / w - .5
    y = (np.arange(h) + .5) * uv_extent * th / h - .5
    # The measured quad stays inside the populated texture region.
    ix, iy = np.floor(x).astype(int), np.floor(y).astype(int)
    fx, fy = (x-ix)[None,:,None], (y-iy)[:,None,None]
    ix0, ix1 = np.clip(ix,0,tw-1), np.clip(ix+1,0,tw-1)
    iy0, iy1 = np.clip(iy,0,th-1), np.clip(iy+1,0,th-1)
    tex = texture.astype(float)
    sampled = ((tex[iy0[:,None],ix0] * (1-fx) + tex[iy0[:,None],ix1] * fx) * (1-fy)
             + (tex[iy1[:,None],ix0] * (1-fx) + tex[iy1[:,None],ix1] * fx) * fy)
    return before.astype(float)*(1-alpha_byte/255) + sampled*(alpha_byte/255)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("texture_bgra", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--alpha-byte", type=int, required=True)
    args = parser.parse_args()
    before = np.asarray(Image.open(args.before).convert("RGB"))
    after = np.asarray(Image.open(args.after).convert("RGB"))
    raw = args.texture_bgra.read_bytes()
    if len(raw) != 512*512*4 or before.shape != (600,800,3) or after.shape != before.shape:
        raise ValueError("Only the measured 800x600 / 512x512 capture layout is supported")
    texture = np.frombuffer(raw, "u1").reshape(512,512,4)[:,:,[2,1,0]]
    predicted = np.clip(np.rint(composite(before, texture, args.alpha_byte)),0,255).astype("uint8")
    error = np.abs(predicted.astype(int)-after.astype(int))
    result = dict(alpha_byte=args.alpha_byte, alpha=args.alpha_byte/255,
        max_channel_error=int(error.max()), mean_channel_error=float(error.mean()),
        channels_within_one=float(np.mean(error<=1)),
        point_505_407=dict(before=before[407,505].tolist(), predicted=predicted[407,505].tolist(), after=after[407,505].tolist()),
        limitation="Captured source texture; its generation and temporal behavior are not reconstructed")
    args.output.mkdir(parents=True, exist_ok=False)
    Image.fromarray(predicted).save(args.output/"predicted.png")
    (args.output/"comparison.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(json.dumps(result,indent=2))

if __name__ == "__main__": main()
