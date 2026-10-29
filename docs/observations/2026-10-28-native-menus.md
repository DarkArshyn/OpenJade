# Native detailed menus — 2026-10-28

## Scope and provenance

This ports the independent `src/simulation_screens.py` layouts and interaction
model into Rust; no original executable code is included. Layout references are
the user's PC GOG 800x600 captures. `src/export_native_menu.py` reads the existing
DDS/MFT research report and the previously validated OJUI0001 Camera02 samples.
It produces OJUI0002 assets only; Python is not invoked by the runtime.

## Implemented behavior

- Profile creation/selection/deletion; main and Options pages; Keyboard/Gamepad,
  Game, Graphics Effects/Advanced, Sound; original credits remain a notice.
- DDS panels, cursor, arrows, slider bar/handle and MFT glyph geometry rendered
  over the existing 3D scene in one Vulkan window. ASCII profile input is direct
  keyboard input, without clipboard paste. Six of eighteen command rows are visible.
- Gamma, ordinary-material filtering, window resolution and V-Sync are live.
  IMMEDIATE presentation is required for V-Sync off; unsupported requests stay
  enabled with an explanation. Window resolution does not change the desktop mode.
- Settings preview, Yes/No/Cancel, research-baseline defaults, and isolated
  OpenJade persistence. Keyboard bindings can be captured and saved but are not
  gameplay actions. Other unavailable systems are greyed out.
- New Game keeps the existing nine-second Camera02 playback and Escape reset.

`jade-assets/src/native_ui.rs` contains the bounded loader, menu state, transactions
and sprite layout. `jade-viewer` translates winit input and applies renderer settings.
`jade-render-vulkan` uploads dynamic UI vertices after waiting for the sole frame
fence; ordinary draw order remains scene, alpha-blended UI, output gamma.

## Assets and persistence

106 sprite/glyph entries use three 512x512 atlases instead of 76 baked-page tiles.
There are 41 total images with the current 38-image scene. Original scene texture
dimensions are unaffected. UI logo preparation is 480x120, panel preparation
500x500; original bitmap glyphs retain their extracted coverage/metrics. Nearest
atlas sampling and exact font layout remain visual limitations.

The adjacent `menu.ojmenu` uses OJMNU001 and contains global committed preferences,
up to five independent menu profiles, the selected active profile, 36 keyboard
labels and 18 gamepad labels. It is not an original save decoder. Loading is
bounded to 8 KiB and validated before mutation. Saves use an exclusive temporary
file, flush and rename; unrelated files are refused. One writer per file is
supported. No game installation/profile directory is written. Files are Git-ignored.

## Validation

On Windows / AMD Radeon RX 9070 XT:

- 27 Rust tests passed, including six native UI cases and two state-file tests.
- `cargo fmt --all --check` and Clippy all targets with warnings denied passed.
- Native menu GPU smoke: 80 frames, two resizes, page navigation, gamma/filter/
  V-Sync changes, Cancel/No handling and accelerated Camera02; zero validation errors.
- Interactive Vulkan inspection: profile entry/main menu, Options, Graphics,
  gamma 0.52 preview, No restoring the committed value, Keyboard, quit confirmation.
  That session ended after 27,268 frames with zero validation errors.

Unit tests cover state serialization/reload and safe replacement of owned files;
validation success does not establish original-game pixel equivalence. Local
artifacts and smoke logs are under `reports/engine-native-menu-20261028/`.

## Remaining work

Original credits, saved-game loading, gameplay, audio, gamepad capture, mouse/camera
gameplay controls and remaining graphics-quality options are not implemented.
Profiles identify the menu user; preferences are global, not per-profile. Default
values are research baselines. No new original lighting/material interpretation
is established here. High-resolution interface filtering, clipping/focus polish
and full cross-platform validation remain follow-ups.
