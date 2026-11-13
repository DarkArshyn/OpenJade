# Effective menu light contributions on Prince components

Date: 2026-11-11

## Scope and method

This follows the [receiver identification](2026-11-11-menu-light-receivers.md). It measures color-target changes on the eleven identified Prince/equipment components in the fixed menu pose, using the local GOG research copy. No runtime lighting change is made, and the original installation and resource bytes remain unmodified.

The `light-ablation2` probe preserves the register state, including ECX, when observing the GPU upload entry at `00660380`. An earlier experimental ablation used an ordinary C wrapper at this entry; that experiment is excluded from the results below. Native inspection establishes the path `00444A60 -> 00660380 -> 006683A0`. The CPU color-accumulation hooks produced no records in the measured configuration.

At captured frame 120, the probe replays each eligible draw from the same saved color target and unchanged depth buffer. Depth testing remains active; depth writes are disabled for the replay only. Afterward it restores the target, constants and depth-write state, and lets the original draw execute normally. Stencil-enabled or multisampled draws are excluded by the probe.

Eight variants are recorded: baseline; zero RGB in each of `c28`, `c32`, `c36`, `c40`, `c25` individually; repeated baseline; and zero RGB in `c28/c32/c36` together. W components are preserved. This tests the effect of the transmitted color constants while retaining the original shader, geometry, textures, transforms, attenuation, depth test and blending.

## Light selection and GPU transfer

There are 132 sampled receiver calls across frames 0 through 132 at intervals of 12, with 528 GPU slot uploads. Each receiver has the same three-entry private list. Resource identities are resolved through native load bindings in this same process, not through pointer equality with an earlier run.

| Slot | Source GAO / key | GPU kind | Color register | Captured RGB, byte scale |
| --- | --- | --- | --- | --- |
| 0 | `Menu3D_LUM_Lune.gao`, `30000CE2` | 1 | `c28` | 99, 134, 169 |
| 1 | `Menu3D_LUM_Radio_Room.gao`, `30000CF4` | 3 | `c32` | 189, 128, 68 |
| 2 | `Menu3D_LUM_brasero.gao`, `30000D57` | 3 | `c36` | 189, 128, 68 |
| 3 | Generated directional contribution; no selected GAO | 1 | `c40` | 64, 64, 64 |

The previously shortened room-light name is `Menu3D_LUM_Radio_Room.gao` in the actual resource. The capture verifies that all four RGB triples reach the draw-time shader constants as channels divided by 255, with W = 1.

The fourth slot is not a fourth entry in the selected list. The tail of `00444A60`, gated by private-list flags at `+0x36` bit 1, computes a direction using the owning object's translation relative to context coordinates `+0x184..+0x18C`. It calls `00444270`, transforms the direction, constructs a temporary descriptor, and submits another kind-1 light. `00444270` obtains its color from `007F27D4`; the captured packed effective color is `40404040`. The temporary descriptor has a stack address, not a resource identity. Its complete directional equation has not been independently replayed here.

The separate `c25` constant is `(37, 46, 59)/255` in these draws. Its ablation also changes pixels. Its producer and full semantic role are not resolved by this experiment, so it is not attributed to one of the three named lights.

## Measured RGB differences

Twenty-four 800x600 draws cover all eleven receivers. All 192 replay draw calls report success; all 192 BGRA readbacks have the expected size. The repeated baseline is byte-identical for every draw. Another 22 replay records target 256x256 surfaces and have no supported BGRA readback in this probe; they are excluded, not counted as zero contribution.

Each entry below is the maximum absolute difference in an 8-bit RGB channel over the component's measured draws when the indicated constant is neutralized. It is not a percentage of illumination. Multiple passes can revisit the same pixel, and the columns must not be added together.

| Component | Draws | Moon | Room | Brasero | Generated slot 3 | c25 | Three named lights together |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Prince_Sword01.gao` | 3 | 20 | 7 | 21 | 9 | 14 | 40 |
| `Prince_Dagger.gao` | 2 | 15 | 7 | 8 | 7 | 25 | 19 |
| `Prince_Holder_Body.gao` | 1 | 14 | 11 | 0 | 3 | 8 | 24 |
| `M_Pr_Face.gao` | 1 | 5 | 3 | 23 | 11 | 11 | 27 |
| `M_Prince_Plate_Body.gao` | 2 | 24 | 8 | 32 | 7 | 11 | 43 |
| `M_Prince_Legs.gao` | 7 | 44 | 6 | 29 | 13 | 22 | 48 |
| `M_Prince_Veil.gao` | 2 | 8 | 4 | 18 | 6 | 8 | 26 |
| `M_Prince_Plate_Shoulder_Left.gao` | 1 | 5 | 0 | 8 | 7 | 11 | 12 |
| `M_Prince_Sleeve_Left.gao` | 2 | 17 | 6 | 13 | 12 | 12 | 20 |
| `M_Prince_Plate_Shoulder_Right.gao` | 1 | 6 | 0 | 14 | 6 | 7 | 19 |
| `M_Prince_Sleeve_Right.gao` | 2 | 20 | 2 | 23 | 10 | 9 | 31 |

Thus the moon has a measurable effect on all eleven components; the room light on nine; the brasero on ten. No RGB change is measurable for the room light on either shoulder plate, or for the brasero on the holder body, at this pose and resolution. The generated slot and c25 each have a measurable effect on all eleven components.

These are per-draw color-target measurements before subsequent scene/postprocessing passes. They do not establish the final displayed contribution after occlusion, fog and composition. A zero can result from orientation, attenuation, occlusion or quantization; it does not establish that a selected light is globally inactive. No claim is made about other poses, the balcony zoom, or unrelated scenery.

## Reproduction and evidence

`tests/integration_light_contributions.py` validates same-session mesh/GAO bindings, component labels and vertex counts, all three selected identities, the four-slot upload sequence, packed-to-float color transfer, successful replay calls, readback sizes, repeated baselines and the difference measurements. It reads local evidence and original decoded resources without changing them.

```powershell
python tests/integration_light_contributions.py <light-ablation2> <Prince-decoded.bin> <PrinceCostume01-decoded.bin> <Prince_Weapons-decoded.bin> <Menu3D-decoded.bin>
```

Private evidence: `light-ablation2/verified-contributions.json`, `light-ablation2-selected.txt`, `light-ablation2-slots.bin`, `light-ablation2-registry.bin`, receiver/replay text records, and `mask-120-*-light-ablation2-v*.bgra`. The JSON contains input resource SHA-256 values and per-draw pixel counts, signed RGB delta sums and affected bounds. Native inspection files remain private; neither original assets nor decompiled code are added to Git.

- GOG executable SHA-256: `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
- Probe source SHA-256: `01ff4d7deb17e701c9fef2e0968ffbe59f57bbc0e5c01563bd525d89ebd798f8`.
- The research process ended and the saved proxy was restored, verified by SHA-256 `e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`.

## Runtime consequence

Implementing the Prince's lighting will require the three selected lights, the generated directional contribution, and the remaining constant/material terms. This result does not justify brightening the cached-color scenery or changing global illumination. The next bounded investigation is the producer of c25 and the exact generated direction/shader combination before introducing this actor lighting in Vulkan.

## Follow-up

The [November 12 investigation](2026-11-12-actor-light-terms.md) identifies the immediate c25 producer and verifies the generated direction and its GPU transfer numerically. Ambient-source initialization and the complete shader combination remain open.
