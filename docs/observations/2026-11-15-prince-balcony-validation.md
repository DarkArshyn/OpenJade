# Prince balcony pose and loop validation (2026-11-15)

## Scope

This validation uses the prepared balcony package and the decoded Camera02 endpoint
at nine seconds. It does not compare a synchronized original-game frame or validate
the whole camera transition. Original game data remains read-only.

`tests/integration_prince_balcony_poses.py` captures 0, 1, 2, 3.983333 and 4 seconds.
For each fixed time, frames 11 and 21 are byte-identical and no Vulkan validation
error is reported. The Prince is visible on the balcony in the inspected two-second
and pre-wrap captures. Scene foreground tests alone do not prove actor visibility,
correct ground contact, correct materials or original-game pixel parity.

Private results are in `reports/prince-balcony-validation-20261115`:
`validation.json`, individual captures, `frame-timing.txt` and `continuity.txt`.

## Confirmed loop discontinuity

Update: the subsequent [native controller capture](2026-11-15-prince-sheath-loop.md)
establishes state retention at three observed loops and corrects the reset described
below. The figures in this section record the pre-correction diagnostic.

`actor_continuity` measures the Euclidean displacement of every expanded vertex
between two local animation times. Units are original scene units, not asserted
meters. RMS is computed across expanded vertices and therefore includes duplicates.

| Interval | Maximum with sheath | Maximum without sheath |
| --- | --- | --- |
| 0 to 1/60 s | 0.002584472 | 0.000418016 |
| 2 to 2+1/60 s | 0.009652749 | 0.000732664 |
| 3.983333 to 4 s | 0.325070918 | 0.000737824 |
| 3.999990 to 4 s | 0.325568408 | 0.000000485 |

The maximum discontinuity is expanded vertex 3794, within the draw range 3378..5265
of `M_Prince_Legs.gao`. Its sole exported influence is bone `130035EE`, weight
1.0000026226043701 (the existing packed-weight interpretation is retained).
The original skeleton names that bone `B_Pr_Mod_Sheath_Dagger.gao`; its child is
snap `130046A1`. Thus the mesh name alone does not mean that a leg articulation
causes the discontinuity: this vertex follows the sheath controller.

The body-only result approaches zero as the interval shrinks. With the controller,
the finite jump remains. The diagnostic explicitly resets the controller to rest
at each four-second body loop. The cached evaluator was previously checked against
the uncached replay, so this is an existing diagnostic reset discontinuity, not a
new cache or frame-rate regression. It can look like an animation jerk even when
frame delivery is fast.

No smoothing, changed source parameters, altered body keys or guessed grounding
offset is introduced. Native cross-loop controller behavior is not established by
the existing one-step capture comparisons. The next targeted check should capture
the native state across the body-loop/action boundary, then determine whether to
carry controller state across the loop and when the game actually resets it.
The current four-second repeat policy must not be marked fully validated.

## Performance reference

A separate live run (no fixed time and no screenshot layer) renders 600 frames at
800x600, FIFO, legacy-unorm, validation enabled, AMD Radeon RX 9070 XT. Warmup and
sampling use the existing bounded profiler. This endpoint-camera scene has no UI;
it must not be compared as identical workload to the 1600x1200 full-menu run.

| Metric | Median | p95 |
| --- | --- | --- |
| Frame interval | 5.607 ms | 11.294 ms |
| Simulation | 0.663 ms | 0.809 ms |
| Upload and recording | 1.813 ms | 2.000 ms |
| GPU commands | 0.311 ms | 0.331 ms |

No Vulkan validation errors. These timings are a reproducible local reference,
not hardware-independent thresholds or display-scanout measurements. Future
integrations should rerun the same workload and retain median/p95 measurements.

## Reproduction

```powershell
python tests/integration_prince_balcony_poses.py reports/menu-prince-20261115/balcony-preview/menu.ojscene reports/prince-balcony-validation-new
cd engine
cargo run -p jade-assets --example actor_continuity -- ../reports/prince-sheath-animation-20261114/prince.actor
```

The output directory must be new. The first command requires the local Vulkan
screenshot layer and prepared private assets. No resources or screenshots are
published with the test. Ground placement remains unresolved (native/source Z
difference about 0.014345), along with source-loaded lighting, sword reflections,
other procedural controllers and native action selection.
