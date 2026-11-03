# Menu fog particles and fullscreen composite

Date: 2026-11-03. Follow-up to the
[aligned native mip comparison](2026-11-03-native-mips-aligned.md).

## Sources and capture boundaries

Local evidence is in ignored `reports/menu-postprocess-20261103/`.
The independent D3D9 probe observes an isolated GOG game copy. Original game
inputs remain unchanged. The copied Hardware.ini is restored after each run.
The scene is the fixed menu backdrop behind the profile selector, at 800x600,
ForceVSFog=1 and InvertFogRange=0. The measurement point (505,407) is outside UI.
The probe records vertex buffers, declarations, shaders, textures and state for
one frame. One additional readback draws the 64x64 texture point-for-point into
a temporary target, then restores captured device state, render/depth targets
and viewport. It does not substitute a texture in the game's scene.

The source container remains the frozen Menu3D SHA-256
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
Captured shader binaries and original resources stay in ignored local reports.
The repository contains an independent numeric comparison tool and synthetic tests.

## The small dynamic contribution is fog particles

The selected draw has eight triangles, 24 corners in a dynamic stride-36 buffer,
and four quad-like groups with diffuse RGBA values
(119,154,176,18), (115,149,171,7), (114,148,170,6), (111,146,167,1).
It uses source-alpha / inverse-source-alpha blending, depth test enabled,
and depth writes disabled. The triangle count varies between captures.

All 4,096 RGBA texels read from its 64x64 GPU texture exactly match decoded
resource `2E004FE4`. Material `2E0051F1` references this texture at payload
+44. Objects `30000D26` / `Menu3D_Fog3D.gao` and `30000D28` /
`Menu3D_Fog3D2.gao` reference this material at +143 / +144 respectively.
This links the dynamic contribution to the fog emitter family. It does not
identify which emitter owns the selected four quads or recover their spawning,
lifetime, motion and opacity evolution. Do not replace these with static planes.

In the final captured frame these quads change the probe RGB from (51,86,111)
to (54,89,114). The third textured fog panel then changes it to (77,119,149).

## The final contribution is an image-space composite

The last draw is not identified by its stale camera constants. Its declaration
uses POSITIONT, four screen-space vertices and two triangles. Coordinates span
(-0.5,-0.5) to (799.5,599.5), with first UVs spanning (0,0) to (0.5,0.5).
Depth test and writes are disabled. The bound 512x512 ARGB render-target texture
contains a blurred image of the scene in its upper-left 256x256 region.

All four vertex colors are ARGB `68FFFFFF`. The pixel shader samples texture
RGB, multiplies it by the white vertex RGB and takes alpha from the vertex.
Together with the captured source-over blend state this yields:

`output_rgb = blurred_sample_rgb * (104/255) + current_rgb * (151/255)`

These operations are evaluated in stored UNORM values. No gamma curve or
additional light is inferred. The captured texture is an input to the audit,
not an implementation of its generation. Blur kernel, render-target generation,
temporal history and whether this weight varies in other states remain unknown.

The independent `src/compare_menu_postprocess.py` applies bilinear sampling with
the captured texel-center convention. Against the complete 800x600 before/after
framebuffers, the maximum channel error is 1/255, mean error 0.006626 byte levels,
and 100 percent of channels are within one byte level. At (505,407), predicted
and captured RGB both equal (72,111,139), from (77,119,149) before the pass.
This validates the final composite, not the process that generates its source.

## Fog3 phase comparison

The captured fog3 UV rows are c12=(1,0,0.0738018379,0), c13=(0,1,0,0).
A local diagnostic package uses that U offset for fog3 while holding other
Vulkan animations at time zero. At the existing rate 0.0791015625 cycles/s,
it is equivalent to 0.933001 seconds modulo the U period; this is not a recovered
absolute scene clock or synchronization of every animation.

Vulkan at the probe changes from (82,125,155) to (80,123,152). GOG before its
fullscreen pass is (77,119,149), and afterward (72,111,139). Matching fog3 phase
therefore removes part of the difference but does not establish full fidelity.
The production scene package and global lighting settings are unchanged in this
investigation. Neither the captured blurred GOG image nor a guessed blur is
inserted into Vulkan.

## Reproduction and next step

```powershell
python -m unittest discover -s tests -p test_menu_postprocess.py
python src/compare_menu_postprocess.py reports/menu-postprocess-20261103/before.ppm reports/menu-postprocess-20261103/after.ppm reports/menu-postprocess-20261103/blurred-texture.bgra reports/menu-postprocess-check --alpha-byte 104
```

The output directory must be new. Three synthetic tests pass, covering alpha,
texel centers/bilinear interpolation and invalid inputs. The phase-matched Vulkan
capture produces no validation error. Exact capture hashes and vertex layouts
are retained in the local evidence files.

Next priority: trace writes to the blurred render-target texture to recover its
construction and any temporal reuse. Separately trace the two fog emitter objects
to recover particle controls before integrating them into the runtime.

Follow-up: the [construction audit](2026-11-03-menu-blur-construction.md) now
recovers the blur passes and finds no previous-frame scene contribution in three
consecutive fixed-menu frames. The generation/temporal unknowns above describe
the earlier stage of this investigation. Runtime integration remains pending.
