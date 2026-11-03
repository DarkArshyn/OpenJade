# Native masked additive chain in Vulkan (2026-11-03)

## Evidence and scope

Local GOG D3D9 captures `chain-20-*` and `mask-20-*` in the isolated probe show
a late alpha-only redraw after scene depth is complete. The identified balcony
material `30000D43` contributes 24 triangles (72 expanded vertices). Its material
byte at offset 27 is 184, matching the captured alpha. Two other native draw
writers remain outside this implementation. Game installation files are unchanged.

## Implementation

`menu.glow` binds the exported draw and alpha. The loader checks its size, magic,
range binding and alpha. Ordinary scene passes write RGB only; the late mask pass
writes alpha with depth testing. The scene copy preserves RGBA at 512 square.
The first 256-square reduction multiplies clamped RGB gain 256/255 by source alpha.
Levels 128, 64, 32, 16 and 8 each reduce with gain 256/255, then apply horizontal
and vertical three-tap filters with weight 0.365234405 per tap. Pairs 8+16, 32+64
and 128+256 composite with ONE/ONE blending and gain 256/255. The existing blur
still samples the pre-additive scene copy, then composites at alpha 104/255.
All targets are UNORM, linear sampled and clamped. No temporal feedback is used.
UI and display gamma follow the scene effects. This path requires legacy-unorm
and the prepared native scene sidecars; it does not implement the Effects option.

## Validation

`reports/menu-additive-validation-20261103/comparison.json` records a maximum
2-byte channel difference and mean 0.0158201 against the independent byte-domain
reference at 800x600, fixed time zero. The mask contains 28 nonzero pixels.
Frames 11 and 21 agree; no Vulkan validation errors were reported. The diagnostic
`OPENJADE_CAPTURE_GLOW_MASK=1` exposes alpha as grayscale for this test only.
The original capture contains 23 visible mask pixels for the identified draw;
visibility agreement with GOG is not claimed. Native pyramid intermediate outputs
were separately checked by the research probe; this GPU test checks integration,
not complete original scene lighting or missing emitters.

Run `tests/integration_menu_additive.py` for GPU validation and
`tests/test_menu_additive.py` for synthetic zero/full-mask coverage.
