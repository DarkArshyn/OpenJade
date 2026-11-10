# Vulkan fixture deformation

Date: 2026-11-10

## Implemented behavior

The two hangfire fixtures now evaluate their ordered type-1 modifiers in the native viewer. The first wave uses primary mesh alpha / 256, and the second wave reads the Z coordinate produced by the first. Their stored local-axis scales and row-basis rotations transform the displacement into world space. Only the selected `[0, 41)` source vertex range moves; excluded groups retain their existing geometry.

The exporter writes an optional `menu.fixtures` sidecar. Its 672 records cover 168 expanded corners in each of two flame passes on each of two fixtures. Both passes therefore share the same local deformation; the existing independent UV animations and blending remain active. The decoded controls use the existing animated-vertex GPU upload path, including fence synchronization, window resizing and Camera02 movement. No shader or global-light adjustment is required.

The sidecar is `OJFIX001`, a u32 count, eight f32 values (amplitude, spatial factor, rate, initial phase for each modifier), then records of one u32 vertex index and thirteen f32 values (local XYZ, normalized weight, scaled 3x3 basis). Loading is bounded to 4,096 records, rejects malformed extents, nonfinite values, out-of-range indices and overlapping animation controls. Packages without this sidecar retain their previous behavior. Only package preparation reads the original files; the runtime consumes the prepared data.

## Validation

- The Rust native replay checks **41,664 expanded corners** against the GOG modifier capture. Maximum local-coordinate error: `5.960464477539063e-08`. The comparison uses captured phases, not an assumed synchronization with the game's clock.
- Unit checks cover ordered composition, scale application, malformed sidecars and duplicate controls.
- Workspace tests: **60 passed**, 10 local-data tests ignored in the ordinary run. Both fixture native replays were also run explicitly and passed.
- Clippy passes for all workspace targets with warnings denied.
- Deterministic Vulkan captures at 0, 2 and 4 seconds match between frames 11 and 21 of each run. Against the same package without fixture deformation, 846, 716 and 810 pixels respectively change. These are contribution checks, not whole-scene fidelity measurements.
- An 80-frame interactive menu smoke test, including resizing and Camera02 transition, finishes with **zero Vulkan validation errors**.

Local prepared package: `reports/menu-fixtures-20261110`. Capture images and measurements: `reports/fixture-gpu-20261110`. Original assets and these derived artifacts remain outside Git.

## Run

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-fixtures-20261110/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

A full `export_engine_materials.py --palm-source <decoded-menu>` preparation now creates `menu.fixtures` automatically. Keep it with the other scene sidecars. The prepared package above reuses the previous validated package and adds the fixture sidecar.

For the native replay, set `OPENJADE_FIXTURE_SCENE` to the prepared scene and `OPENJADE_FIXTURE_CAPTURE` to the local `hangfire-weights2-modifiers.bin`, then run:

```powershell
cargo test -p jade-assets native_fixture_chain -- --ignored --nocapture
```

The local replay additionally needs `fixture-native-mesh.bin` (resource `2E004CC0`) beside the prepared scene; the viewer does not require this test artifact.

## Limits

The native weight source and modifier order are established in the [loading audit](2026-11-10-hangfire-lighting.md). This integration starts both phases from the stored zero values and advances with the viewer's animation clock. The startup and update rule are now verified for the captured fixed-menu interval below; wall-clock synchronization between independently running programs is not established. The prepared package's base geometry is unchanged, but the initial animated pose can differ from it because cosine displacement is nonzero at phase zero. Lighting receivers, small glow effects and complete visual fidelity remain separate investigations.

## Startup and temporal synchronization check

A new GOG observation records 4,804 modifier calls: four modifier instances over 1,201 consecutive menu frames. Each record contains frame number, menu-ready marker, modifier pointer, flags, phase before and after the call, engine delta at `0080CBFC`, and a performance-counter timestamp. The probe is installed before the first recorded fixture call. Each modifier's first observed phase is zero; each advances exactly once per sampled frame. The two fixtures remain synchronized. Their animation is already active in the main menu, without selecting New Game.

The first captured engine delta is 0.008 seconds. First output phases are 6.2759857177734375 and 0.009600000455975533 radians. This delta is an observation, **not a fixed startup delay to hard-code**.

The native update computes `phase + rate * 30 * dt` with extended intermediate precision and rounds when storing the new float. It then subtracts or adds one float32 full turn if outside the interval; equality with a full turn is retained. The earlier Rust expression rounded intermediate float32 products. Its maximum measured discrepancy here was only `5.59e-9` radians, not a visible speed or delay error. Rust now uses wider intermediates, one float32 store and the native boundary handling. Large fixed-time diagnostic jumps retain an additional modulo fallback; they are not native frame replays.

`native_fixture_clock` reproduces **all 4,804 phase outputs bit-for-bit**, starting from zero and using each recorded engine delta, including positive and negative wrap crossings. It also checks the phase-before chain and one call per frame per modifier. Run from `engine/` with `OPENJADE_FIXTURE_CLOCK` pointing to the private `fixture-sync-events.bin`:

```powershell
cargo test -p jade-assets native_fixture_clock -- --ignored --nocapture
```

Private evidence: `fixture-sync/fixture-sync-events.bin`, `fixture-sync-clock.bin` and `fixture-sync-frequency.bin` in the research workspace. The probe completed and its saved proxy was restored. No original game files were changed.

The recorded engine deltas sum to about 9.210 seconds per modifier; performance-counter time from its first to last callback is about 9.05 seconds. Those intervals also differ by their first-step boundary. Therefore no universal wall-clock correction factor is inferred. The viewer still supplies its own frame deltas (and uses its existing stall clamp), while time-zero diagnostic captures intentionally show the initial pose before elapsed time. Exact overlay with a video requires matching the engine-time origin and frame-delta sequence, not merely matching frame numbers. The check does not cover menu departure, pauses, or resetting the scene.
