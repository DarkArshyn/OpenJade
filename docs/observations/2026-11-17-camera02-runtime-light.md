# Camera02 generated light in Vulkan and final-pixel ablation

Date: 2026-11-17

## Implementation

Placed actors now recompute the generated world direction from their placement
origin and the current camera position. The presenter uses the active menu camera
when supplied, otherwise the scene camera. The direction is converted through
the inverse rigid placement basis before animated-normal lighting. The verified
positive 0.3-radian polar angle and float32 pi offset are used. The named source
lights, ambient color, generated RGB, geometry, animations and material paths are
unchanged. This adds one direction calculation per actor frame, not per vertex.

Legacy isolated actors without a world placement retain their captured direction.
Nonfinite or degenerate horizontal inputs also retain it rather than inventing an
unverified behavior. `render_vertices` preserves the legacy diagnostic API;
`render_vertices_for_camera` is the runtime entry point.

`OPENJADE_GENERATED_LIGHT=dynamic|frozen|off` provides an explicit diagnostic
override. Dynamic is the normal default. Frozen keeps the package direction; off
zeros only this generated RGB contribution. No original game settings are changed.

## Calculation and regression checks

The production Rust calculation agrees with all 3,025 native input/output pairs
from the [Camera02 capture](2026-11-17-camera02-generated-light.md): maximum
absolute direction-component error **1.7881393e-7**. This comparison supplies each
native owner's captured position to the function; it is not a claim that every
runtime component already reproduces that owner's motion.

The runtime currently treats the prepared Prince as one actor with a shared
placement origin. Some native equipment/component owners move separately. Across
the capture, substituting the shared origin for those individual positions changes
a generated direction component by up to 0.006955 (horizontal owner separation
up to 0.286413 scene unit). Individual receiver-owner motion remains a fidelity
limit, distinct from the validated formula and camera dependency.

Two new unit tests check world/local conversion with rotated placement, camera
motion, frozen/off modes, unchanged geometry and fixed-color materials, quadrants
and invalid inputs. The workspace passes **74 ordinary tests**, with 14 private
tests ignored by default. Four relevant private actor tests were run explicitly
and pass: original poses, previous fixed-light parity, sheath continuity and ground
placement. Clippy with warnings denied and formatting checks pass.

## Final Vulkan pixels

The same prepared source-light menu is rendered at three decoded camera poses.
Actor/effect time is fixed at 2 seconds for every variant; only the generated-light
mode changes. Screenshot-layer readback captures the final 800x600 presented image
in `legacy-unorm`, with the normal fog and scene composition enabled, without UI.
These are static samples along Camera02, not a time-synchronized GOG video comparison.

Each variant has byte-identical frames 11 and 21. A separate repeated dynamic run
is also byte-identical at all three poses. Both the initial experiment and the
public test reproduce the following results:

| Camera time | Dynamic vs frozen: changed pixels / max RGB delta | Dynamic vs off: changed pixels / max RGB delta |
| --- | --- | --- |
| 0 s | 0 / 0 | 237 / 17 |
| 4.5 s | 168 / 2 | 2,100 / 44 |
| 9 s | 607 / 2 | 4,725 / 60 |

Deltas are absolute 8-bit channel differences, not percentages. At the endpoint,
dynamic-vs-frozen differences lie within x393..449/y430..511; dynamic-vs-off within
x375..466/y418..519. Visual inspection places these differences around the Prince.
The dynamic correction is small; the full generated light's contribution is larger.
This demonstrates a causal effect on **OpenJade's final pixels**, after composition.
It does not establish equality to GOG final pixels, nor isolate that contribution
after the original game's postprocessing. Original-GOG final-pixel parity remains
unvalidated. Bright curtain/material discrepancies are also outside this change.

## Performance

Four alternating endpoint runs (frozen, dynamic, dynamic, frozen), each with 1,800
frames, used 800x600, FIFO, validation, animated effects and no screenshot layer.
Thirty warmup frames are excluded. All runs report zero validation errors.

| Mode/run | Frame interval median / p95 ms | Simulation median / p95 ms | GPU median / p95 ms |
| --- | --- | --- | --- |
| Frozen 1 | 5.613 / 11.307 | 0.705 / 0.870 | 0.312 / 0.334 |
| Dynamic 1 | 5.604 / 11.359 | 0.701 / 1.042 | 0.314 / 0.333 |
| Dynamic 2 | 5.614 / 11.323 | 0.694 / 0.833 | 0.314 / 0.333 |
| Frozen 2 | 5.608 / 11.353 | 0.714 / 1.017 | 0.313 / 0.331 |

There is no material median slowdown in these measurements. The small sample and
p95 variability do not prove statistical equivalence. Presentation intervals do
not measure scanout latency. This is endpoint profiling, not a full interactive
transition benchmark.

## Reproduction

```powershell
cd engine
cargo run -p jade-assets --example generated_light_parity -- ../reports/camera02-generated-light-20261117/light-camera02b
cargo run -p jade-viewer -- --scene ../reports/menu-prince-source-lights-20261117/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

Existing prepared menu packages work with the updated executable; no re-export
is needed. Select Start New Game to use the active Camera02 camera.

```powershell
python tests/integration_generated_light_pixels.py <prepared-menu-folder> <Camera02-poses.json> <new-output-directory> --viewer <jade-viewer.exe> --profile
```

Private images, pixel reports, camera snapshots and timing logs are in
`reports/camera02-runtime-light-20261117/`. No original assets are added to Git.
Next fidelity targets are individual receiver origins and a controlled comparison
of the original game's final composition.

## Receiver-origin follow-up

The [receiver-origin integration](2026-11-17-receiver-origins.md) replaces the shared origin for the support and face using their evaluated source bones. GOG final-pixel parity remains open.
