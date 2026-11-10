# Cursor glow and isolated dynamic fog (2026-11-05)

## Scope and evidence

The GOG research copy was observed through a D3D9 proxy. The original installation and scene resources were read only. No OpenJade lighting or runtime rendering was changed. The main measurement uses ForceVSFog=1 and InvertFogRange=0. The research copy's previous Hardware.ini and proxy were restored after capture.

The executable SHA-256 is `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`. The frozen FF000CB9 scene SHA-256 is `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`. Local evidence is in `reports/cursor-fog-evidence-20261105`, including raw before/after BGRA targets, bound DDS textures, buffered vertices, state logs, probe source, measurements and previews. These game-derived files remain unversioned.

Frame numbers count Present calls after the existing menu landmark trigger. They are not video timestamps or synchronized animation phases. Readbacks interrupt normal presentation timing. An earlier exploratory capture used InvertFogRange=1. It is not a synchronized A/B comparison with the normal-fog run.

## Cursor uses both textures

Three captures identify the bound 128x128 images exactly, including every RGBA byte. The first cursor draw uses `officialcursor_alpha2_desaturated.dds`. The next uses `test.dds`, which contains the yellow halo and additional warm coloration. Thus replacing one texture with the other would miss the observed two-pass composition.

Both draws use SRC_ALPHA / INV_SRC_ALPHA, RGB-only writes, no depth test, no depth writes, no alpha test and no fog. Texture RGB modulates diffuse RGB at double gain. The captured diffuse RGB is (127,127,127), producing a factor of 254/255 before target quantization. Texture alpha multiplies diffuse alpha.

| Probe frame | Base diffuse alpha | Halo diffuse alpha | Pixels changed by test.dds | Maximum absolute RGB change |
| --- | ---: | ---: | ---: | ---: |
| 240 | 252 | 158 | 1,561 | 71/255 |
| 720 | 250 | 82 | 1,491 | 37/255 |
| 1200 | 255 | 255 | 1,611 | 116/255 |

The two passes occupy the same quad. At frame 1200 its submitted coordinates span (619.5,36.5) to (663.5,81.5), with UVs covering [0,1]. These are native submitted coordinates, not a proposed resolution-independent layout rule. The cursor moved between the first and later observations. Each before/after pair still measures a single draw at one position.

Every changed pixel from the halo pass equals the corresponding final backbuffer pixel in all three samples. The visible halo is already explained by this late 2D overlay. No additional scene-light contribution was established by this measurement. The alpha changes are observed, but their time function and any hover/input dependency remain unresolved. A controlled same-phase dark/bright-background sweep remains useful.

The current Vulkan UI exporter still selects only the base cursor texture. A faithful follow-up must preserve both passes and resolve the native alpha update before claiming an exact animated glow.

## Dynamic fog bindings

| Object | GAO key | Native origin |
| --- | --- | --- |
| Menu3D_Fog3D.gao | 30000D26 | (-88.702988, 1.795274, -3.746641) |
| Menu3D_Fog3D2.gao | 30000D28 | (-98.306015, -2.623171, -0.067985) |

Both GAOs reference descriptor `30000D27` and material `2E0051F1`. The captured 64x64 texture matches decoded `2E004FE4` exactly. The full effective matrices are retained in the logs. Fog3D2 has a different orientation as well as a different origin. Matching the flags alone is insufficient because pollen shares flags `80001041` and capacity 20.

The descriptor stores capacity 20 per emitter, emission rate 5, rectangle half-extents (4.791600,2.361960), speed range (0,0.313210) and zero acceleration. Stored phase ranges are initial (1.464100,3.664390), main (1.762385,6.466816) and end (2.121439,0). The descending end range is preserved as stored. It must be interpreted through the native sampling arithmetic rather than sorted by the exporter.

Both fog draws use SRC_ALPHA / INV_SRC_ALPHA, MODULATE2X texture/diffuse color, multiplied texture/diffuse alpha, depth testing, no depth writes, no alpha test and fog enabled. They are transparent particles, distinct from the existing polygonal fog panels and from the additive pollen.

## Measured contribution

The table subtracts the target immediately before each emitter draw from the target immediately after it. All counts refer to 800x600 RGB pixels. The two emitter regions can overlap, so their counts must not be summed as unique coverage.

| Probe frame | Emitter | Particles submitted | Changed pixels | Maximum absolute channel change |
| --- | --- | ---: | ---: | ---: |
| 240 | Fog3D | 8 | 271,404 | 28/255 |
| 240 | Fog3D2 | 8 | 40,070 | 31/255 |
| 720 | Fog3D | 20 | 353,230 | 93/255 |
| 720 | Fog3D2 | 20 | 60,724 | 66/255 |
| 1200 | Fog3D | 19 | 295,664 | 60/255 |
| 1200 | Fog3D2 | 19 | 60,831 | 26/255 |

Fog3D changes a broad foreground/lower-scene region. Fog3D2 changes the balcony region more locally. The difference images show occlusion by foreground geometry. Some channels decrease because source-over transparency can both brighten and darken the destination. This is additional evidence for missing dynamic fog, not a reason to compensate by changing global lighting.

These are draw-local measurements before later scene composition. They are not final-image contributions after blur, and they do not validate the complete fog model. The two dynamic emitters remain absent from Vulkan. Their birth, phase transitions, spin, effective fog factors and particle ordering still need a native-state replay before integration. Retain the existing panels while adding these emitters, then evaluate the complete image before revisiting lights.

## Reproduce the checks

Extract the local `cursor-fog-captures.zip` and run from the repository root, substituting the local paths:

```powershell
python tests/integration_cursor_fog.py <cursor-fog-normal-directory> <FF000CB9-decoded/decoded.bin> <POPData-extracted/menu/texture>
```

The check validates source hash, GAO links and origins, all bound texture pixels, draw blend/depth/fog state, cursor vertex colors, three observations per object and equality of the halo's changed pixels with final composition. It emits the per-draw measurements as JSON. Twelve observations pass. This is a native evidence check, not a Vulkan regression test.

## Follow-up

The [lifecycle and cursor-track check](2026-11-05-fog-cursor-lifecycle.md) resolves the MGM alpha keyframes and validates fog birth, motion, phase appearance and packed rotation. See that report for remaining precision and integration limits.
