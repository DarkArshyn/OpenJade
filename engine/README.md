# OpenJade Native Engine

[Project overview](../README.md) · [Developer guide](../README-dev.md) · [Research observations](../docs/observations/)

**Documentation snapshot: 2026-11-15**

The `engine/` directory contains OpenJade's experimental native engine implementation, developed in **Rust** with **Vulkan** rendering through `ash`.

The current implementation focuses on reconstructing selected functionality of Ubisoft's Jade Engine, using *Prince of Persia: The Sands of Time* (PC GOG edition) as its initial reference.

The Rust workspace currently provides:

- Native Vulkan rendering of decoded 3D scenes, textures and materials.
- An interactive main menu with profiles, configurable display settings and local persistence.
- Camera02 playback and selected runtime animations.
- Animated vegetation, curtains, particles, birds, fog and light-fixture effects.
- Selected scene postprocessing, including blur and partial additive composition.
- Experimental Prince rendering, skeletal animation and skinning using original game resources.
- Bounded resource-package readers, automated tests and diagnostic rendering tools.

> [!IMPORTANT]
> OpenJade is not yet a playable game.
>
> General gameplay, collision, level loading, audio and complete actor systems remain unimplemented.
>
> Native rendering and animation experiments do not establish full compatibility or visual fidelity with the original engine.

## Platform support

Windows remains the primary development and integration platform.

Initial native Rust engine validation on Linux and macOS was successfully completed on **2026-11-14**.

| Platform | Validation scope |
| --- | --- |
| Windows | Primary development and integration environment. Vulkan rendering and local testing |
| Linux | Rust workspace built: **67 unit tests passed**. Menu and actor Vulkan rendering verified |
| macOS | Rust workspace built: **67 unit tests passed**. Menu and Prince rendering verified. Three runtime tests passed |

No Vulkan validation errors were reported during the recorded Linux and macOS checks.

### Tested configurations

**Linux**
- Manjaro Linux (x86_64).
- AMD Radeon RX 9070 XT.
- Mesa RADV Vulkan driver.

**macOS**
- macOS 27.2.1 on Apple Silicon (M3 Pro).
- KosmicKrisp Vulkan driver.
- Vulkan SDK 1.4.363.1.
- No macOS-specific source modifications required for the tested Rust workspace.

These results apply only to the engine implementation and tested configurations available on the validation date.

Broader Linux and macOS support remains experimental. Future changes, hardware configurations and drivers require independent validation.

PowerShell and Python research tools were not tested on Linux or macOS as part of these validations. Their preparation workflows must not be considered cross-platform validated.

See the [developer guide](../README-dev.md#platform-and-tool-validation) for the validation scope and tooling limitations.

## Prerequisites

### Common requirements

- Rust and Cargo installed through [rustup](https://rustup.rs/).
- A Vulkan-capable graphics device and working Vulkan driver.
- The `glslc` shader compiler, provided by the `Vulkan SDK` or an appropriate platform package.
- Platform-specific development dependencies required by the Rust workspace.

Cargo compiles GLSL shaders from `crates/jade-render-vulkan/shaders/` into SPIR-V during the build. Generated shaders are stored in Cargo build output and embedded in the executable.

### Windows

The primary Windows development environment uses:

- Rust/Cargo 1.99.1.
- MSVC Rust target (`x86_64-pc-windows-msvc`).
- Visual Studio C++ development tools and Windows SDK.
- Vulkan SDK and a compatible Vulkan driver.

The initial validation environment used an AMD Radeon RX 9070 XT.

### Linux

The tested Manjaro Linux development environment uses:
- Rust/Cargo 1.99.1.
- Mesa RADV on an AMD Radeon RX 9070 XT.
- `glslc` provided by the shaderc package.
- Vulkan development headers and validation layers.

Install the documented development dependencies:

```shell
sudo pacman -Syu
sudo pacman -S --needed base-devel git rustup shaderc vulkan-headers vulkan-validation-layers pkgconf wayland libxkbcommon libxcb
```

On an AMD GPU using Mesa RADV, ensure that the vulkan-radeon driver package is installed:

```shell
sudo pacman -S --needed vulkan-radeon
```

If Rust has not yet been configured, install the default stable toolchain:

```shell
rustup default stable
```

Verify the available tools:

```shell
rustc --version
cargo --version
glslc --version
```

The listed packages reflect the tested Manjaro development environment. Package names and dependency requirements may differ across Linux distributions.

These instructions do not establish compatibility with every Linux distribution, GPU or Vulkan driver.

### macOS

The tested macOS development environment uses:

- Rust/Cargo 1.99.1.
- XCode Command Line Tools.
- [LunarG Vulkan SDK 1.4.363.1](https://sdk.lunarg.com/sdk/download/1.4.363.1/mac/vulkansdk-macos-1.4.363.1.zip) with the KosmicKrisp Vulkan driver.

Install the Xcode Command Line Tools:

```shell
xcode-select --install
```

Install Rust through rustup if it is not already available:

```shell
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Install the LunarG Vulkan SDK with KosmicKrisp enabled.

After installation, configure the Vulkan environment:

```shell
# Replace <version> with the installed Vulkan SDK version.
source "$HOME/VulkanSDK/<version>/setup-env.sh"

# Explicitly select the KosmicKrisp Vulkan driver.
export VK_DRIVER_FILES="$VULKAN_SDK/share/vulkan/icd.d/libkosmickrisp_icd.json"
```

Verify the development tools:

```shell
rustc --version
cargo --version
glslc --version
```

KosmicKrisp uses Apple's Metal API to provide Vulkan functionality on supported Apple Silicon hardware. Khronos has officially deprecated [MoltenVK](https://github.com/KhronosGroup/MoltenVK) and now recommends KosmicKrisp for Vulkan on Apple Silicon Macs.

> [!IMPORTANT]
> OpenJade's macOS development and validation currently target Apple Silicon (ARM64) exclusively.
>
> Intel-based Macs are outside the project's supported and planned validation scope.

### Validation scope

The recorded cross-platform results apply only to the tested Rust engine implementation, hardware, operating systems and Vulkan drivers as of **2026-11-14**.

They do not establish compatibility with future engine revisions or validate the PowerShell and Python research workflows on Linux or macOS.

See [Platform support](#platform-support) and [developer validation](../README-dev.md#platform-and-tool-validation) for details.

## Building and testing

Run the following commands from `engine/`.

### Workspace checks

```shell
cargo check --workspace
cargo fmt --all --check
cargo clippy --workspace -- -D warnings
cargo test --workspace
```

These commands check compilation, formatting, Clippy diagnostics and the Rust workspace tests.

They are instructions, not a claim that every command was executed on every supported platform.

For platform-specific test results, see [Platform support](#platform-support).

### Vulkan diagnostic viewer

```shell
cargo run -p jade-viewer -- --validation
```

Without a scene package, the viewer retains its original Vulkan diagnostic panel.

The diagnostic displays a textured square on a blue-grey background and can be used to inspect basic presentation, texture sampling and resizing.

This diagnostic is retained for regression testing; it doesn't represent the current scope of the native engine.

### Automated viewer smoke test

```shell
cargo run -p jade-viewer -- --validation --smoke
```

The smoke workflow exercises a bounded sequence of rendering and resize operations.

When native scene/menu packages are provided, the test can also exercise the corresponding viewer paths.

A successful smoke test verifies the tested runtime behavior and available Vulkan validation checks. It doesn't demonstrate original-game pixel parity.

## Running the viewer

Game-derived resources are not distributed with OpenJade.

A fresh checkout contains no original game assets, decoded scenes, generated menu bundles or research reports.

Native previews require locally prepared OpenJade packages generated from the user's own game installation.

See the [native menu workflow](../README-dev.md#native-menu-workflow) for resource preparation and the required research dependencies.

### Scene-only preview

```shell
cargo run -p jade-viewer -- --scene PATH_TO_SCENE --validation
```

This loads a prepared scene package without requiring the native menu interface.

### Native menu

```shell
cargo run -p jade-viewer -- --scene PATH_TO_SCENE --menu PATH_TO_MENU --color-pipeline legacy-unorm --validation
```

The native viewer renders the reconstructed 3D menu environment and its interactive interface in a single window.

The example below uses a previously prepared local research snapshot:

```shell
cargo run -p jade-viewer -- --scene ../reports/menu-fog-cursor-20261108/menu.ojscene --menu ../reports/menu-fog-cursor-20261108/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

This path is an example from recorded development work, not a universal latest package or a clean-checkout launch command.

Newer scene exports may contain additional effects and require corresponding sidecar files.

### Prince actor diagnostic

The viewer also supports isolated Prince rendering and animation experiments using prepared original-resource data.

```shell
cargo run -p jade-viewer -- --scene ../reports/prince-sheath-animation-20261114/prince.ojscene --color-pipeline legacy-unorm --validation
```

Keep `prince.actor`, `prince.sheath` and `prince.actorlight` beside the corresponding scene package. Prepared balcony scenes additionally use an actor `.placement` sidecar. The latest export derives initial height from the source balcony collision triangle; the runtime applies that matrix to animated vertices. This is not a continuous collision solver. See [grounded integration and launch command](../docs/observations/2026-11-15-prince-grounded-integration.md).

The sheath diagnostic caches its first cycle and retains controller state across subsequent body loops; fractional and backwards queries remain deterministic. See [native loop-state validation](../docs/observations/2026-11-15-prince-sheath-loop.md). To measure actor CPU cost independently of Vulkan, run `cargo run -p jade-assets --example actor_timing -- PATH_TO_PRINCE.actor`. See [performance evidence and scope](../docs/observations/2026-11-15-prince-performance.md).

Development builds optimize `jade-assets` animation math while retaining debug checks. Optional bounded GPU/CPU profiling uses `OPENJADE_PROFILE_FRAMES=600`; `OPENJADE_PROFILE_PRESENT=fifo` or `immediate` enables an explicit comparison without changing saved settings. The viewer prints timings and exits. Unset these variables for ordinary use. GPU timestamps measure command execution, not physical display latency. See the performance evidence above for commands and limitations.


This diagnostic evaluates skeletal animation and skinning in Rust. It is not a playable character implementation or a general-purpose actor runtime.

See [Prince skeletal animation research](../docs/observations/2026-11-14-prince-skeletal-animation.md) and [sheath, lighting and balcony integration](../docs/observations/2026-11-15-prince-sheath-balcony.md). The [developer actor workflow](../README-dev.md#actor-diagnostics) includes the prepared menu launch command.

## Workspace architecture

The Rust workspace separates resource loading, rendering abstractions, the Vulkan backend and viewer-level behavior.

| Crate | Responsibility |
| --- | --- |
| `jade-assets` | Bounded loading and validation of local OpenJade resource packages |
| `jade-render` | Backend-independent rendering data and diagnostic structures |
| `jade-render-vulkan` | Vulkan device management, GPU resources, pipelines, presentation and rendering |
| `jade-viewer` | Window/event handling, input, native menu, diagnostics and viewer state |

These boundaries describe the current implementation and may evolve as the engine gains additional functionality.

### Design principles

- Separate resource decoding and preparation from native runtime rendering.
- Validate package boundaries and reject malformed inputs.
- Keep rendering infrastructure independent of game-specific behavior where practical.
- Distinguish verified original-engine behavior from independent implementation decisions.
- Avoid adding speculative general-purpose systems before their requirements are established.
- Preserve compatibility with supported older diagnostic packages where practical.

The long-term goal is to distinguish reusable Jade Engine functionality from game-specific implementations.

## Implemented systems

OpenJade distinguishes between reusable engine infrastructure and implementations developed for individual games.

**A system described as reusable is not necessarily validated across multiple Jade Engine titles.** Current native development and game-resource validation primarily use *Prince of Persia: The Sands of Time*.

### Core engine systems

These components form the foundation of the native Rust engine and are intended to support future game integrations where technically appropriate.

#### Resource loading and package validation

- Bounded loading of locally prepared OpenJade scene and interface packages.
- Validation of supported package layouts, sizes and input boundaries.
- Support for selected historical package versions and optional runtime sidecars.
- Separation of offline resource preparation from native runtime loading.

The current viewer doesn't directly load original game archives. BF/BIG extraction, POP-LZO decoding and resource-format research are handled by the repository's separate research tools.

These tools contribute to the project's Jade Engine research but are not yet integrated as general-purpose native archive loaders.

#### Vulkan rendering and materials

The Rust/Vulkan renderer provides:

- Decoded 3D geometry and texture rendering.
- Vertex colors, depth testing and selected material blending.
- Native-dimension texture uploads and selected original mipmap chains.
- Configurable texture-filtering diagnostics.
- Camera-relative transparent-pass sorting.
- Selected fog, blur and additive-composition paths.
- Diagnostic sRGB and legacy UNORM color-processing modes.
- Post-composition gamma processing.

The rendering infrastructure is intended to be reusable. However, most currently reconstructed material states and visual comparisons are derived from Sands of Time.

Original Jade Engine rendering behavior and compatibility with other titles remain unverified.

#### Animation foundations

The native engine includes selected runtime animation capabilities:

- Time-dependent material UV offsets.
- Vertex deformation for supported animated geometry.
- Hierarchical skeletal transformations.
- Animation-key interpolation and runtime vertex skinning.
- Selected attachment-transform calculations.
- Bounded particle update and rendering mechanisms.

These capabilities currently serve specific menu and Prince diagnostics.

They do not yet constitute a complete, game-independent animation framework or reproduce the original Jade Engine animation runtime.

#### Window, input and runtime infrastructure

The native viewer provides:

- Window creation and Vulkan presentation through `winit`.
- Resize handling and swapchain recreation.
- Keyboard and mouse input for supported viewer operations.
- Runtime state management for the current prototypes.
- Vulkan validation and automated smoke-test entry points.
- Local configuration persistence for the native menu.

General gameplay input, gamepad handling and complete game-state management remain future work.

### Game-specific implementations

The following systems use resources and observed behaviors from individual games.

Their implementation doesn't imply compatibility with other Jade Engine titles.

#### Prince of Persia: The Sands of Time (2003)

**Native menu**

The experimental native menu includes:

- Interactive main menu and supported option screens.
- Local profile creation, selection and deletion.
- Keyboard-binding label capture.
- Gamma, texture filtering, window resolution and V-Sync settings.
- Confirmation dialogs and persistent OpenJade configuration.
- Resolution-aware bitmap font selection.
- Animated cursor and glow effects.

The interface is rendered directly in Rust and doesn't require a Python controller at runtime when prepared resources are available.

Profiles are independent of original game saves. Unsupported audio, gameplay and gamepad-dependent controls remain disabled.

**Menu scene and visual effects**

The reconstructed menu environment includes selected original geometry, textures, materials and visual effects:

- Animated palms, vegetation and hanging curtains.
- Rain, splash, pollen and other particle effects.
- Mesh birds, bird particles and fly swarms.
- Dynamic fog emitters and scene fog panels.
- Animated suspended fixtures.
- Selected blur and additive postprocessing effects.
- Camera-relative transparency handling.

These systems reproduce bounded observations from the original game.

Exact scene lighting, runtime synchronization, effect activation and complete visual fidelity remain unresolved.

**Camera02 transition**

Selecting Start New Game plays a reconstructed nine-second Camera02 animation toward the balcony.

The current implementation uses 541 precomputed poses sampled at 60 Hz.

The transition ends at the balcony without loading a playable level.

The original scripting runtime, complete activation chain and subsequent gameplay are not implemented.

**Prince actor diagnostics**

The experimental actor preview supports:

- Selected original-resource geometry and textures.
- Hierarchical skeletal animation in Rust.
- Runtime skinning of supported character geometry.
- Selected sword and support attachment transforms.
- Sampled pose and transformation comparisons.

The current diagnostic evaluates 62 body bones and 35 transform channels from an original 37-track clip.

The source-backed dagger controller and animated-normal lighting also run in a prepared balcony scene. Lighting parameters retain capture provenance. Native startup/loop timing, other secondary controllers, complete equipment behavior, general scene-light loading and gameplay remain incomplete.

This remains a diagnostic integration, not a playable Prince implementation.

#### Prince of Persia: Warrior Within (2004)

Not implemented.

Future research will need to establish relevant engine-version differences, resource layouts and game-specific runtime requirements.

#### Prince of Persia: The Two Thrones (2005)

Not implemented.

Compatibility requirements have not been established through the current native engine validation.

#### Beyond Good & Evil (2003)

Not implemented.

Future research may investigate its resource formats, engine behavior and opportunities for reusing existing OpenJade infrastructure.

### Compatibility boundaries

Current support is based primarily on the reference Sands of Time PC GOG edition.

Reusable Rust components do not automatically establish binary-format compatibility, equivalent engine behavior or rendering fidelity across different Jade Engine games.

Each additional title will require independent research and validation before compatibility can be claimed.

For the project's compatibility objectives and roadmap, see the [main README](../README.md). For format research and validation evidence, see the [developer guide](../README-dev.md).

## Resource packages and sidecars

The native viewer reads locally generated OpenJade interchange packages rather than directly loading an original game installation.

The package readers validate supported layouts and input boundaries.

### Main packages

| Package | Purpose |
| --- | --- |
| `.ojscene` | Scene geometry, materials, textures and selected runtime scene data |
| `.ojui` | Prepared menu sprites, fonts, interface assets and associated UI data |
| `.ojmenu` | Local OpenJade menu profiles and persisted settings |

Selected historical package revisions remain readable for compatibility and regression testing.

Not all features are available in older revisions.

### Optional scene sidecars

Depending on the prepared scene, additional files may carry selected native-resource data or runtime parameters.

Examples include:

- `menu.leaf` and `menu.trunk` for verified native texture mip data.
- `menu.rain` and `menu.splash` for particle emitters.
- `menu.fog` for dynamic fog emitters.
- `menu.flight` for mesh bird animation data.
- `menu.pollen` for luminous particles.
- `menu.fixtures` for fixture animation.
- `.actor`, `.sheath` and `.actorlight` for Prince animation, constrained equipment and animated-normal lighting.
- `.placement` for a bounded actor vertex range and rigid scene placement.

See [actor sidecar formats](../docs/formats/actor-diagnostic-sidecars.md).

Other effect or deformation sidecars may also be present, depending on the export.

Keep required sidecars beside their associated scene package.

Package versioning, binary layout details and exact sidecar requirements are documented in the [format specifications](../docs/formats/) and dated [research observations](../docs/observations/).

## Viewer command-line options

The viewer provides diagnostic and comparison options for the implemented rendering systems.

| Option | Purpose |
| --- | --- |
| `--probe` | Run the available adapter/device diagnostic |
| `--validation` | Request available Vulkan validation checks |
| `--smoke` | Run bounded automated viewer checks |
| `--scene PATH` | Load a prepared OpenJade scene |
| `--menu PATH` | Load a prepared native menu |
| `--color-pipeline srgb` | Use the explicit sRGB comparison path |
| `--color-pipeline legacy-unorm` | Use the stored-value color comparison path |
| `--texture-filter nearest` | Nearest filtering for supported ordinary materials |
| `--texture-filter linear` | Linear base-level filtering |
| `--texture-filter trilinear` | Enable supported mipmap filtering |
| `--gamma VALUE` | Apply a fixed diagnostic gamma value |
| `--no-rain` | Disable native rain for comparison |
| `--no-splashes` | Disable splash effects for comparison |
| `--no-fog` | Disable dynamic fog emitters |
| `--no-menu-blur` | Disable the menu blur/composite path |
| `--no-menu-additive` | Disable the supported additive contribution |

Some options require specific package versions or optional sidecars.

The filtering and color-processing modes are diagnostic comparisons, not necessarily recovered original-game configuration values.

### Legacy gamma bridge

The separate Python menu simulation can communicate a diagnostic gamma value to older viewer configurations through an OpenJade `.ojsettings` file.

This workflow is retained for historical comparison and is not required by the current native menu.

Native menu bundles manage gamma directly and reject conflicting external settings control.

See [gamma bridge research](../docs/observations/2026-10-28-gamma-bridge.md).

## Testing and validation

The project uses several complementary validation methods.

| Method | Purpose |
| --- | --- |
| Rust unit tests | Validate package readers, data structures, calculations and supported behavior |
| Synthetic fixtures | Exercise bounded inputs without requiring original game data |
| Native differential comparisons | Compare selected calculations or decoded values against observed original-engine behavior |
| Vulkan validation | Detect supported Vulkan API and resource-use errors |
| GPU smoke tests | Exercise rendering, resizing, transitions and selected runtime paths |
| Visual comparisons | Investigate differences between reconstructed and original-game output |

These methods establish different levels of evidence.

An error-free Vulkan run doesn't prove pixel accuracy, and a matching isolated calculation doesn't establish complete engine behavior.

Test counts and results should always be associated with their execution date, environment and scope.

Recorded validation details and reproducible research procedures are available in the [developer guide](../README-dev.md#testing-and-validation) and [dated observations](../docs/observations/).

## Known limitations

The native engine remains experimental.

Major limitations include:

- No playable Sands of Time implementation.
- No general-purpose level loading or gameplay runtime.
- No player input, collision or interaction systems connected to gameplay.
- No functional native game-audio system.
- No complete original game scripting runtime.
- No general-purpose actor loader or completed character-controller system.
- Incomplete secondary animation, attachment and dynamic actor-lighting support.
- Incomplete original lighting, material, particle and postprocessing fidelity.
- Incomplete synchronization of runtime effect activation, timing and random state.
- Limited validation across hardware, drivers and operating systems.
- Dependence on locally prepared resource packages for the current viewer.

The implementation and its limitations will evolve as further original-engine behavior is researched and validated.

## Technical references

- [Developer guide](../README-dev.md) — setup, research workflows, testing and milestones.
- [Format documentation](../docs/formats/) — native resource findings and OpenJade interchange formats.
- [Research observations](../docs/observations/) — dated experiments, evidence and validation.
- [Architecture decisions](../docs/decisions/) — recorded implementation choices.
- [External research references](../references/) — documented prior work and provenance.
- [Project overview](../README.md) — objectives, compatibility roadmap and legal disclaimer.

Original game files remain outside version control and must be supplied from a legally obtained installation.

OpenJade doesn't distribute proprietary game assets or original engine source code.