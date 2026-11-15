# Prince diagnostic CPU performance (2026-11-15)

## Finding and scope

The sheath evaluator replayed all 125 Hz steps from clip start for every rendered
frame. Each step evaluated the complete skeleton. At 3.9 seconds this meant 487
historical evaluations, in addition to the current pose. This explains a measured
CPU cost increasing through the diagnostic cycle. It does not establish that all
perceived stutter has this cause.

## Reproducible measurement

From `engine/`, with a locally prepared actor and its sidecars:

```powershell
cargo run -p jade-assets --example actor_timing -- ../reports/prince-sheath-animation-20261114/prince.actor
```

The benchmark warms up three calls and measures 25 calls per timestamp. It reports
median and nearest-rank p95 wall-clock CPU time. It measures skeleton, skinning,
sheath and optional vertex lighting, excluding Vulkan, presentation and frame pacing.
These are Windows development-build results, not end-to-end FPS or GPU timings.

| Lit actor phase | Before median / p95 (ms) | After median / p95 (ms) |
| --- | --- | --- |
| 0.0 s | 12.693 / 13.728 | 12.649 / 13.321 |
| 0.5 s | 17.985 / 18.236 | 12.806 / 12.979 |
| 2.0 s | 33.664 / 33.977 | 12.813 / 12.899 |
| 3.9 s | 54.549 / 65.615 | 12.792 / 12.903 |

At 3.9 seconds, median lit-actor CPU time decreased by approximately 76.5%.
Skinning without the sheath or lighting measured about 2.9 ms. Animated lighting
remains a substantial CPU cost in this unoptimized build.

An additional optimized (`--release`) run of the corrected code measured lit-actor
medians of 0.397-0.433 ms across these four phases, with 3.036 ms total load time.
This is not a before/after release comparison.

## Correction and limits

The immutable diagnostic clip now prepares its complete-step sheath states once
when loading the controller. A query copies the corresponding state and evaluates
only its fractional remainder, preserving the prior arithmetic and timing policy.
No captured poses, interpolation approximation or reduced animation rate are added.
Cache construction costs about 43 ms once on this fixture; total lit actor loading
measured 53.666 ms instead of 10.405 ms. Storage is bounded by the ten-second clip
limit: at most 1,251 states, 45,036 bytes of state data. The four-second fixture uses
501 states. Reloading the controller replaces the cache transactionally.

This is specific to the fixed, repeating diagnostic clip. Interactive forces,
changed clips or future action controllers require an appropriate new evaluator;
this cache is not a general gameplay physics implementation.

## Validation

- Exact matrix equality against the prior replay on synthetic and original-resource
  fixtures, including fractional steps, repeat boundaries, backwards seeks and
  invalid timestamps. Controller reload and failed reload are tested.
- Existing Python-reference pose and RGB checks still pass (maximum differences
  7.748604e-7 and 1.013279e-6 respectively).
- 71 ordinary workspace tests pass; three private actor checks pass separately.
- Full menu Vulkan smoke: 80 frames, resolution changes, zero validation errors
  on the AMD Radeon RX 9070 XT. This is a correctness smoke test, not an FPS benchmark.

The follow-up below measures GPU commands and presentation-related CPU waits.
Linux/macOS performance has not been measured for these changes.

## GPU and presentation follow-up

Windows, AMD Radeon RX 9070 XT, 1600x1200, complete prepared menu with Prince,
all enabled effects, `legacy-unorm`, Vulkan validation enabled. First 30 frames
are warmup; swapchain-rebuild frames and the following interval are excluded.
Initial runs used 300 frames; final A/B runs used 600 each (570 CPU samples,
569 completed GPU samples; the final submission is intentionally not collected).

The optional profiler uses two Vulkan timestamp queries around each submitted
command buffer. It checks queue timestamp support, handles valid-bit wrapping and
reads results only after the existing submission fence. During profiling only,
the image-acquire semaphore waits at TOP_OF_PIPE to exclude image availability
from the timestamp interval. This changes pipeline scheduling slightly; results
are instrumented measurements, not exact uninstrumented throughput.

CPU measurements separate simulation, prior-frame fence wait, image acquisition,
buffer updates/command recording, submission and `queue_present`. Frame intervals
also include event-loop/UI work. None measures actual screen scanout or compositor
delivery; no claim of fully eliminated display stutter follows from these timings.

| Configuration | Frame interval median / p95 | Simulation median | Fence wait median | GPU median / p95 |
| --- | --- | --- | --- | --- |
| Unoptimized dev, FIFO, after sheath cache | 17.850 / 18.659 ms | 14.514 ms | 0.432 ms | 0.503 / 0.642 ms |
| Release, FIFO, before overlap change | 5.605 / 11.180 ms | 0.398 ms | 3.715 ms | 0.557 / 0.583 ms |
| Dev with optimized assets, FIFO, before overlap | 5.639 / 11.092 ms | 0.688 ms | 2.687 ms | 0.586 / 0.635 ms |
| Dev with optimized assets, FIFO, after overlap | 5.605 / 11.145 ms | 0.658 ms | 2.703 ms | 0.541 / 0.576 ms |
| Dev with optimized assets, IMMEDIATE, before overlap | 3.223 / 3.768 ms | 0.667 ms | 0.385 ms | 0.430 / 0.467 ms |
| Dev with optimized assets, IMMEDIATE, after overlap | 2.880 / 3.218 ms | 0.650 ms | 0.022 ms | 0.427 / 0.477 ms |

The GPU is not saturated in these runs. The remaining long waits depend strongly
on presentation mode: FIFO has approximately 5.6/11.1 ms interval quantization,
whereas IMMEDIATE removes most fence waiting. This supports a presentation-related
queue wait, not a long GPU draw. It does not identify the precise compositor/display
cause of every doubled interval. FIFO behavior is retained; IMMEDIATE is only an
explicit diagnostic override and can tear.

### Integrated changes

- The dev profile optimizes only `jade-assets` at level 2. Debug information,
  assertions and overflow checks remain; renderer and application stay unoptimized.
  The original actor benchmark table above predates this profile change.
- Simulation now runs before the previous submission fence wait, allowing CPU
  calculations to overlap pending GPU/presentation work. Mapped-buffer writes,
  command-buffer reuse and query-result reads still happen after that fence.
- The IMMEDIATE comparison shows reduced fence waiting and lower frame intervals;
  FIFO improvement from this ordering alone is not established.
- No texture quality, fog, lighting or animation rate has been reduced. Default
  V-Sync selection and the single-frame GPU-resource lifetime remain unchanged.

### Repeat the bounded diagnostic

From `engine/`:

```powershell
$env:OPENJADE_PROFILE_FRAMES = '600'
$env:OPENJADE_PROFILE_PRESENT = 'fifo' # Or 'immediate' for the controlled comparison.
cargo run -p jade-viewer -- --scene ../reports/menu-prince-20261115/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
Remove-Item Env:OPENJADE_PROFILE_FRAMES
Remove-Item Env:OPENJADE_PROFILE_PRESENT
```

The viewer exits at the requested count (60-6000) and prints median, p95 and maximum
times. The override does not modify saved settings. Without profiling, no query
pool is created and the ordinary acquire wait stage is retained. No original game
files are written. Both final 600-frame runs reported zero Vulkan validation errors.
