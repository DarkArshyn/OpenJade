# Fog lifecycle and cursor alpha tracks (2026-11-05)

## Evidence and scope

This follows [isolated cursor and fog draws](2026-11-05-cursor-dynamic-fog.md). A read-only resource analysis and an in-memory probe of the research GOG copy recorded two fog emitters, before/after callback states, emission RNG outputs, draw vertices and cursor alphas. No runtime rendering or lighting was changed. The executable and frozen scene hashes are those in the preceding report.

Local evidence is in `reports/fog-life-evidence-20261105/fog-life-captures.zip`. The probe observes the type-11 callback at 00431D30 and the emission routine at 0042EE80. The native update at 004307F0 corroborates the phase-transition arithmetic. The research configuration retained ForceVSFog=1 and InvertFogRange=1 for this state/vertex capture. The measurements below precede depth fog and framebuffer blending. They do not measure final image brightness.

## Birth and motion

Both Menu3D_Fog3D (30000D26) and Menu3D_Fog3D2 (30000D28) use descriptor 30000D27. Ten captured CRT outputs per birth reproduce the initial duration, two sizes, local X/Z rectangle coordinates, two velocity angles, speed, initial angle and spin. The native matrix transforms position and velocity. Zero acceleration leaves velocity constant during the observed lifetime.

| Check | Fog3D | Fog3D2 |
| --- | ---: | ---: |
| Births replayed | 54 | 50 |
| Same-phase motion/timer updates | 44,569 | 44,627 |
| Observed initial-to-main transitions | 45 | 44 |
| Observed main-to-end transitions | 39 | 34 |
| Removed particles | 35 | 31 |

Birth duration and size match exactly. Maximum birth position component error is 8.92e-6 world units and velocity error is 4.54e-8. The birth position comparison uses an independent matrix calculation with different intermediate precision.

The motion step is float32 bit pattern `3c88893b`, approximately 0.016667 engine seconds. The number of steps is the truncated value of 60 times the float32 sum of the incoming delta and previous remainder. The remainder carries forward. Repeating the native float32 position addition for every step matches captured positions exactly on the 89,196 same-phase updates. Their remaining timers also match exactly.

Packed rotation advances once per callback, including callbacks with no motion step. The increment is the low 15-bit spin magnitude shifted left by 16, added or subtracted according to bit 15, with 32-bit wraparound. All compared surviving particles match this rotation update.

## Phases and appearance

Stored duration ranges are initial [1.464100,3.664390], main [1.762385,6.466816], and end with endpoints (2.121439,0). The descending end endpoints are intentional input to `start + random * (end-start)` and must not be reordered. A phase changes when its remaining timer is strictly less than the elapsed quantized time. The new duration replaces the old timer, then the full elapsed interval is subtracted. A sufficiently short end duration can lead to removal in the same callback that leaves the main phase.

The observed transitions follow initial -> main -> end -> removal. The new phase timer agrees with the duration reconstructed from its stored reciprocal to within 4.77e-7. Transition RNG calls were not captured in this run, so their exact random draws are not independently replayed. The emission RNG replay is exact in draw count and verifies births separately. Trailing state records copied after the last complete callback capture are excluded from the comparison.

The four native RGBA color endpoints are (113,149,171,0), (136,172,194,48), (123,148,162,12), and (161,179,197,0). Initial phase interpolates toward the main-start endpoint, main phase toward the main-end endpoint, and end phase toward transparent. Interpolation uses the previously verified packed-byte routine, not ordinary independent floating-point channel interpolation.

Crucially, these fog quads retain their sampled sizes in the initial phase. Their appearance is controlled by color/alpha, without the initial size growth used by some other particle modes. Their camera-facing axes rotate with the packed angle. The native cosine lookup uses `(index+256)%1023` while the sine uses the 1024-entry table.

Across 204 native draws, 1,355 initial, 1,795 main and 408 end-phase particle observations produce 21,348 submitted corners. All UVs and packed RGBA values match exactly. Maximum corner component error is 7.59e-6 world units after retaining the initial size.

## Cursor transparency is an MGM animation

The C_Default cursor in `POPData-extracted/menu/pop4common.mgm` contains two IMAGE children and a FRAMERATE of 10. Both use Linear keyframes and GotoFrame 0 at frame 60.

| Animation frame | Base texture alpha | test.dds alpha |
| --- | ---: | ---: |
| 0 | 255 | 255 |
| 25 | 250 | 50 |
| 50 | 255 | 255 |
| 60 | 255 | 255, then return to frame 0 |

Let f be the cursor animation frame. Define w=f/25 for 0<=f<25, w=(50-f)/25 for 25<=f<50, and w=0 for 50<=f<60. Before integer quantization, the base alpha is 255-5w and the halo alpha is 255-205w. The nominal cycle is six engine seconds, including a one-second plateau. Each pass multiplies this alpha by its texture alpha before the source-over blend already verified in the preceding report. MGM image bounds are 35x35 in the package's 640x480 space.

Replaying the MGM tracks against 2,488 captured pairs gives a maximum error of one alpha level for each pass. The replay uses captured frame deltas and resets the phase at the observed activation restart at probe frame 341. That restart is aligned from the measured discontinuity, not predicted from recovered menu activation logic. Periodic GotoFrame resets discard the overshoot in this reference. Exact native timer/quantization order remains to be resolved before claiming byte-exact alpha reproduction. The source keyframes and large halo amplitude explain the observed pulsing without inventing a sinusoidal light.

## Reproduce and next integration

Extract the local archive and run from the repository root:

```powershell
python tests/integration_fog_cursor_lifecycle.py <fog-life-directory> <FF000CB9-decoded/decoded.bin> <prepared-menu.ojscene> <POPData-extracted/menu/pop4common.mgm>
```

The check passes on the captured dataset. Use the prepared fixed-menu scene from `reports/menu-vegetation-20261104` for its validated camera axes. The original files are opened read only.

The verified lifecycle and constant-size appearance provide the next fog integration reference. Preserve the existing panels, add both native emitter transforms and source-over draws, and validate vertex fog and draw ordering before reassessing lighting. Cursor integration should export both MGM tracks and textures. Exact transition RNG replay and byte-level cursor timing remain bounded follow-up checks. Neither effect has been added to Vulkan by this research change.
