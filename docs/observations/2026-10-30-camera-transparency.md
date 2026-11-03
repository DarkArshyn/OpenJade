# Camera-relative transparency ordering — 2026-10-30

## Change

The Vulkan viewer now recalculates scene pass order for every rendered frame,
using the same active eye/forward push constants as scene.vert. This follows
native-menu Camera02 playback and its reset, as well as the legacy UI camera.
Without a menu, the fixed scene camera is used.

World-space centroids are calculated once from each validated draw's vertex
range, with f64 accumulation. Each frame uses `(center - eye) dot forward`.
Opaque draws retain their original order and execute first. Source-over and
source-alpha-additive draws follow from far to near. Equal-depth passes retain
their original relative order, including stages sharing the same fixture
geometry. The UI still draws separately after the scene. GPU vertex buffers,
textures, material parameters, gamma and light contributions are unchanged.

Implementation: `engine/crates/jade-render-vulkan/src/draw_order.rs`, invoked
from Panel's command recording before scene draw calls. The interchange reader
continues to validate contiguous source ranges; only submission order changes.
No resource regeneration or format change is needed.

## Validation

- Workspace tests: 34 passed, including four new ordering regressions.
- New tests cover forward-vector reversal and reset, opaque-first ordering,
  equal-depth stage stability, view depth rather than radial distance, correct
  draw ranges, trailing UI exclusion and an empty diagnostic scene.
- Cargo fmt and Clippy with warnings denied pass.
- Updated viewer with the final sky/moon package, native UI, legacy-unorm and
  validation: 80 smoke frames including display-setting changes, resizes,
  Camera02 playback and reset; zero validation errors.

An independent CPU check of all 541 camera samples from the actual OJUI0003
bundle finds four distinct orders. Initial order matches the exported package.
The following changes occur at sampled frame boundaries:

| Frame / time | Pass owners changing relative order |
| --- | --- |
| 153 / 2.55 s | hangfire1, lampions |
| 169 / 2.816667 s | hangfire1, hangfire2 |
| 187 / 3.116667 s | hangfire2, lampions |

Names above omit the common Menu3D_ prefix and .gao suffix. These are computed
ordering changes, not measurements of a live original-game frame or a visual
claim that every change is perceptible. The seven-pose research JSON is not
the 541-sample native playback bundle; the final check uses the latter.

Local evidence: `reports/camera-transparency-20261030/orders.json`.
Scene SHA-256: `491880aec2de07fa2552dcbfbac25c715609179989deb59fe6acbfba395eef48`.
UI SHA-256: `63f0b15b7e1303d868b5cd35f457623c4bfb17afbb5ede857df84cfe87482486`.

## Run

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-sky-moon-20261030/runtime-final/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

Start New Game plays Camera02; Escape returns to the initial menu camera.
Add `--smoke` for the automated lifecycle check.

## Limits

Centroid sorting is an OpenJade diagnostic policy, not recovered native Jade
sorting. It cannot guarantee correct composition for intersecting transparent
surfaces or solve per-triangle ordering within a group. Geometry remains static;
fog/fixture UV animation is still sampled at its exported phase. No global
lighting, moon illumination, fog opacity or material gain was changed.
