# Measured menu blur integrated in Vulkan

Date: 2026-11-03. The implementation follows the
[native construction audit](2026-11-03-menu-blur-construction.md) and the
[independent reference](../../src/reconstruct_menu_blur.py).

## Runtime behavior

For prepared menu packages with the native trunk sidecar, `legacy-unorm` now
enables the measured current-frame blur by default. `--no-menu-blur` disables
it for direct comparisons. It is deliberately disabled in the diagnostic sRGB
pipeline: the captured operations use stored UNORM values, and a different
transfer function has not been validated. This option is not connected to the
simulated Special Effects setting. Other scene packages remain unchanged.

The scene is rendered and stored before UI. A new `menu_blur.rs` owner provides
three 512x512 RGBA8 UNORM targets: the scene copy S and working targets A/B.
Five draws implement the copy plus the four native passes. Native 256/255 gains,
three offsets, weights, clamp/linear sampling, 128/256 partial writes, preserved
current-frame A border and black B padding match the reference. Each frame
initializes its own content; no history image is sampled.

The result is blended over the scene with alpha 104/255 and RGB-only writes.
UI, logo, cursor and text are then drawn sharply; gamma is applied afterward.
With menu UI enabled, the blur source/composite use the same centered 4:3 viewport,
so letterbox bars are outside the effect. Working targets and descriptors are
rebuilt with the existing swapchain resources on resize. Explicit dependencies
separate attachment writes, texture reads and the resumed UI/gamma render pass.

The measured construction was established on the fixed menu. The prototype also
keeps this effect during Camera02 preview; native parity during that transition
has not been separately validated. The additive multiresolution chain and fog
particles remain absent. The blur currently copies the OpenJade scene as rendered;
once the additive chain is implemented, its source must remain the pre-additive
scene copy, matching the native pass order.

## Numerical and runtime validation

Ignored evidence: `reports/vulkan-menu-blur-20261103/` and
`reports/vulkan-menu-blur-final-20261103/`.
A resumed verification is recorded in `reports/vulkan-menu-blur-resume-20261103/`,
including a fresh native UI capture. It reproduces the same maximum one-byte
GPU/reference error and fixed-frame stability. The UI/gamma resize smoke test
again completed 80 frames with zero validation errors.

At fixed animation time zero, the unblurred Vulkan framebuffer is fed into the
independent CPU reference and its final source-over composite. Against the blurred
Vulkan output at 800x600: maximum RGB error 1/255, mean absolute error 0.0157354
byte levels, and all channels within one byte. At (505,407), input RGB is
(82,125,155); both the reference and Vulkan produce (75,115,145).
This validates the Vulkan effect against its measured algorithm, not complete
GOG scene fidelity. No captured GOG background image is used by the runtime.

Frames 11 and 21 are identical with time fixed, with and without the blur.
The GPU integration test checks this along with the numeric comparison and
validation output. Captures at 800x600 and with the UI at 1600x1200 show no Vulkan
validation errors. A smoke run with gamma 50, native UI and resize/recreation
presents 80 frames with zero validation errors. All 45 Rust tests pass; fmt and
clippy (all targets, warnings denied) pass. The renderer was tested on Windows
with an AMD Radeon RX 9070 XT; other platforms are not validated.

## Launch and comparison

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/palm-runtime-20261101/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

Add `--no-menu-blur` to compare. No resource re-export is needed when the prepared
native sidecars are already present. Rebuild the viewer to obtain the new shaders.

From the repository root, after building the viewer:

```powershell
python tests/integration_menu_blur.py reports/palm-runtime-20261101/menu.ojscene reports/menu-blur-gpu-check
```

Use a new output directory. This optional GPU regression requires the Vulkan SDK
screenshot layer, NumPy and Pillow; Python is not needed to run the prepared viewer.
The test captures both paths, checks fixed-time stability and compares the result
against the reference within a maximum two-byte tolerance.
