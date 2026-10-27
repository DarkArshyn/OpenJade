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

## Decoded menu geometry

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

Current limits: three fog panels and three multi-stage fixture objects are excluded;
textures use nearest sampling and 512x512 array layers without mipmaps. Colors are
those of the research export, not verified native lighting. There is no UI overlay,
animated camera or gameplay. The near/far planes (0.1/1000) are chosen research values.
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

Next: material fidelity, transparent fog, Camera02 transition controls and menu integration.
Create `assets/scene/game-specific` crates when their first implemented behavior
is introduced. Keep the existing research tools in the repository root.

Original assets remain outside source control. Tests of Windows do not establish
Linux/macOS compatibility. No desktop settings or Vulkan layer registry entries
are modified by the probe.
