# Live menu rain state (2026-11-03)

Follow-up to [controlled spawn and matrix checks](2026-11-03-rain-spawn-life-transform.md).

## Observation method and limits

A local D3D9 proxy in the isolated GOG research copy observes the registered
particle callback `00431D30` through table slot `00A6EA38`. The wrapper logs
state before and after calling the original callback, without changing particle
parameters. It identifies rain descriptors by count 150 and emission rate 50,
then matches their matrices against the two frozen menu records. D3D9 draw
observations are scoped to the corresponding callback, not inferred from a
texture name. Frames 20-22 follow the established menu-geometry readiness marker.

Two short runs completed. The capture launcher restores the copied Hardware.ini
and previous proxy bytes in a finally block. The original installation is not
modified. The copied Hardware.ini uses InvertFogRange=0. The probe adds CPU/file
logging overhead; measured dt and population are not performance benchmarks.
Evidence and independent probe source remain in ignored `reports/rain-live-20261103`.

## Effective emitter transforms

All 24 before/after observations in the second capture match exactly one of
`2E00E1AD` (Rain01) and `2E00E1AF` (Rain02), within 1e-6 for printed matrix floats.
Each has one context, capacity 150, selector +0x40=0 and link +0x94=0.
Therefore the native branch actually uses GAO +0x0C, not the identity matrix
stored in the context. Both live GAO matrices agree with the stored menu matrices.
This closes the earlier live-transform uncertainty for this fixed menu sample.
It does not establish that matrices never change in other scenes or transitions.

## Live update checks

Six before/after callback pairs advance the simulation across three frames and
two emitters. Other callback invocations in the same frame leave the accumulators
unchanged, consistent with the native frame guard. The second run has 12-13 live
particles per emitter, not 150 continuously active particles.

For each advancing pair, the emission and simulation remainders match the recovered
rate-50 and rate-60 formulas within 1e-7 of the printed values. Birth requests are
0, 0, 1 for frames 20, 21, 22 on both emitters. Simulation steps are 1, 0, 1.
The population increase matches the birth request in this short sample; no deaths
were observed here. Lifetime transition validation remains the separate controlled
native test, not an inference from these three frames.

## Observed draw state

Each rain draw binds the same 32x32 A8R8G8B8 texture in this capture. Dimensions and
binding identity are verified, but pixels were not read back to prove resource-key
identity. The descriptor still references the independently decoded rain texture.

| D3D9 state | Observed value |
| --- | --- |
| Alpha blending | Enabled |
| Source / destination | SRC_ALPHA / ONE |
| Depth test / write | Enabled / disabled |
| Alpha test | Disabled; stale alpha-reference values have no effect |
| Fixed-function fog | Disabled; this alone does not exclude shader fog |
| Color writes | RGB only, no alpha-mask write |

The first draws have 24 triangles for 12 live particles, consistent with two
triangles per particle. This establishes additive rain drawing rather than
source-over blending. It contributes to scene RGB before postprocessing but does
not directly fill the scene-alpha glow mask in the observed draws.

## Next integration boundary

Matrices, native parameters, spawn math, timer transitions, movement and core
blend/depth state now have evidence. Before faithful Vulkan rendering, decode or
capture generated particle corners/UVs and per-vertex colors/alpha, including their
phase dependence and any shader fog. Shared random-stream phase is still not
synchronized with GOG. No rain rendering is added by this observation step.
