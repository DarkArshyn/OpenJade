# Native trunk mipmaps and aligned GOG comparison

Date: 2026-11-03. This supersedes the leaf depth-write assumption in the earlier
[background probe](2026-11-03-leaf-background.md).

## Native texture integration

Resource `30000C5C`, material `30000C95`, has six BC1 levels: 256, 128, 64,
32, 16 and 8 pixels square. Data starts at payload offset 60. The frozen container
contains both a short metadata record and a full texture record with the same key;
the exporter selects the full record and verifies every base texel against the PNG.
`menu.trunk` carries all six RGBA levels without regenerated mipmaps. Only the
verified tronc1 pass selects its native trilinear sampler. Other passes sharing
the texture keep their existing sampler selection. The leaf retains five native levels.
Keep both `menu.trunk` and `menu.leaf` beside `menu.ojscene`.

## Direct comparison protocol

Local evidence: `reports/native-mips-aligned-20261103/` (ignored by Git).
The independent D3D9 probe captures the GOG backbuffer before Present and the
render target before/after selected draws. The game runs from an isolated copy;
original game inputs are not modified. ForceVSFog=1 and InvertFogRange=0 are used;
the copied Hardware.ini is restored after each run. The capture is 800x600,
A8R8G8B8, without MSAA. It shows the profile selection screen using the same
fixed menu scenery; the measured patch is outside the profile overlay.
Vulkan is captured directly at 800x600, legacy-unorm, no gamma adjustment,
animation time zero. Neither framebuffer is resized or warped for measurement.
The enlarged comparison uses nearest-neighbor scaling only for presentation.

The native tronc1 shader constants c0/c1/c3 and the stored object transform
project 44,955 in-frustum exported corners within a maximum 0.004742 pixel
of the Vulkan camera equations (median 0.001546). This validates the fixed
camera projection, not animation phase or the D3D9/Vulkan half-pixel raster
conventions. Motion phases are not synchronized. Backbuffer reads do not include
an OS display gamma ramp. A single pixel is not a global fidelity metric.

## What actually contributes at (505,407)

This is the 800x600 region corresponding to the previous 1600x1200 repère.
The old and new sample centers differ by a fraction of a pixel.

| Native stage | RGB after the draw | Depth test / write |
| --- | --- | --- |
| Before tronc1 | 32,48,59 | — |
| Tronc1, 128 indexed triangles | 34,63,92 | enabled / enabled |
| Plante2, 72 non-indexed triangles | 51,86,111 | enabled / disabled |
| Additional 8-triangle draw, unresolved | 52,87,112 | enabled / disabled |
| Third fog panel, four indexed triangles | 76,117,148 | enabled / disabled |
| Later two-triangle draw, unresolved | 71,109,138 | disabled / disabled |

The fog panel's model-view depth row matches `Menu3D_fake_fog3.gao`
(`30000D38`) with its native Z scale 0.330190331; maximum row difference is
below 0.000002. The tronc1 draw matches its known index signature and pose.
The two unresolved draws must not yet be assigned an object name.

CPU ray intersections in the exported scene find plante2 at depth 1.646,
fog3 at 4.766 and tronc1 at 7.406. The leaf passes the depth test but does not
write depth in GOG, allowing fog3 to blend afterward against the trunk depth.
The previous Vulkan leaf depth write incorrectly suppressed that contribution.
The renderer now disables that write and orders opaque geometry, the verified
leaf pass, then the remaining transparent passes. This bounded ordering is not
a reconstruction of the engine's general sorting algorithm.

At the same pixel Vulkan changes from RGB (59,96,119), with native trunk mips
but the old depth write, to (82,125,155) after correction. GOG is (71,109,138).
The correction restores a real native contribution but does not establish a
color match. Remaining work: synchronize material/fog phase and identify the
later native draws before modifying lighting or material constants. At (99,383),
GOG is (8,14,20), Vulkan (3,6,8); tronc1/plante2 do not modify that other region.

## Validation

45 Rust tests and five focused Python tests pass. Cargo fmt and clippy pass.
The Vulkan captures at 800x600 and 1600x1200 produce no validation error.
Synthetic tests cover the duplicate resource key, six-level contents, malformed
sidecar extents/bindings, leaf depth flags and opaque/leaf/fog ordering.
The runtime package at `reports/palm-runtime-20261101/` has been regenerated.
Older experimental leaf packages with depth-write flags must be regenerated.

Sources: local frozen decoded Menu3D SHA-256 `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`,
[previous native sampler audit](2026-11-03-trunk-filtering.md),
[native fog transform](2026-10-21-native-fog-state.md), and the current
`pixel-events.txt`, `trunk-filter.txt`, `measurements.json` and framebuffer captures.
