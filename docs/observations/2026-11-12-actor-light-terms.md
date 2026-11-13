# Actor ambient color and generated directional light

Date: 2026-11-12

## Scope

Follow-up to the [GPU contribution measurements](2026-11-11-menu-light-contributions.md). This investigation identifies the immediate producer of c25 and numerically checks the additional directional light through its GPU transfer. It does not change Vulkan rendering, introduce actor geometry, or retune scenery lighting.

Evidence comes from the local GOG research copy (executable SHA-256 `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`), read-only native inspection, and `light-terms3` captures. The original installation is unchanged. Decompiled code and original assets remain outside Git.

## c25: immediate source and remaining provenance limit

The verified transfer is:

1. The owning render instance points at its private lighting structure through `+0x70`.
2. `00432720` copies the packed color at that structure's `+0x44` into render context `+0x850` on the private-list path.
3. When enabling the GPU lighting path, `00668280` converts that context color to normalized RGB in the constant buffer at byte offset `0x190`, forcing W to one.
4. `00667B00` uploads the block beginning at register 25; the draw-time capture verifies c25.

For all 121 receiver samples, both cache and context contain `FF3B2E25`: RGB `(37,46,59)` in the engine's low-byte-first channel order. All 506 sampled draws carry `(37,46,59)/255, W=1` in c25. The maximum conversion discrepancy against mathematical division is `1.602e-8`, consistent with float storage. This is an ambient color term separate from the three selected lights and the generated fourth direction.

Upstream, `00444410` writes private `+0x44` from the packed result of `00443730`, with the high byte forced to FF. An inheritance branch can instead copy the full private structure from another object. `00443730` handles an ambient source or cached color and a position-dependent transition. This inspection does not establish which earlier branch initialized every captured cache.

The scene contains `Menu3D_LUM_Ambiant.gao` (`30000CE4`), referencing descriptor `30000CE8`, whose color at payload `+0x0C` is `003B2E25`. That matches c25's RGB. However, the owning instance's direct ambient-source field `+0x74` is null in all 121 samples. Its cached ambient field `+0x60` contains the matching RGB in 99 samples and zero in 22, while the private cache remains nonzero in all 121. Therefore the named source is a supported candidate, not a proven causal binding. Capture the earlier ambient resolution/cache construction to establish that final link; do not substitute color equality for provenance.

## Generated direction

`00444A60` prepares a vector from the owner's translation relative to the render-context reference position, normalizes it, and passes it to `00444270`. The generated-light path is enabled by private-list flags at `+0x36` bit 1. It is separate from the three-entry selected list.

The native globals measured in the executable and at runtime are:

| Parameter | Address | Value |
| --- | --- | --- |
| Azimuth offset | `007F27CC` | float32 pi, `3.1415927410125732` |
| Polar angle | `007F27D0` | `0.30000001192092896` radians |
| Packed color | `007F27D4` | `40404040` (RGB 64,64,64) |

For the captured positive polar angle, the normalized direction is reproduced by:

```text
x_safe = x, or 1e-7 when x == 0
azimuth = atan(y / x_safe) + (pi when x < 0, otherwise 0) + azimuth_offset
direction = (sin(polar) * cos(azimuth),
             sin(polar) * sin(azimuth),
             cos(polar))
```

The native sequence computes cosine and sine, derives a positive Z through a square root, then normalizes. The expression above is a mathematical reduction for the measured default angle, not bit-exact emulation or a verified rule for arbitrary angle signs. Native intermediate float stores explain small rounding differences. The input vector's Z is not used by the angle calculation. At this setting the output Z is approximately `0.9553365`; the horizontal magnitude is approximately `0.2955202`.

Ghidra assigned the ambiguous library name `FID_conflict__cos` to `00729630`. Direct native evaluations at 0, 0.25, 0.5 and 1 instead match **atan**. Equivalent checks identify `00729404` as cos, `007294B4` as sin and `00729764` as sqrt. All 16 checks agree with the corresponding host math results for those inputs. These samples and the instruction sequence support the interpretation; the automatically assigned name alone did not.

## Transfer and validation

The world direction is transformed into receiver-local space using the captured inverse matrix at `A6DE58`. The GPU upload then applies the matrix at render state `AE1790 + 0x20` and normalizes the vector. Row-vector multiplication with the captured matrix layout reproduces both steps; interpreting that layout with the opposite multiplication order does not.

Slot 3 uses direction register **c39**, W=0, and color register **c40**, RGB `(64,64,64)/255`, W=1. `00660380` explicitly sets ECX to the render-state address `AE1790` before calling `006683A0`; ECX on entry to `00660380` is not the render-state pointer.

| Check | Samples | Maximum absolute component error |
| --- | --- | --- |
| Closed-form direction vs native `00444270` output | 121 | `1.574e-7` |
| World-to-local direction | 121 | `2.958e-8` |
| Local-to-GPU direction vs c39 | 506 draws | `1.024e-7` |
| Private ambient cache vs c25 | 506 draws | `1.602e-8` |

The capture covers eleven components at frames 0 through 120, every 12 frames. Mesh identities are checked against same-session load bindings. This validates the measured fixed-menu pose and its sampled animation updates; it does not validate all camera positions, degenerate horizontal input vectors, arbitrary settings, final shader color equations or final displayed pixels.

The first `light-terms` probe read the wrong GPU context address and stopped the research process. Its partial results are excluded. `light-terms2` completed after the address correction; `light-terms3` repeated the measurement with additional ambient provenance fields and is the evidence used here. The saved proxy was restored after every run, with final SHA-256 `e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`. The earlier ablation's incoming-register preservation remains harmless, but the native code now shows that preserving ECX is not needed to provide the context to `006683A0`.

## Reproduction

```powershell
python tests/integration_actor_light_terms.py <light-terms3>
```

The read-only check requires NumPy. It validates record sizes and coverage, eleven mesh keys, math-function samples, ambient equality, GPU constants and both transformations. It emits the maximum errors, per-sample directions and SHA-256 hashes for the captured binary evidence. The checked output is stored locally as `light-terms3/verified-terms.json`.

## Next bounded step

Trace ambient resolution during initial private-cache construction to prove the named ambient source and inheritance. Then inspect the actual vertex-shader combination of normals, these light terms and material colors before implementing actor lighting. This result does not justify applying actor lighting to scenery already rendered with cached colors.

## Follow-up: November 13

The [initial-cache and shader capture](2026-11-13-ambient-cache-shaders.md) now resolves the previously open named ambient-source link through the balcony fallback and verifies the captured lighting arithmetic and distinct material paths.
