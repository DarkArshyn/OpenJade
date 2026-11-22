# Prince fixed-menu lights from original resources

Date: 2026-11-17

## Result and scope

Menu assembly now prepares the ambient color and three named lights directly from
the original scene. Animated normals continue to be evaluated by the existing Rust
renderer. The generated directional contribution (six floats) remains captured;
this is not a general runtime light graph or validated Camera02 lighting behavior.
Scenery lighting, materials, geometry and collision placement are unchanged.

## Source and native comparison

Original scene SHA-256: `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
The existing `light-ablation2` same-process registry resolves descriptors to the
following original keys; each GAO's final reference independently matches that key.
The ambient binding was established in the [initial cache investigation](2026-11-13-ambient-cache-shaders.md).

| Object | GAO | Descriptor | Source interpretation |
| --- | --- | --- | --- |
| Menu3D_LUM_Lune | 30000CE2 | 30000CE6 | Positive second basis row, RGB |
| Menu3D_LUM_Radio_Room | 30000CF4 | 30000D55 | Translation, RGB, inner/outer ranges |
| Menu3D_LUM_brasero | 30000D57 | 30000D58 | Translation, RGB, inner/outer ranges |
| Menu3D_LUM_Ambiant | 30000CE4 | 30000CE8 | RGB |

For these version-10 GAOs, the matrix begins at name length +30; the payload
extent is name length +148. Version-9 light descriptors have 36 bytes, packed
low-byte-first RGB at +12, inner/outer float ranges at +16/+20. Attenuation is
`clamp((outer-distance)/(outer-inner), 0, 1)`. This targeted reader does not infer
arbitrary descriptor flags, parent hierarchies or automatic receiver selection.

`tests/integration_prince_scene_lights.py` compares source terms with the existing
`light-terms3` evidence: 121 receiver samples, 506 draws, eleven components.
Captured coordinate matrices are used only by this comparison, not as the light
parameter source. The captured inverse matrix stores zero in its unused bottom-right
lane; the test reconstructs affine W=1 before composing point transforms.

| Quantity | Maximum absolute component error |
| --- | --- |
| Moon direction | 1.451e-7 |
| Point-light position | 1.816e-6 |
| RGB | 3.647e-8 |
| Attenuation parameters | 2.109e-8 |

This compares source-derived parameters to native GPU constants, not final pixels.
The private report retains resource hashes and byte offsets. No original assets or
native implementation code are distributed.

## Integration and validation

`src/prince_scene_lights.py` converts source world terms into the grounded actor's
local coordinates. `assemble_prince_balcony.py` replaces 25 of the 31 lighting
parameters while preserving the generated direction/color and all normal records.
Three synthetic tests cover conversion, changed resource ranges and rejected input.
All other `menu.*` files are byte-identical to the preceding grounded package.

Three Vulkan captures at 2, 3.983333 and 4 seconds have identical repeated fixed-time
frames and zero validation errors. This verifies repeatability, not original-game
pixel parity. The balcony's bright curtains and complete material fidelity remain
unresolved.

The 800x600 balcony endpoint run used FIFO, validation and 1,800 presented frames,
with 30 warmup frames excluded. Frame interval median/p95: 5.661/11.238 ms;
simulation: 0.711/0.914 ms; GPU commands: 0.310/0.325 ms. Zero validation errors.
The preceding grounded run measured 5.653/11.239 ms frame intervals and
0.314/0.335 ms GPU commands. These single runs show similar timings, not statistical
proof of equivalent performance. No new per-frame calculation was introduced.

## Reproduction

```powershell
python tests/test_prince_scene_lights.py
python tests/integration_prince_scene_lights.py <Menu3D-decoded.bin> <light-terms3> <output-directory>
cd engine
cargo run -p jade-viewer -- --scene ../reports/menu-prince-source-lights-20261117/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

The viewer command requires the local prepared package. Earlier exports are not
modified automatically. Next: measure the generated directional term and effective
light selection during Camera02 before replacing that remaining captured term.

## Camera02 follow-up

The [transition capture](2026-11-17-camera02-generated-light.md) verifies the generated direction and GPU transfer during the zoom. The runtime still retains its frozen captured term.
