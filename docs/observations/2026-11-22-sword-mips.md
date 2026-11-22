# Native sword mipmaps

Date: 2026-11-22

## Measurement

A fresh readback from the GOG research copy captured each level of both bound sword
textures. All surface, render-target and copy calls succeeded. Every RGBA pixel
matches the original resource after the measured storage-to-GPU extent selection.

| Resource | Stored levels | GPU levels |
| --- | --- | --- |
| 13006B64, base | 128x64, 64x32, 32x16, 16x8, 8x8 | 128x64, 64x32, 32x16, 16x8, 8x4 |
| 2E011834, reflection | 32x32, 16x16, 8x8 | 32x32, 16x16, 8x8 |

For the final base level, the first four rows of the stored 8x8 block exactly match
the 8x4 GPU level. No resize or averaging is needed. This is verified for this
resource only; do not generalize the rule to unmeasured formats.

The reflection sampler still disables mip sampling, so its runtime use remains
LOD zero. The base sampler uses native linear min/mag and linear mip filtering.

## Runtime

The animated exporter now writes a bounded `OJSWMP01` sidecar for the original five
base levels. The menu assembler offsets its texture binding. Vulkan uploads these
levels directly, preserving 128x64 through 8x4 dimensions and selecting trilinear
sampling for the corresponding linear material binding. Other actor textures
retain their existing behavior.

The reader validates exact extent, texture dimensions, level count and base-image
equality with the scene package. Older packages without this sidecar remain valid.
No source game files or historical engine sources were modified or used as code.

## Validation

    python tests/integration_sword_mips.py CAPTURE_DIRECTORY SOURCE_MANIFEST

The test reports eight exact original-resource/native-readback matches and hashes
each capture. Private capture: `sword-mips-20261122` in the working research directory.
The research proxy was restored to SHA-256
`e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`.

- Rust workspace: 78 ordinary tests pass; 15 private-data tests ignored by default.
- Reader tests reject truncation, trailing data, incorrect dimensions and mismatched base pixels.
- Three fixed-time endpoint-camera comparisons are reproducible with no Vulkan errors.
- Mips on/off changes 245, 133 and 201 final pixels at actor times 0, 2 and
  3.983333 seconds; maximum channel changes are 32, 109 and 34 (8-bit scale).
  The reflection remains enabled in both sides of each comparison.
- These differences do not demonstrate whole-image parity with GOG.

Four sequential FIFO runs, 1,800 frames each, 30 warm-up frames excluded, Windows
and Radeon RX 9070 XT:

| Run | Native mips | Frame median / p95 ms | GPU median / p95 ms |
| --- | --- | --- | --- |
| 1 | Off | 5.683 / 11.630 | 0.333 / 0.354 |
| 2 | On | 5.716 / 11.477 | 0.332 / 0.356 |
| 3 | On | 5.653 / 11.489 | 0.330 / 0.352 |
| 4 | Off | 5.698 / 11.369 | 0.332 / 0.354 |

Zero validation errors across 7,200 frames. CPU simulation medians vary from 0.962
to 1.256 ms across the runs; these measurements are not proof of statistical
performance equivalence.

Prepared scene: `reports/menu-prince-mips-20261122/menu.ojscene`.
The native UI bundle remains `reports/menu-fixtures-20261110/ui/menu.ojui`.


## Remaining investigation

The material-index selection uncertainty for sword slots 2 and 4 was resolved
in a subsequent investigation conducted on 2026-11-22.
Both requested indices select the last available entry (index 1) in the
original two-entry material pack. See
[sword material-pack selection](2026-11-22-sword-material-selection.md)
for native evidence, implementation details and validation limits.

Full GOG image parity and mip-chain validation for other actor textures remain
separate tasks. The native base mip-chain uncertainty documented in the older
[sword reflection integration](2026-11-17-sword-vulkan.md) is resolved
specifically for resource `13006B64`.
