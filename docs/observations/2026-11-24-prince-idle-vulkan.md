# Prince menu idle controller in Vulkan (2026-11-24)

The bounded menu route established by the [native timing and event checks](2026-11-23-prince-clock-menu-sync.md)
now runs in the Rust/Vulkan viewer. This is an independent implementation from
original resource decoding and observable GOG behavior. No historical engine
source was consulted or incorporated.

## Implemented behavior

An optional `.idle` sidecar carries the original alternative clip `330010E9`:
36 local transform channels, 73 source units, source SHA-256
`ccbc4ad1d10d868d130b71580e7e247b6e63efe4ca103f84c00b52b74fd822b8`.
The existing `.actor` supplies the normal clip, skeleton and skin bindings.
The exporter checks the source skeleton and does not overwrite existing outputs;
the runtime uses bounded actor decoding and rejects incompatible skeletons.
Without this sidecar, older exports retain their previous single-clip behavior.

The UI's existing Camera02 completion state enables the sequence. The current
normal clip finishes before stage 1 starts. Two alternative cycles run at rate
10, followed by three normal cycles at rate 10; the terminal alternative stage
continues at rate 5. Durations come from clip data, not recorded wall-clock
thresholds. The stage-3 repetition-counter wrap is pose-equivalent because that
stage repeats the same clip/rate. The runtime does not implement arbitrary rows,
health-dependent branches or a general behavior interpreter.

Normal-clip returns blend from the preceding terminal pose. The alternative
clip's extra spine translation survives the return to the normal clip. Sheath
simulation preserves state across body clip changes; lighting and reflection
sample the same evaluated pose. Returning to the menu disables the sequence;
Camera02 can activate it again. This return is a viewer preview/reset operation,
not a claim to reproduce a general playable-game interruption.

The game-specific sequence is isolated in `actor/tsot_idle.rs`; resource readers,
skinning, lighting and the Vulkan renderer remain separate. Sampling is independent
of display frequency. The blend uses the existing 125 Hz diagnostic simulation
timebase with the measured 1/15360-second elapsed quantization. This is not a claim
of bit-exact native frame scheduling. Absolute startup phase relative to the GOG
application, all native branches and the complete animated character remain outside
this implementation.

## Validation

- Workspace tests: 80 passed, 16 fixture-dependent tests skipped by default.
- The new fixture-dependent test was run explicitly: 29 native poses / 34 primary
  rotations, with time derived from observed selection and captured dt, no pose
  phase fitting. Maximum rotation RMS: 0.000058428, below 0.0002.
- The fixture test also checks retained spine translation and cached-versus-replayed
  sheath results through 80 seconds, including disable/reactivate and seeking.
- Synthetic checks cover initial clip-end gating, sequence/terminal behavior and
  repeatable samples across simulated display rates 30/60/144/240 Hz.
- Five Vulkan captures at diagnostic times 6, 18.7, 25, 40 and 80 seconds have
  identical repeated fixed-time frames and zero validation errors. Captures use
  the balcony endpoint camera and an explicit diagnostic activation at time zero;
  they are not synchronized GOG final-pixel comparisons.
- Interactive menu smoke passes with Camera02 completion, return and resizing;
  80 presented frames, zero Vulkan validation errors.
- `cargo fmt --check` and workspace/all-targets Clippy with warnings denied pass.

## Frame-time comparison

Same executable, legacy-unorm, 800x600, FIFO, validation enabled, 6,000 frames per
run. The earlier baseline used a different presentation timing pattern; a second
baseline was measured after the completed idle run. An interrupted idle run of
741 frames is retained but excluded from the comparison.

| Metric, milliseconds | Baseline repeat median / p95 | Idle median / p95 |
| --- | --- | --- |
| Frame interval | 5.584 / 11.378 | 5.583 / 11.417 |
| CPU simulation | 0.738 / 0.871 | 0.752 / 1.036 |
| GPU commands | 0.331 / 0.343 | 0.331 / 0.341 |

Both completed runs report zero Vulkan validation errors. These bounded sequential
runs show a modest simulation cost increase and similar frame intervals; they do
not establish long-session stability or every machine's performance.

## Local reproduction

Prepared private bundle: `reports/menu-prince-idle-20261123/menu.ojscene`.
It includes the new `.idle` beside the existing actor, sheath, lighting,
placement, reflection and scenery sidecars. From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-prince-idle-20261123/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

Select Start New Game, wait for Camera02 to finish, then leave the Prince idle.
Escape returns to the menu. This is an animated preview, not player movement.

To prepare the optional clip for another compatible existing export, from the
repository root, supply the original decoded actor bundles:

```powershell
python src/export_prince_idle.py <scene.actor> <scene.idle> --sources <decoded-bundle-1> <decoded-bundle-2> <decoded-bundle-3>
```

Diagnostic environment variable `OPENJADE_PRINCE_IDLE_START=0` explicitly enables
an activation origin for isolated fixed-time captures/profiling. Omit it for
normal interactive use, where Camera02 drives activation.

Private evidence in the bundle directory includes `idle-export.json`,
`pose-*/validation.json`, `pose-*/prince.png`, `menu-smoke.txt`, `tests.txt`,
`tests-native-idle.txt`, `timing-idle-complete.txt` and `timing-baseline-repeat.txt`.
Game data and captured native palettes are not intended for Git.
Windows was tested here; this change has not been revalidated on Linux/macOS.
