# Construction and temporal dependencies of the menu blur

Date: 2026-11-03. Follow-up to the
[fullscreen composite audit](2026-11-03-menu-postprocess.md).

## Capture scope and evidence

The independent D3D9 proxy records three consecutive menu frames (20, 21, 22
after detecting the known tronc1 menu draw), including render targets, texture
surfaces, viewport, blend/write states, quad vertices, shaders, constants and
before/after RGB buffers. StretchRect and Clear calls are also recorded.
The game runs in an isolated copy; original game data is untouched. The copied
Hardware.ini is restored afterward. Conditions: 800x600 PC GOG, AMD RX 9070 XT,
ForceVSFog=1, InvertFogRange=0, fixed menu behind the profile selector.

Ignored evidence: `reports/menu-blur-chain-20261103/`, including SHA-256 hashes,
proxy source, three-frame captures and `validation.json`. Captured native shader
binaries remain local. The independent reference implementation is
`src/reconstruct_menu_blur.py`; it has no previous-frame input.

## Observed construction

The trace separates an additive multiresolution chain (passes 25..43) from
the final softened-scene chain (44..48). The latter takes its input from pass 24,
a copy of the current backbuffer made before those additive composites.
It therefore does not simply blur the already-composited backbuffer at pass 44.

Two reusable 512x512 targets, A and B, are used. Sizes below describe the written
region, which is not always the full allocation:

| Pass | Source | Written region | Operation |
| --- | --- | --- | --- |
| 24 | Current 800x600 backbuffer | 512x512 scene copy | StretchRect; captured result matches linear resampling within 1 byte |
| 44 | Current scene copy | All of A, 512x512 | Sample RGB and multiply by 256/255 |
| 45 | A, full UV range | Upper-left B, 256x256 | Linear reduction and RGB multiplication by 256/255 |
| 46 | B, UV range 0..0.5 | Upper-left A, 128x128 | Three offset linear samples with equal weights |
| 47 | A, UV range 0..0.25 | Upper-left B, 256x256 | Three offset linear samples with equal weights |
| 48 | B, UV range 0..0.5 | Current backbuffer, 800x600 | Previously verified source-over composite, alpha 104/255 |

Passes 44/45 use captured diffuse RGB 128/255 and MODULATE2X, hence 256/255.
For passes 46/47 the offsets, in texels of the 512-square source, are (-1,-1),
(+1,0), (0,+1). Constants c0/c1/c2 are 0.333332986; c3 is zero. Three stages bind
the same source surface. All samplers are linear with clamp addressing and no
mipmap filtering. Pixel-center coordinates follow the captured -0.5 quad edges.

Passes 44..47 disable blending and depth testing/writes; their color mask writes
RGB only. A is fully overwritten in pass 44, then partly overwritten in pass 46;
its surrounding current-image texels must be preserved for edge sampling.
B's unused padding is black in all three captured frames. Alpha is not sampled
into final RGB or used as the final blend weight. Do not replace this sequence
with an arbitrary Gaussian blur: reductions, offsets and partial writes matter.

StretchRect reports D3DTEXF_NONE in this trace, but its measured scaled output
matches the independent linear resampler within one byte and does not match
point sampling. This observation is specific to the measured implementation;
it is not a general claim about every D3D9 driver.

## Does it reuse a previous image?

No previous-frame scene contribution is observed in this menu blur chain.
For each of the three frames, these five RGB links are exactly equal:

- Pass 24 output = pass 44 texture input.
- Pass 44 output = pass 45 texture input.
- Pass 45 output = pass 46 texture input.
- Pass 46 output = pass 47 texture input.
- Pass 47 output = pass 48 texture input.

Thus reuse of GPU allocations does not imply reuse of their old image content.
The current-frame path overwrites the sampled working regions. Observed unused
B padding is black, and the retained area of A comes from the same frame's pass 44.
The reference reconstructs each output independently using only its current scene
copy and zero B padding. It reproduces the active 256x256 output with maximum
RGB error 2/255; 99.9883% or more of channels differ by at most one byte.
Mean absolute error is 0.0319..0.0326 byte levels in the active region.

The captured outputs are not identical static images: 34,859 active pixels change
from frame 20 to 21, and 37,540 from 21 to 22. The conclusion concerns this fixed
menu state and this chain. It does not establish that all gameplay effects,
transitions, or other graphics settings are history-free.

## Validation and next step

Four synthetic tests cover the two native gains, partial writes and padding,
bilinear texel centers/clamping, input validation, and absence of retained
working-image state in the independent reference. Three real-frame comparisons
verify all four intermediate passes and their same-frame dependencies. The model
is numerically close but not bit-exact; residual differences are retained in the
report rather than hidden by fitted parameters.

```powershell
python -m unittest discover -s tests -p test_menu_blur.py
python src/reconstruct_menu_blur.py reports/menu-blur-chain-20261103 reports/menu-blur-chain-check
```

Use a new output directory. The reference outputs a reconstructed 256x256 PNG
for each frame and numerical checks. Its inputs are captured original scene RGB,
not a claim that OpenJade already renders every original scene contribution.

The next runtime step is a Vulkan implementation of this measured chain with
explicit intermediate targets, native gains, three-tap offsets and partial-write
behavior, followed by a fixed-image comparison. The separate additive chain and
fog particle simulation remain additional work. No Rust renderer behavior or
production scene parameters changed during this investigation.

Follow-up: [Vulkan integration](2026-11-03-vulkan-menu-blur.md) now implements
the measured chain and validates it against the independent reference. The
implementation-pending statements above describe this audit before integration.
