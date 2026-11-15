# Source collision placement in the Vulkan menu (2026-11-15)

## Implemented behavior

`assemble_prince_balcony.py` now resolves the source balcony collision intersection
through `prince_ground.grounded_placement`. Checkpoint XY and orientation are retained;
only initial Z comes from the unique upward collision triangle below that checkpoint.
Missing, ambiguous, downward-facing or unsupported intersections fail the export.
No native captured height constant is used in the export or runtime placement.

The result is written to the existing `OJAPL001` placement sidecar and to the
initial actor vertices. Rust loads that rigid placement and applies it to every
animated actor vertex, including after body-loop boundaries. No new frame-by-frame
collision calculation is added. This is **initial menu placement**, not a continuous
collision solver, foot IK, player movement or a general game-asset loader.

Private package: `reports/menu-prince-grounded-20261115/menu.ojscene`.
Older prepared packages are retained and are not silently upgraded. The new manifest
records the collision resource hashes, hit triangle, source checkpoint and derived
placement. Scene SHA-256:
`84cf41b6f8fc79c21191aea41b51d2e9f26012fb29399c05eae1e8ba20f0718c`.

## Verification

- Derived Z: 1.342055320739746; difference from the checkpoint: -0.014345169067382812.
- Compared against 167 native placements: Z residual within +/-2.3842e-7,
  with checkpoint XY and orientation retained.
- Existing scenery vertices, draw records, texture pixels, UV rates, palm records
  and effect sidecars remain identical to the input scene.
- Five synthetic Python tests cover a known support plane, changed source height,
  missing/ambiguous support, invalid indices/truncation and unsupported normal/height.
- Rust private-fixture test checks the loaded placement on every uploaded actor
  vertex at 0, 2, 3.99999, 4 and 8.01 seconds. Four actor fixture checks pass.
- 72 ordinary Rust workspace tests pass (14 private-fixture tests ignored by
  default); workspace Clippy passes with warnings denied.
- Full interactive-menu smoke: 80 frames with resolution changes, zero Vulkan errors.
- Endpoint-camera captures at 2, 3.983333 and 4 seconds have identical repeated
  frames at each fixed time and zero Vulkan validation errors. They do not establish
  original-game pixel parity.

## Frame-time reference

Same endpoint-camera scene, 800x600, FIFO, legacy-unorm, validation enabled,
AMD Radeon RX 9070 XT, 1,800 live frames. No screenshot layer during timing.

| Metric | Previous median / p95 | Grounded median / p95 |
| --- | --- | --- |
| Frame interval | 5.670 / 11.087 ms | 5.653 / 11.239 ms |
| CPU simulation | 0.674 / 0.802 ms | 0.674 / 0.955 ms |
| GPU commands | 0.312 / 0.321 ms | 0.314 / 0.335 ms |

Medians remain close; the p95 increase is recorded rather than dismissed. These
single local runs do not establish a statistically significant regression or
equivalence. There is no added runtime collision workload. Continue using the same
workload and profiling method for subsequent changes. Display scanout and other
platforms are outside this measurement.

## Launch

From `engine/`, using the existing local UI bundle:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-prince-grounded-20261115/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

Preparation still uses the documented assembler arguments, with a new output directory.
See [native grounding evidence](2026-11-15-prince-native-ground.md) for the resource
chain and native contact observations. Native startup forces, action selection,
general collision, source-loaded scene lighting and full material fidelity remain
unfinished. This update has been checked on Windows only.
