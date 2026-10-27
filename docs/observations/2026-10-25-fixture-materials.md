# Two-pass light-fixture materials

Analysis date: 2026-10-25. Frozen executable and Menu3D hashes are the
same as [the native fog investigation](2026-10-21-native-fog-state.md).

## Native evidence and scope

`00446480` loads version-6 stage records (24 bytes each) into a linked list.
The low 16-bit continuation values at offsets 24 and 48 are 1 and 0 for
these two-pass materials. `00441560` visits the linked stages in order and
issues a draw per stage; neither resource selects the next-stage bit-0x1000
combined path. `004412B0` selects the regular mesh UVs for these textures.
`0043F9C0`, `0043F300` and `0043F7C0` establish packed UV scale/offset,
time-dependent offsets and rotation. These particular resources have zero
discrete rotation. A zero UV word bypasses the entire transform, as does a pair
of exact unit words; this matters for the lampions base texture.

`006696B0` sets MODULATE2X RGB, MODULATE alpha, wrap sampling and the blend
factors. Its mode 6 uses SRCALPHA/ONE; mode 1 uses SRCALPHA/INVSRCALPHA;
mode 0 disables blending. Bit 0x200 disables depth writes. Definitions were
cross-checked against Microsoft [D3DBLEND](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dblend)
and [D3DTEXTUREOP](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dtextureop)
(accessed 2026-10-25). No external implementation code was copied.

| Material | First pass | Second pass |
| --- | --- | --- |
| 2E00541D (hangfire) | C0066207, texture 2E004C15 | C0066207, texture 2E004C15 |
| 3000FCCE (lampions) | 00200407, texture 6600D789 | 00010207, texture 6600D792 |

Both hangfire passes are additive with independent U/V animation rates and no
depth writes. Lampions use an opaque base, then an alpha overlay with static
UV offsets. The bounded decoder rejects other flags/layouts. All three objects
now retain every group: hangfire1/2 have 60 triangles each, lampions has 544.
The full diagnostic assembly has 46 objects, 15,674 triangles and 39 materials.
The previous partial assembly had 15,122 triangles: 552 triangles are restored.

## Implementation and checks

`src/menu_fixture_materials.py` decodes and samples the two supported materials.
The rasterizer draws complete stage passes in order and allows equal depth for
fixture stages so the overlay survives the base pass. RGB still uses diagnostic
vertex colors, with the traced texture multiplication factor of two; original
scene lighting is not reconstructed. Synthetic tests cover malformed stage
chains, zero-word UV bypass, static versus animated offsets, alpha/additive
composition, saturation and equal-depth second-pass rendering. Six new tests
and the two existing projection tests pass.

The image renderer uses base-level bilinear sampling. Texture 6600D792 contains
43,832 bytes; its raw BGRA base level is bounded at offset 56 with dimensions
128x64. Its remaining lower-level layout does not satisfy the older tight mip
chain calculation (128 additional bytes). A scoped base-level reader accepts
only this key, size and header; lower mips are not interpreted.

## Artifacts and limitations

Ignored local output: `reports/menu-fixture-materials-20261025/renders/`.
The camera position/basis and provisional 59.38-degree vertical FOV are unchanged.
Animation uses the existing effective-time option with phase zero, not captured
runtime phase. The change is visually small at this framing. Native inter-object
transparency ordering, original lighting, filtering/mip selection and live camera
state remain unverified. This completes the previously omitted fixture groups
and their two-pass diagnostic materials, not the original fire/particle system.
OBJ/MTL retains only the first texture stage; individual stage textures and full
stage metadata are exported alongside it. Use the PNG raster to inspect both
passes, not an OBJ viewer alone.
