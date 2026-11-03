# Native menu rain in Vulkan (2026-11-03)

## Scope and evidence

This independent implementation connects the previously verified
[parameter reader](2026-11-03-rain-native-parameters.md),
[creation and lifetime behavior](2026-11-03-rain-spawn-life-transform.md),
[live emitter state](2026-11-03-rain-live-state.md) and
[captured draw appearance](2026-11-03-rain-appearance.md) to the Rust viewer.
Only GFX_Rain01 and GFX_Rain02 are enabled. Original files are read only;
game-derived packages, captures and executable analysis remain in ignored reports.

## Data and implementation

`src/export_rain_controls.py` accepts only the hash-verified frozen menu. It checks
object/descriptor/material bindings and supported flags, then resolves the unique
decodable texture record. `menu.rain` contains magic OJRAIN01, two 156-byte records
(16 matrix floats, capacity, 18 parameter floats and four packed colors), then
4096 RGBA bytes. Total size is exactly 4416 bytes. Numeric fields come from the
resource, not values adjusted to imitate a screenshot. The 32x32 base image is
preserved; no game data is embedded in Rust source or synthetic test fixtures.

`jade-assets::rain` validates the sidecar before changing the scene, appends one
texture and reserves 150 six-corner slots per emitter. Inactive slots are
degenerate and have zero alpha. The exporter manifest distinguishes its base
geometry counts from the 600 reserved runtime triangles and extra texture.
The current package has 48 static objects, 39 base texture layers and 16,365 base
submitted triangles; loading rain produces 40 layers and 16,965 reserved triangles.

Emission and motion have separate native accumulators. Float step constants,
strict phase expiry, swap removal, zero-speed random consumption, rectangle axes
and packed-byte interpolation are retained. Rust range sampling uses a double
intermediate to preserve the observed x87 final-store rounding. The color/UV/
corner path is checked directly against native captures, not only Python output.

Vulkan uploads XYZ/UV/RGB/layer and byte alpha after the previous frame fence.
The material uses texture times diffuse times two, texture-alpha times particle
alpha, SRC_ALPHA/ONE RGB blending, depth testing with writes disabled, and no
applied vertex fog. Rain does not write the masked additive target. It participates
in scene composition before the measured blur, UI and gamma. Existing source-alpha
additive pipelines and the per-vertex alpha stream are reused. `--no-rain` disables
simulation; the initially degenerate reserved geometry remains invisible.

## Validation

- Six synthetic Rust tests cover three native creation seeds, motion, strict phase
  boundaries, packed colors, corner order, parser failures, capacity and deterministic
  scheduling. The standard workspace suite passes 51 tests; the local capture test
  is ignored by default because it needs original-game data.
- Explicitly running the capture test matches all 4,602 corners from 18 native draws:
  positions, UVs and RGBA agree exactly across 635 main, 42 initial and 90 end-phase
  particle observations.
- Vulkan captures at fixed times 0, 1 and 2 seconds match exactly between frames
  11 and 21. Comparing enabled and disabled rain changes 0, 23,786 and 16,688 pixels,
  respectively; maximum RGB differences are 0, 18 and 21 byte levels. These are
  contribution checks, not a comparison to an aligned original-game frame.
- An 80-frame native-menu smoke test exercises resizing and reports zero Vulkan
  validation errors on AMD Radeon RX 9070 XT. The captured scene-only runs also
  report no validation errors. `cargo clippy --workspace --all-targets -- -D warnings`
  passes.

Local evidence: `reports/menu-rain-20261103/`, `reports/menu-rain-gpu-20261103/`
and original draw captures in `reports/rain-appearance-20261103/`.

## Reproduction

From the repository root, choose a new output directory:

```powershell
python src/export_engine_materials.py reports/menu-sky-moon-20261030/source-final reports/camera02-transition-20261026/preview/poses.json reports/menu-rain-20261103 --animate-uv --palm-source reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin
python tests/integration_rain_vulkan.py reports/menu-rain-20261103/menu.ojscene reports/menu-rain-gpu-check
```

From `engine/`:

```powershell
cargo test --workspace
$env:OPENJADE_RAIN_CAPTURES = 'C:/OpenJade/reports/rain-appearance-20261103'
cargo test -p jade-assets native_captured_vertices -- --ignored --nocapture
Remove-Item Env:OPENJADE_RAIN_CAPTURES
cargo run -p jade-viewer -- --scene ../reports/menu-rain-20261103/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

The GPU check needs a built viewer and the Vulkan SDK screenshot layer. It writes
new directories only. `OPENJADE_CAPTURE_SECONDS` fixes the research animation time;
it is not a recovered game timestamp. Add `--no-rain` for comparison.

## Remaining limits

The two emitters share a private CRT-compatible stream initialized with seed 1;
the original stream is shared with other systems. A fixed 60 Hz research scheduler
feeds the native update/emission equations and keeps poses independent of display
rate. Native wall-clock scaling and random-stream synchronization remain unresolved.
Stored matrices match measured live fixed-menu matrices; behavior-dependent
overrides during Camera02 have not been reproduced. This is a focused rain mode,
not a general particle decoder. Native rain sampler/mipmap selection and scene-wide
transparent ordering still need separate validation. The current renderer uses
linear sampling and its existing mip/filter behavior. No splash, bird, insect,
dynamic fog-particle or particle-collision implementation is claimed.
