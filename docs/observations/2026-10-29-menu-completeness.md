# Cached balcony colors, fog coverage and missing menu resources

Analysis date: 2026-10-29. This is a focused audit of the frozen menu,
not a live capture of the original game. Original assets are read-only.

## Cached colors: stored bytes and native upload

The balcony instance 30000CD9 uses mesh 30000C8C. Its primary representation
has 10,731 vertices, 8,898 triangles and 26,694 expanded corners. The cached
representation stores 14,503 vertices (separate UV combinations), not a new mesh.

| Data | Payload offset | Stride / size |
| --- | ---: | --- |
| Cached geometry in 30000C8C | 279428 | 14,503 vertices, 20 bytes each |
| Cached index byte count | 569488 | 53,388 bytes |
| Cached indices | 569492 | 26,694 uint16 indices |
| Cached colors in 30000CD9 | 43153 | 14,503 entries, 12 bytes each |

Expanding the cached indices gives **zero position error, zero UV error and
zero RGB mismatches across all 26,694 corners**. Cached color bytes are BGRA;
primary instance bytes are RGBA. There is no stored halving of RGB. The extra
eight bytes per cached instance entry are not interpreted by this audit.

Native chain newly traced with read-only Ghidra:

1. `00445D40` loads the cached geometry at mesh +0x4C and per-group index buffers.
2. `0067D8C0` calls `00446140`, which fills the instance stream at +0x20 by
   copying count * stride bytes from its resource.
3. `0066ADC0` constructs the static buffer through `006704C0`. Its vtable
   007B18B8 has upload slot +0x0C pointing to `00670510`.
4. `00445D20` invokes that upload when dirty. `00670510` locks, copies the bytes
   unchanged, unlocks and clears dirty state; no RGB arithmetic occurs here.
5. `00432720` binds mesh and instance streams through `006677E0`.
   `006622D0` selects the cached group branch when its pointer is non-null;
   `006688C0` applies `006696B0` material states before `00668850` draws.
6. `006687F0` and `0066C250` fill/upload **index** buffers, not color buffers.

This resolves stored color correspondence and the static upload. It does not
capture active runtime selection, subsequent state overrides or all shader
inputs. The previous balcony MODULATE2X experiment remains opt-in.

Evidence: local `reports/balcony-cache-20261029*` directories; original executable
SHA-256 `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
Decompiler output remains in ignored reports, outside implementation source.

## Texture completeness

The current source report has **39 decoded material entries; 36 are submitted**.
All 38 submitted image files match their recorded SHA-256; the runtime package
also matches its manifest hash. A material entry/image existing on disk does
not imply a draw or visible coverage.

| Source slot | Material / texture key | Missing objects | Reason |
| --- | --- | --- | --- |
| 32 | 30000D1B / 68000DAC | 2100_ciel_nuit_lune.gao (30000D1D) | Scaled matrix rejected |
| 36 | 30000D90 / 30000C67 | Menu3D_Bird_Fake, Fake2, Fake3 | Scaled matrices rejected |
| 37 | 2E005242 / 2E005240 | Menu3D_GFX_Mouches, Mouches2 | Scaled matrices rejected |

`Menu3D_sky.gao` (30000CC4) is also excluded for its scaled matrix, although its
material pack is shared with rendered objects. Therefore counting unused
materials alone does not detect every missing object. Other exclusions include
unsupported geometry, nonzero slots on a leaf material and non-mesh GAOs; the
JSON report preserves them with names and resolvable material links.

The moon scale is approximately (0.5011184,0.5011184,0.5011184); sky scale is
(1,1,1.5159291). Local-axis scale was already understood for selected objects,
but those two keys were not admitted by the assembler's bounded allowlist.
The moon's flags 0x00014607 require source-over, no depth writes and local alpha
(the rotation/alpha word is 0x80000000). Simply adding its triangles to the
current opaque fallback would not reproduce its material. Restoring these
objects must include their material states and transparency ordering.

This audit covers the decoded menu/export dependencies. It does not claim that
all resources required by the original runtime have been decoded or displayed.

## Fog attenuation over the balcony

A CPU ray diagnostic reads the actual OJSCN003 vertices, camera, draw states and
texture pixels. At 800x600, initial Camera02, FOV 59.37908, phase zero, it samples
pixel centers on an 8-pixel grid spanning x=240..400 and y=120..280.
It selects the nearest opaque surface passing the base-level linear alpha test,
then tests the three fog panels in front of it. This is not a full GPU rasterizer:
fixture transparency contributions, rasterization edge rules and original-game
state are outside the probe. Shared triangle edges are excluded from sampling.

- 175 samples hit a visible balcony surface.
- 59 intersect a fog panel in front; 116 do not.
- Background transmission `product(1 - texture_alpha)` ranges from
  0.7896303 to 1.0: at most about 21% attenuation at these samples.
- At x=328, sampled balcony points y=160,168,176,184,224,232 have no foreground
  fog intersection. These are viewport coordinates, excluding window chrome.

Thus the current three panels do not veil much of the balcony. This is a
measured property of our exported scene, not proof that the original should
use denser fog or a global fog term. Confirm panel phase, coverage and any
additional original fog state before changing opacity or adding a global veil.

## Moon and global lighting

The raw menu contains **19 objects whose names include `_LUM_`**, including
LUM_Lune, LUM_Ambiant, LUM_Fog, LUM_Fog_BG and secondary LUM_Radio lights.
They are not implemented as dynamic lights by the Vulkan viewer. Their names
do not establish active contribution, type, intensity or attenuation.

The visible moon image and LUM_Lune are separate resources. Adding the moon
image does not itself illuminate other meshes. Conversely, absent runtime
lights do not prove all their contribution is missing: the balcony and tested
tree have recorded instance colors and flag 0x40; `00432600` can select those
colors and clear the dynamic-light-enable bit, while `00432720` gates light
accumulation on that bit. Adding every named light could count baked lighting
twice. Active flags and per-object light selection still need verification.

## Reproduce and validate

```powershell
python src/audit_menu_completeness.py reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin reports/menu-fixture-materials-20261025/renders/horizontal-angle reports/engine-textures-20261028 reports/menu-completeness-20261029/audit.json
python -m unittest discover -s tests -p test_menu_completeness.py
```

Requires NumPy and Pillow. Output must not exist. Frozen source hash:
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
Four synthetic tests cover BGRA correspondence with reused indices, rejected
halved colors, independent geometry/UV mismatches and invalid cached indices.
The real-data audit additionally validates cached extents, group mapping,
resource/package/image hashes and full corner correspondence.

No rendering default, camera, light or fog opacity was changed by this audit.
Priority: restore the scaled sky/moon with their actual material states, then
compare fixed-pose captures before changing global lighting or fog.
