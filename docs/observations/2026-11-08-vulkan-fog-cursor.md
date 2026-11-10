# Dynamic fog and animated cursor in Vulkan (2026-11-08)

## Implemented behavior

The viewer now loads the two native Menu3D_Fog3D emitters from the optional `menu.fog` sidecar. Export reads descriptor 30000D27, both GAO matrices, material 2E0051F1 and texture 2E004FE4 from the verified frozen scene. Both emitters retain their original parameters, including descending end-duration endpoints. They render alongside the three existing fog panels using source-over blending, depth testing without depth writes and the existing normal vertex-fog path.

Births start in the initial phase. Sampled sizes remain constant, while the native packed colors change through the three phases. Movement uses the quantized native step and rotation advances once per update. Interactive presentation uses frame deltas. Fixed-time captures use deterministic 60 Hz scheduling. A private RNG stream is used, so these particles are not synchronized with the original game's shared RNG. Sorting retains the existing emitter-center/transparent-draw ordering; exact native ordering and final scene fidelity remain under comparison.

The OJUI0004 bundle adds both original cursor textures and the four linear color keyframes read from C_Default in `pop4common.mgm`. Rate, layout dimensions and alpha endpoints come from that resource. The viewer draws the base and halo consecutively, with independent per-quad opacity and RGB gain 254/255. Original texture dimensions and linear filtering are preserved. Older OJUI0002/0003 bundles still load with their existing base cursor. The new track restarts when the menu bundle is loaded and loops at its final keyframe. Native activation timing is not reconstructed and alpha quantization remains within the previously measured one-level tolerance.

## Validation

- 57 ordinary Rust workspace tests pass. Eight local-evidence tests remain opt-in.
- The opt-in Rust native_fog_draws check passes 204 captured GOG draws and 21,348 corners. UV and packed colors match exactly, with maximum XYZ component error 7.63e-6.
- Fixed-time Vulkan comparisons with --no-fog change 0, 80,998 and 239,592 pixels at 0, 1 and 2 seconds. Maximum channel changes are 0, 13 and 45 levels. This measures contribution, not original-game fidelity.
- The complete menu presents 80 smoke frames, including resizing and Camera02 transition, with zero Vulkan validation errors. A regression checks that UI opacity data is cleared with the vertices during the transition.
- Clippy passes for all workspace targets with warnings denied.

Local prepared resources are under `reports/menu-fog-cursor-20261108`, GPU comparisons under `reports/menu-fog-gpu-20261108`. Earlier [draw isolation](2026-11-05-cursor-dynamic-fog.md) and [lifecycle measurements](2026-11-05-fog-cursor-lifecycle.md) remain the research evidence. Original game data is not modified or included in Git.

## Run

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-fog-cursor-20261108/menu.ojscene --menu ../reports/menu-fog-cursor-20261108/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

Add `--no-fog` to disable only the two dynamic emitters, keeping the existing panels and vertex fog. The prepared package copies the previous validated geometry and sidecars and adds menu.fog. A fresh full export with `export_engine_materials.py --palm-source` also writes menu.fog. Re-export the UI with `export_native_menu.py` to obtain the two cursor passes and MGM tracks.

For the native draw replay set OPENJADE_FOG_SCENE to the prepared scene and OPENJADE_FOG_CAPTURES to the extracted fog-life directory, then run `cargo test -p jade-assets native_fog_draws -- --ignored --nocapture`. From the root run `python tests/integration_rain_vulkan.py <scene> <new-output-directory> --effect fog` for fixed-time contribution checks.

Next, compare the complete fog composition with a phase-controlled original capture before changing global lighting. Exact transition RNG replay, cursor activation/rounding and native transparent ordering remain research limits.
