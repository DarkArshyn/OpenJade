# OpenJade developer guide

[Project overview](README.md) · [Native engine guide](engine/README.md) · [Research observations](docs/observations/)

**Documentation snapshot: 2026-11-15**

This document describes the current development workflows and points to dated evidence, it's not a compatibility guarantee. Original game inputs remain read-only.

## Development environment

- Windows remains the primary development and integration platform.
- The Rust engine has undergone initial native build, test and Vulkan validation on Windows, Linux and macOS. See [Platform and tool validation](#platform-and-tool-validation).
- Windows PowerShell 5.1 remains the documented research shell.
- Rust/Cargo, ash, winit and Vulkan are used for the native engine. Platform-specific build requirements are documented in [engine/README.md](engine/README.md#prerequisites).
- The Vulkan SDK provides `glslc` for shader compilation. Khronos validation layers can be enabled for runtime checks.
- Python with Pillow and NumPy supports research and exports; tkinter is used by the separate Python menu simulation.
- C# helpers support selected research decoding tasks.
- Ghidra and a compatible JDK support optional native static analysis.
- Source comments and documentation are written in English. Dates use `YYYY-MM-DD`.

Tool versions and platform requirements may vary. Consult the engine guide before configuring a new development environment.

## Start here

| Goal | Entry point |
| --- | --- |
| Build or test the Rust workspace | [Engine guide](engine/README.md) and [Testing and validation](#testing-and-validation) |
| Launch a prepared menu in Vulkan | [Native menu workflow](#native-menu-workflow) |
| Explore the Prince actor preview | [Actor diagnostics](#actor-diagnostics) |
| Extract or inspect game resources | [Research tool setup](#research-tool-setup) and [Resource workflows](#resource-workflows) |
| Run the older Python menu simulation | [Legacy Python simulation](#optional-python-menu-simulation) |
| Understand current capabilities | [Current implementation](#current-implementation) |
| Investigate technical evidence | [Research and evidence index](#research-and-evidence-index) |
| See development priorities | [Roadmap and milestones](#roadmap-and-milestones) |

> [!IMPORTANT]
> A fresh clone contains neither original game resources nor generated `reports/` or native scene/UI bundles.  
Rust source-level checks can be run without distributing game assets and prepared visual previews require locally generated data.  
Many examples below refer to **previously generated research reports**, not inputs available in a fresh checkout.

## Platform and tool validation

Development remains primarily focused on Windows.

Initial native validation of the Rust engine on Linux and macOS was successfully completed on **2026-11-14**. These results don't establish complete cross-platform support.

| Platform | Verified Rust engine scope (2026-11-14) | Research tooling scope |
| --- | --- | --- |
| Windows | Primary development and integration platform<br>Local Vulkan viewer and research workflows | Windows PowerShell 5.1, Python and associated tools are used here |
| Linux | Rust workspace built<br>Menu and actor Vulkan rendering checked: **67 unit tests passed**<br>No Vulkan validation errors reported | PowerShell 7 and Python tools **not tested** on Linux |
| macOS | Rust workspace built without macOS-specific source changes<br>Menu and separate Prince scene rendered: **67 unit tests passed**<br>Three runtime tests passed and no Vulkan validation errors reported | PowerShell 7 and Python tools **not tested** on macOS |

For platform-specific build dependencies and current launch options, see [engine/README.md](engine/README.md#prerequisites). Avoid interpreting the cross-platform Rust tests as validation of the full preparation pipeline.

## Current implementation

The table describes **implementation scope**, not original-game fidelity. A verified native calculation or an error-free Vulkan run does not by itself establish pixel parity or a complete game system.

| Area | Current scope | Important limitations |
| --- | --- | --- |
| Archives and formats | Tested BF/BIG extraction, recognized POP-LZO decoding, selected MGM/DDS/MFT inspection | Limited to validated formats and resource layouts. BIG v37 is the principal tested archive version for Sands of Time |
| Native menu | Rust-drawn screens, profiles, keyboard-label capture, confirmations, gamma/filtering/resolution/V-Sync persistence | No real game saves, gameplay bindings, audio or gameplay |
| Scene and camera | Reconstructed Sands of Time menu scene, texture/material paths, Camera02 nine-second baked transition | Original runtime scripting, full render-state and lighting parity unverified |
| Scene effects | Selected animated UVs, palms, curtains, rain/splash, birds/flies, pollen, fog, cursor glow, fixtures and partial postprocessing | Native timing/random-state synchronization and full effect composition unresolved |
| Prince diagnostics | Original-resource animation/skinning, constrained dagger, animated-normal lighting and prepared balcony integration | Native startup/loop timing, general scene-light loading, remaining secondary controllers and gameplay are incomplete |
| Platform coverage | Windows primary; bounded Linux/macOS Rust build, test and Vulkan checks on 2026-11-14 | Python/PowerShell not validated cross-platform; no future compatibility guarantee |

**Validation vocabulary:**
- `implemented` = present within a specified scope
- `experimental` = bounded diagnostic/prototype
- `research only` = observed but not fully implemented
- `planned` = future work

*Original-game fidelity is a separate claim and must be independently supported.*

## First-time setup

1. Clone the repository and consult [engine/README.md](engine/README.md#prerequisites) for toolchain and Vulkan prerequisites.
2. For source-only checks, start with [Testing and validation](#testing-and-validation).
3. For a visual preview, use original resources from your own installation and prepare the local exports described under [Native menu workflow](#native-menu-workflow) or [Actor diagnostics](#actor-diagnostics).
4. For archives, resource analysis and research exports, follow [Research tool setup](#research-tool-setup) on the documented Windows research toolchain.

Exporters commonly require **previously generated research reports**. They do not replace archive extraction or automatically reconstruct the full dependency chain from a clean clone. Output directories generally must be new; generated files belong under ignored `reports/`, never under `game/`.

## Project structure

| Location | Responsibility |
| --- | --- |
| `engine/` | Rust workspace, package readers, Vulkan renderer and native viewer |
| `src/` | Research decoders/exporters, helpers and legacy Python simulation |
| `tools/` | Research command wrappers and Ghidra helpers |
| `tests/` | Synthetic unit tests and optional local-data/GPU integration checks |
| `docs/formats/` | Observed resource layouts and OpenJade interchange formats |
| `docs/observations/` | Dated research findings; historical limitations are date-specific |
| `docs/decisions/`, `references/` | Architecture decisions and external research provenance |
| `reports/` | Local generated reports, exports, bundles and captures; excluded from Git |
| `game/` | Read-only, user-provided game files; excluded from Git |

### Local game-directory naming

The current game directory naming convention is `game/TSoT-GOG`. This is an example of a local input path, not a bundled dependency.

The following naming convention is proposed for additional GOG game installations:

| Directory | Game |
| --- | --- |
| `game/TSoT-GOG` | Prince of Persia: The Sands of Time |
| `game/WW-GOG` | Prince of Persia: Warrior Within |
| `game/T2T-GOG` | Prince of Persia: The Two Thrones |
| `game/BGE-GOG` | Beyond Good & Evil |

For other game editions, no naming convention has been finalized yet. The following naming scheme is proposed as a possible convention:
- `game/TSoT-UbiConnect` : TSoT Ubisoft Connect version
- `game/TSoT-CD` : TSoT CD version

These names are provisional and may change as the project evolves.

> [!NOTE]
> Other game editions have not been validated. Their archive layouts, executable differences, dependencies and potential DRM-related constraints require separate investigation.

## Roadmap and milestones

| Workstream | Current evidence / implementation | Next validation boundary |
| --- | --- | --- |
| Resource foundations | BF/BIG, POP-LZO and selected formats implemented for tested inputs | Additional versions/layouts with bounded fixtures and byte-level checks |
| Native menu | Native Rust UI, profiles/options persistence and Camera02 playback | Compare missing behaviors and integrate only systems that exist |
| Menu rendering | Selected scene geometry/materials, transparency, textures, fog, blur and additive composition | Native lighting and whole-frame rendering fidelity |
| Dynamic menu effects | Selected cloth/vegetation, particles, animated fixtures and cursor glow | Native timing, activation, RNG and full-frame comparison |
| Prince actor diagnostics | Source-resource geometry and sampled Rust skeletal animation/skinning | Secondary controllers, dynamic actor lighting and broader actor runtime |
| Core game systems | Not playable; no general gameplay runtime | Investigate scene/object logic, collision, player control, audio and game loading |
| Other games | Objectives only | Independent version/resource/runtime research for each title |
| Cross-platform | Initial Windows/Linux/macOS Rust validation in recorded configurations | Repeat on new versions, hardware and drivers; validate preparation tools separately |

There is no reliable overall completion percentage, release date or guaranteed schedule. Test counts and resource coverage are not proxies for overall engine completeness.

## Testing and validation

From `engine/`:

```shell
cargo fmt --all --check
cargo clippy --workspace -- -D warnings
cargo test --workspace
```

These commands are *instructions*, not claims that every check ran on every platform. The specific Linux/macOS outcomes above come from the **2026-11-14** validation. Local Vulkan smoke tests additionally require the relevant GPU/driver, validation layers where applicable, and prepared scene bundles.

From the repository root, using the **documented Windows research environment**:

```powershell
python -m unittest discover -s tests -p 'test_export_engine*.py'
python -m unittest discover -s tests -p 'test_native_mips.py'
python -m unittest discover -s tests -p 'test_menu_postprocess.py'
python -m unittest discover -s tests -p 'test_menu_blur.py'
```

Many other test scripts require private reports or game-derived fixtures. Read the corresponding [observation](docs/observations/) before running them. Historical numbers such as 27, 30, 37 or 57 passing tests describe **earlier runs**, not the size of the latest suite. A passing Vulkan smoke run does not prove original-game pixel parity.

## Native menu workflow

The Rust viewer draws the reconstructed menu over the 3D scene in one window. It includes profile creation/selection, navigation, supported display settings and confirmation screens. The disabled Load Game, audio and unsupported controls do not silently perform gameplay operations. Python is **not needed at runtime** when a prepared native menu bundle is available.

### Preparing assets

The following is an **existing-report workflow**, not a clean-clone build recipe. Run from the repository root on the documented research environment; replace report paths with your own generated inputs and use new output directories.

```powershell
python src/assemble_menu_scene.py reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin reports/menu-sky-moon-20261030/source-final --yaw 0 --pitch 0 --fov 59.37908
python src/export_engine_materials.py reports/menu-sky-moon-20261030/source-final reports/camera02-transition-20261026/preview/poses.json reports/palm-runtime-20261101 --palm-source reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin
python src/export_engine_ui.py reports/menu-effects-fix-8796132f9b234657a4a88218be9cb644 reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin reports/engine-ui-20261028
foreach ($size in 10,12,14,16,18,20,22,24,26,28,36,48) {
    .\tools\Read-MFT.ps1 -Path "reports/POPData-extracted/menu/fonts/atlantis mf regular $size.mft" -OutputDirectory "reports/native-ui-fonts-20261029/$size" | Out-Null
}
python src/export_native_menu.py reports/menu-effects-fix-8796132f9b234657a4a88218be9cb644 reports/engine-ui-20261028/menu.ojui reports/engine-ui-scale-20261029 --fonts reports/native-ui-fonts-20261029
```

> [!NOTE]
> These paths document the development workstation's research lineage. A newcomer cannot execute them from a fresh clone without first reproducing the required extractions and reports. Some older bundles do not include later fog, cursor or actor sidecars.

### Launching the prepared viewer

From `engine/`, with a locally prepared scene and UI bundle:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-fog-cursor-20261108/menu.ojscene --menu ../reports/menu-fog-cursor-20261108/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

For the newer fixture-animation snapshot, see [fixture integration](docs/observations/2026-11-10-vulkan-fixtures.md). The command above is a **documented example**, not a verified universal latest package. Keep sidecars (`menu.fog`, `menu.trunk`, `menu.fixtures`, etc., where required) beside the scene. The [engine guide](engine/README.md) is the reference for current CLI arguments.

**Controls and behavior:** mouse/keyboard navigation, up to five OpenJade-only menu profiles, keyboard-binding label capture, and gamma/filtering/window-size/V-Sync settings committed after confirmation. Values are saved in a local `.ojmenu` file rather than the game's original profiles. Starting a new game only plays the precomputed Camera02 transition; it does not start gameplay. The viewport remains 4:3 through resizing.

**Rendering limitations:** material/filtering options are diagnostic, fog/particle RNG phase and activation are not fully synchronized to the original game, and lighting/transparency/postprocessing fidelity is incomplete. Avoid describing scene snapshots with older counts (such as 48 objects) as the current universal inventory.

### Viewer diagnostics

| Option | Purpose / caveat |
| --- | --- |
| `--validation` | Enable available Vulkan validation checks |
| `--smoke` | Execute the viewer's bounded smoke workflow with prepared assets |
| `--color-pipeline legacy-unorm` | Compare stored-value color processing in diagnostic scenes |
| `--texture-filter nearest\|linear\|trilinear` | Compare available texture-filter paths; not a recovered original setting |
| `--no-rain` | Isolate native rain contribution |
| `--no-fog` | Disable dynamic fog emitters (not all fog paths) |
| `--no-menu-blur` | Bypass menu blur and associated composite path |
| `--no-menu-additive` | Isolate additive path where supported |

See the [engine guide](engine/README.md#viewer-command-line-options) and the linked [rendering observations](#research-and-evidence-index) for precise scope and required sidecars.

## Actor diagnostics

These are **experimental validation previews**, not playable characters or general-purpose runtime actor loading. The Prince diagnostic evaluates 62 body bones and 35 body transform channels from a 37-track clip. The dagger uses source-backed sheath constraints, and vertex RGB updates with animated normals. Light parameters still come from a native capture; startup timing, other secondary controllers and action selection remain incomplete.

From `engine/`, with the previously prepared local `.ojscene` and `.actor` sidecar:

```powershell
cargo run -p jade-viewer -- --scene ../reports/prince-sheath-animation-20261114/prince.ojscene --color-pipeline legacy-unorm --validation
```

Keep the `.actor`, `.sheath` and `.actorlight` sidecars beside the isolated scene.
The prepared balcony integration additionally uses `.placement` and preserves the menu's effect sidecars:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-prince-20261115/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

This example requires existing local exports. The original checkpoint height is retained;
its small measured difference from native ground placement is unresolved. See the
[sheath, lighting and balcony validation](docs/observations/2026-11-15-prince-sheath-balcony.md)
for preparation, tests and the distinction between measured calculations and diagnostic timing.
This Windows update has not been revalidated on Linux/macOS.

Research lineage and reproducible fixture requirements:

- [Isolated head preview](docs/observations/2026-11-13-actor-head-preview.md)
- [Original-resource Prince preview](docs/observations/2026-11-13-prince-resource-preview.md)
- [Source-skeleton animation diagnostic](docs/observations/2026-11-14-prince-skeletal-animation.md)
- [Lighting contribution measurements](docs/observations/2026-11-11-menu-light-contributions.md)
- [Ambient cache and shaders](docs/observations/2026-11-13-ambient-cache-shaders.md)

## Research tool setup

The workflow below is documented for **Windows PowerShell 5.1**. It hasn't been validated with PowerShell 7 on Linux/macOS

The Python tools haven't been executed there in the recorded cross-platform checks.

From the repository root:

```powershell
$pythonPath = (Get-Command python -ErrorAction Stop).Source
& $pythonPath -m pip install Pillow numpy
& $pythonPath -c "import tkinter, PIL, numpy; print('Research dependencies available')"
```

Some decoding helpers also use C#. Ghidra and a JDK are optional for static analysis, neither is required for a prepared Vulkan viewer. Keep original archives read-only: create new destinations in `reports/`.

The exact Python package and native development prerequisites are described in the relevant scripts and [engine guide](engine/README.md#prerequisites).

## Resource workflows

These are **selected entry points**, not a complete dependency-free export pipeline. Run PowerShell commands from the repository root, adapting input paths to your own legally obtained game installation. Use fresh output directories.

| Task | Command / starting point | Specification or evidence |
| --- | --- | --- |
| Inspect BF index | `.\tools\Read-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF` | [BF format](docs/formats/BF.md) |
| Extract BF entry | `.\tools\Extract-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF -Entry gamepads.dat -OutputDirectory .\reports\gamepads` | [BF baseline](docs/observations/2026-10-09-bf-baseline.md) |
| Inspect BIG | `.\tools\Read-BIG.ps1 -Path .\game\TSoT-GOG\prince.bf -OutputDirectory .\reports\prince-index` | [BIG format](docs/formats/BIG.md) |
| Extract BIG stored bytes | `.\tools\Extract-BIG.ps1 -Path .\game\TSoT-GOG\prince.bf -Id '0x03090337' -OutputDirectory .\reports\versiontag` | [Stored extraction](docs/observations/2026-10-09-big-extraction.md) |
| POP-LZO expansion | `.\tools\Expand-POPLzo.ps1 -Path .\reports\lzo-input\FD3F0142.stored.bin -OutputDirectory .\reports\lzo-decoded` | [POP-LZO format](docs/formats/POP-LZO.md) |
| Inspect MGM | `.\tools\Read-MGM.ps1 -Path .\reports\mgm-input\menu\pop4common.mgm -OutputDirectory .\reports\mgm-common` | [MGM format](docs/formats/MGM.md) |
| Inspect DDS | `.\tools\Export-DDSPreview.ps1 -Path .\reports\POPData-extracted\menu\texture\pop.dds -OutputDirectory .\reports\logo-preview` | [DDS format](docs/formats/DDS.md) |
| Inspect MFT | `.\tools\Read-MFT.ps1 -Path <extracted-font.mft> -OutputDirectory .\reports\font-atlas` | [MFT observations](docs/observations/2026-10-13-mft.md) |

For less common workflows, see [Text DAT / INI](docs/formats/Text-DAT.md), [MGM resource links](docs/formats/MGM-resource-links.md), [BIG compression investigation](docs/formats/BIG-compression.md), and the dated [research observations](docs/observations/). The original tools distinguish stored extraction from decompression: extracting bytes does not automatically decode a resource.

### Optional Python menu simulation

The Python/Tk simulation is a **historical research/reference interface**, separate from the native Rust menu. It uses previously exported menu resources, approximates layouts from screenshots and does not control a playable game. Its optional legacy gamma bridge is not required for native menu settings.

```powershell
# From the repository root, with an existing complete report:
$pythonPath = (Get-Command python -ErrorAction Stop).Source
$reportDirectory = Read-Host 'Path to the generated menu prototype report'
.\tools\Show-MenuSimulation.ps1 -ReportDirectory $reportDirectory -PythonPath $pythonPath
```

The report must contain `experiment.json`, `menus-assets/catalog.json` and available referenced resources; screenshots alone are insufficient. See [original simulation evidence](docs/observations/2026-10-16-complete-menu-simulation.md) and [gamma bridge](docs/observations/2026-10-28-gamma-bridge.md).

## Research and evidence index

**Rule:** dated findings describe the evidence available at their date. Later tests may refine or overturn an earlier hypothesis. Current implementation claims belong in [Current implementation](#current-implementation), not in an old observation treated as permanently authoritative.

| Topic | Evidence to consult |
| --- | --- |
| Original resource formats | [BF](docs/formats/BF.md), [BIG](docs/formats/BIG.md), [POP-LZO](docs/formats/POP-LZO.md), [MGM](docs/formats/MGM.md), [DDS](docs/formats/DDS.md) |
| UI and settings | [Native menus](docs/observations/2026-10-28-native-menus.md), [UI scaling](docs/observations/2026-10-29-ui-scaling.md), [gamma](docs/observations/2026-10-28-gamma-bridge.md) |
| Camera and scene | [Camera02 transition](docs/observations/2026-10-26-camera02-transition-preview.md), [scene completeness](docs/observations/2026-10-29-menu-completeness.md), [transparency](docs/observations/2026-10-30-camera-transparency.md) |
| Scene textures and lighting | [Texture checks](docs/observations/2026-10-28-native-textures.md), [mipmap comparisons](docs/observations/2026-11-03-native-mips-aligned.md), [light receivers](docs/observations/2026-11-11-menu-light-receivers.md) |
| Scene effects | [Palms](docs/observations/2026-11-01-palm-runtime.md), [rain](docs/observations/2026-11-03-vulkan-menu-rain.md), [fog/cursor](docs/observations/2026-11-08-vulkan-fog-cursor.md), [fixtures](docs/observations/2026-11-10-vulkan-fixtures.md) |
| Postprocessing | [Blur](docs/observations/2026-11-03-vulkan-menu-blur.md), [additive](docs/observations/2026-11-03-vulkan-menu-additive.md) |
| Prince actor | [Sheath and balcony integration](docs/observations/2026-11-15-prince-sheath-balcony.md), [Resource preview](docs/observations/2026-11-13-prince-resource-preview.md), [skeletal animation](docs/observations/2026-11-14-prince-skeletal-animation.md), [actor light terms](docs/observations/2026-11-12-actor-light-terms.md) |
| Design decisions and prior work | [Architecture decisions](docs/decisions/), [External research provenance](references/) |

Detailed historical test counts, hashes, byte offsets, resource IDs, fixture requirements and unresolved hypotheses remain in their **dated source observations**. This guide intentionally does not duplicate a chronological research log.

## Contributing and documenting research

- Keep original inputs read-only; never commit game binaries, extracted copyrighted resources, personal captures or generated bundles.
- Document source edition, resource ID, hash, command, expected output, comparison method and test environment where applicable.
- Distinguish **observed behavior**, **implementation**, **hypothesis**, and **unverified interpretation**.
- State the platform, hardware, driver and date for Vulkan/GPU checks. Do not generalize a passing check beyond its measured scope.
- When a later finding supersedes an earlier one, update the **current status** here and link a new dated observation; preserve the earlier record as historical evidence.
- Verify Markdown links, example commands and test-scope claims before publication.

For licensing and legal conditions, see [LICENSE](LICENSE) and the [main README disclaimer](README.md#license--legal-disclaimer).
