# OpenJade engine bootstrap

Target: Rust + ash + Vulkan on Windows as host.

This workspace now opens a **Vulkan presentation window** and retains the CLI adapter probe.
The window renders a centered **textured square (two triangles)** on a blue-grey background.
Its original 128x128 RGBA checkerboard is uploaded to a Vulkan image and sampled by a fragment shader.
Expected corner colors: red top-left, green top-right, blue bottom-left, yellow bottom-right.
The square retains its proportions when resized. With `--scene`, the viewer instead
renders decoded menu geometry with textures, vertex colors, depth testing and a fixed camera.
Rust 1.99.1, Cargo 1.99.1 and MSVC C++ tools are installed and verified. The workspace compiled and the probe ran
successfully with validation enabled: AMD Radeon RX 9070 XT, Vulkan 1.4.349, one graphics-capable queue family.

The 2026-10-27 textured-panel smoke run presented 80 frames, resized from 800x600 to 1024x720
and back to 800x600, then shut down with zero validation errors. Clippy with
warnings denied passed. Minimization and other GPU/OS combinations remain
unverified by this automated test. Validation success alone does not prove pixel correctness.

## Prerequisites and first build

- Rust via rustup, x86_64-pc-windows-msvc.
- Visual Studio C++ desktop development tools and Windows SDK.
- A working Vulkan driver; Vulkan SDK for validation and shader tools.
- `glslc` from the SDK, found through `VULKAN_SDK` or `PATH`. Cargo compiles
  the GLSL sources in `crates/jade-render-vulkan/shaders/` into SPIR-V automatically.
  Generated shaders stay in Cargo build output and are embedded in the executable.

From this directory:

```powershell
cargo check --workspace
cargo fmt --all --check
cargo clippy --workspace -- -D warnings
cargo run -p jade-viewer -- --probe --validation
cargo run -p jade-viewer -- --validation
cargo run -p jade-viewer -- --validation --smoke
```

Rustup was installed without modifying PATH on the initial host. If needed,
use `$env:USERPROFILE\.cargo\bin\cargo.exe` explicitly, or configure RustRover
with that toolchain location.

`Cargo.lock` is generated and should be committed for this application workspace.
The toolchain is pinned to the tested Rust 1.99.1 release.

## Native menus and Camera02

See [current workflow and controls](../README-dev.md#native-menu-prototype).

```powershell
cargo run -p jade-viewer -- --scene ../reports/engine-textures-20261028/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --validation
```

The UI and 3D scene share one render pass/window. UI is alpha blended after the
scene with depth disabled. OJUI0003 supplies sprite/glyph atlases; Rust composes
profile, main, options, keyboard/gamepad, game, graphics and sound screens with
confirmations. Gamma, filtering, window size and V-Sync apply only after Back -> Yes;
editing and Default Settings change a draft, No discards it, Cancel keeps editing.
Unsupported controls are disabled. Profiles/preferences persist in an independent
`.ojmenu` file beside the bundle. No Python controller is needed at runtime.
Keyboard bindings are stored only; gamepad input and gameplay remain absent.
Start New Game plays a baked 60 Hz, nine-second Camera02 trajectory and holds the
balcony pose. Escape resets it. No gameplay follows. Letterboxing preserves 4:3
rendering and mouse coordinates. The smoke mode accelerates time to exercise the
transition plus return in 80 frames; ordinary playback uses elapsed real time.

## Decoded menu geometry (initial import, 2026-10-27)

The local import tested on 2026-10-27 contains **40 objects / 14,994 triangles / 31
texture layers**, taken from the existing research export. Camera02 uses its initial
stored pose and the provisional vertical FOV 59.37908 degrees. No new manual camera
rotation is applied. Both scene and panel passed the 80-frame resize smoke test
with zero Vulkan validation errors; the scene was also inspected in the window.
Five Rust tests and two Python bridge tests pass.

Generate a new local package from the repository root (replace paths for your exports):

```powershell
python src/export_engine_scene.py reports/menu-fixture-materials-20261025/renders/horizontal-angle reports/camera02-transition-20261026/preview/poses.json reports/engine-menu-20261027
```

The output directory must not already exist. The command reads existing decoded
exports; it does not extract archives or modify game files. On the current host the
package has already been generated. From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/engine-menu-20261027/menu.ojscene --validation
cargo run -p jade-viewer -- --scene ../reports/engine-menu-20261027/menu.ojscene --validation --smoke
cargo test --workspace
```

Without `--scene`, the original diagnostic panel remains available. Scene data is
never automatically loaded from the game installation. The package, manifest and
capture live under ignored `reports/`; `*.ojscene` is also ignored globally.

The initial version-1 import excluded three fog panels and three fixture objects.
The newer `export_engine_materials.py` / OJSCN003 import includes all six, with
source-over fog and two-pass fixtures; its `--time` selects a fixed material phase.
Remaining limits:
original mipmaps are not imported. OJSCN003 preserves native base dimensions;
`--texture-filter nearest|linear|trilinear` compares ordinary nearest/base-level,
linear/base-level (default), and generated trilinear mipmaps. Fog/fixture samplers
remain linear; UI uses linear/base-level sampling. Colors are
those of the research export, not verified native lighting. UI and camera playback are enabled with `--menu`; gameplay remains absent. The near/far planes (0.1/1000) are chosen research values.
See [interchange specification](../docs/formats/engine-scene-interchange.md).

## Boundaries and milestones

- `jade-assets`: bounded, backend-independent local scene package reader.
- `jade-render`: backend-independent diagnostic data.
- `jade-render-vulkan`: ash loader, explicit validation request, instance
  lifetime and adapter enumeration, plus device/surface/swapchain presentation.
  The diagnostic panel uses a graphics pipeline, render pass, sampled sRGB image,
  descriptor set and staging upload. Panel vertices come from the vertex shader;
  imported scene vertices use a buffer, texture array and camera push constants.
  Panel resources are currently rebuilt on swapchain recreation for simplicity.
  One frame is in flight, with a submission fence and per-image presentation
  semaphores. Out-of-date swapchains are recreated; zero-sized windows skip drawing.
- `jade-viewer`: winit event loop and diagnostic entry point. Close the window
  normally, or use --smoke for two automatic resize requests and exit after 80
  presented frames. Vulkan errors make the smoke process return failure.
  Game-derived resources are loaded only from an explicit local `--scene` package.

Next: faithful lighting/materials, remaining settings backed by real systems, UI scaling and general animation systems.
Create `assets/scene/game-specific` crates when their first implemented behavior
is introduced. Keep the existing research tools in the repository root.

Original assets remain outside source control. Tests of Windows do not establish
Linux/macOS compatibility. No desktop settings or Vulkan layer registry entries
are modified by the probe.

## Texture validation (2026-10-28)

The 38 scene textures use individual GPU images at their decoded dimensions.
The interchange's padding is never uploaded as texture content. Mipmap generation
checks sRGB format blit/filter support and fails explicitly if unavailable.
Generated chains are diagnostic; alpha coverage and original mip data are not
recovered. GPU resources are still rebuilt on swapchain resize, including each
texture upload; this prototype path is not optimized yet.

```powershell
cargo run -p jade-viewer -- --scene ../reports/engine-textures-20261028/menu.ojscene --menu ../reports/engine-ui-20261028/menu.ojui --texture-filter trilinear --validation
```

All three settings passed 80-frame resize/Camera02 smoke tests with zero Vulkan
validation errors on the AMD RX 9070 XT. The checker and OJSCN001 regression runs
also passed. See [evidence and limitations](../docs/observations/2026-10-28-native-textures.md).

## Color comparison

Keep the scene and filter identical and compare `--color-pipeline srgb` (default)
with `--color-pipeline legacy-unorm`. The latter uses UNORM textures and an UNORM
attachment, including blending, while retaining SRGB_NONLINEAR presentation.
Neither mode is yet established as the original live menu configuration.
Without OJUI0003 native menus the default bypasses gamma. Optional `--gamma 0..100` or `--settings PATH`
emulates the recovered output ramp after composition without changing desktop gamma. Mipmap blits
use the selected texture format, so prefer `--texture-filter linear` when isolating
the base-image color comparison. Unsupported presentation formats fail explicitly.
See [native trace and limits](../docs/observations/2026-10-28-color-pipeline.md).

## Legacy gamma bridge

OJUI0003 has native gamma controls and rejects `--settings`. The bridge below
remains available with the OJUI0001 bundle or scene-only viewer for comparisons.

The Python full-menu simulation can publish a gamma preview/committed value to
an OpenJade `.ojsettings` file. Run it first, then pass that same file to
`jade-viewer --settings PATH`. The viewer polls at 100 ms and retains its last
valid value on a malformed/missing update. Only gamma is linked so far.
`--gamma 0..100` is an alternative fixed-value option; it cannot be combined with
`--settings`. Without either (and without OJUI0003), gamma is bypassed. A second render subpass applies
the ramp after scene and UI blending in display-value space, preserving alpha.
See [launch commands](../README-dev.md#live-gamma-control-from-the-python-menus)
and [native calculation](../docs/observations/2026-10-28-gamma-bridge.md).

## Interface scaling (2026-10-29)

The current OJUI0003 bundle preserves the 1024x256 logo and 128x128 cursor pixels,
and includes twelve MFT variants. Rust selects a font based on actual letterboxed
viewport pixels. Linear UI sampling replaces nearest filtering; other scene
filtering remains separate. The 800x600 layout and sprite display sizes are retained.
Use the new bundle path above; old OJUI0001/2 bundles do not contain these resources.
Their loaders remain supported. See [export commands](../README-dev.md#native-menu-prototype)
and [evidence/limits](../docs/observations/2026-10-29-ui-scaling.md).
