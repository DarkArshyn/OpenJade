# Runtime material animation

Date: 2026-10-30. Scope: the frozen menu export, not general Jade materials.

## Evidence and implementation

This reuses the bounded decoders and native interpretation documented in
[fixture materials](2026-10-25-fixture-materials.md) and
[fog state](2026-10-21-native-fog-state.md). No new native decompilation is claimed.
`src/export_engine_materials.py` now optionally emits OJSCN004 with per-draw UV
rates. U/V flags 0x40000000/0x80000000 select moving components; non-dynamic
offsets stay in the existing parameters. Fog uses the decoded U rate and retains
the existing correction for the source OBJ's sampled fog time.

| Draws | U cycles/s | V cycles/s |
| --- | ---: | ---: |
| Three fake fog panels | 0.0791015625 | 0 |
| hangfire1 and hangfire2, stage 0 | -0.19921875 | -0.296875 |
| hangfire1 and hangfire2, stage 1 | -0.3984375 | -0.6484375 |

These are seven animated passes among 90. Lampion offsets are static; sky/moon
are unchanged. The Presenter owns an elapsed-time clock independent of Camera02
and swapchain resources. Each frame combines the sampled offset and signed rate
in f64, wraps modulo one, and uploads the resulting fragment constants. Static
components remain bit-preserved. No shader change, geometry change, alpha change
or global illumination adjustment is included.

## Validation

- 37 Rust tests passed, including legacy/static loading, v4 extent and rate
  rejection, negative UV motion, wrapping, long elapsed time and static fields.
- Four exporter tests passed, including binary equality of fixed/animated data
  before the rate table and correct association after transparent sorting.
- Workspace Clippy passed with warnings denied.
- Real export: 48 objects, 15,813 geometry triangles, 16,365 submitted triangles,
  90 passes and 39 textures. Previous payload preserved exactly after excluding
  the header and appended 720-byte rate table.
- Vulkan smoke: 80 presented frames, zero validation errors; resize, native UI
  and Camera02 exercised. Evidence: ignored
  `reports/menu-uv-motion-20261030/verification.json` and `runtime/manifest.json`.

## Limits

The phase origin is chosen at startup plus exported `--time`, not captured from
the original executable. Pause semantics are not reproduced. The material clock
continues across menu navigation and camera reset. No visual comparison against
a timed original-game capture has been performed. This does not implement fire
particles, light emission, dynamic lighting or more accurate fog density. Earlier
packages remain static and require re-export with `--animate-uv` to move.
