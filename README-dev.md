# OpenJade developer guide

[Project overview](README.md) · [Native engine guide](engine/README.md) · [Research observations](docs/observations/)

**Documentation snapshot: 2026-11-26**

This document describes the current development workflows and points to dated evidence. It's not a compatibility guarantee. Original game inputs remain read-only.

## Development environment

- Windows remains the primary development and integration platform.
- The Rust engine has undergone native build, test and Vulkan validation on Windows, Linux and macOS. See [Platform and tool validation](#platform-and-tool-validation).
- PowerShell 7.6 LTS is the required research shell, replacing Windows PowerShell 5.1.
- Core PowerShell research workflows and selected Python workflows have been validated on Windows x86_64, Linux x86_64 and macOS ARM64.
- Rust/Cargo, ash, winit and Vulkan are used for the native engine. Platform-specific build requirements are documented in [engine/README.md](engine/README.md#prerequisites).
- The Vulkan SDK provides `glslc` for shader compilation. Khronos validation layers can be enabled for runtime checks.
- Python with Pillow and NumPy supports research and exports; tkinter is used by the separate Python menu simulation.
- Managed C# helpers support selected resource decoding and PNG generation tasks without requiring System.Drawing.
- Ghidra and a compatible JDK support optional native static analysis.
- Source comments and documentation are written in English. Dates use `YYYY-MM-DD`.
- Repository-level line-ending policies are defined in `.gitattributes`, using LF for cross-platform source files.

Tool versions and platform requirements may vary. Consult the engine guide and [Research tool setup](#research-tool-setup) before configuring a new development environment.

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

Development remains primarily focused on Windows. Cross-platform validation covers both the native engine and selected research and resource-preparation workflows.

### Native engine validation

Initial native validation of the Rust engine on Linux and macOS was successfully completed on **2026-11-14**. These results don't establish complete cross-platform support.

| Platform | Verified Rust engine scope (2026-11-14) |
| --- | --- |
| Windows x86_64 | Primary development and integration platform<br>Local Vulkan viewer and research workflows |
| Linux x86_64 | Rust workspace built<br>Menu and actor Vulkan rendering checked<br>**67 unit tests passed**<br>No Vulkan validation errors reported |
| macOS ARM64 | Rust workspace built without macOS-specific source changes<br>Menu and separate Prince scene rendered<br>**67 unit tests passed**<br>Three runtime tests passed and no Vulkan validation errors reported |

Additional Linux ARM64 testing was performed on a Raspberry Pi 4B. This was an architectural validation rather than a supported deployment target. The tested hardware didn't provide sufficient performance for a viable runtime experience.

For platform-specific build dependencies, hardware configurations and current launch options, see [engine/README.md](engine/README.md).

### Research tool validation

Following Microsoft's [announcement of the deprecation of Windows PowerShell 5.1](https://support.microsoft.com/en-us/servicing/os/windows/docs/2026/11/kb5137172-windows-powershell-5-1-deprecation) on 2026-11-17, the research toolchain was migrated to **PowerShell 7.6 LTS** to improve long-term maintainability and facilitate cross-platform development.

The final common source version was validated on **2026-11-26**.

#### Validated environments

| Component | Windows x86_64 | Manjaro Linux x86_64 | macOS ARM64 |
| --- | --- | --- | --- |
| PowerShell | 7.6.6 | 7.6.9 | 7.6.6 |
| .NET runtime | 10.0.12 | 10.0.14 | 10.0.12 |
| Python | 3.15.0 | 3.14.10 | 3.15.2 |
| Pillow | 12.3.0 | 13.0.0 | 13.0.0 |
| NumPy | 2.5.4 | 2.5.4 | 2.5.5 |
| Tk | 9.0 | 8.6 | 9.0 |
| Ghidra | 12.1.4 | 12.1.4 | 12.1.4 |
| JDK | 21.0.12.1+1 | 21.0.13.0.3+1 | 21.0.2+13 |

All three environments used native execution for the tested workflows.

These versions describe the recorded validation environments, not mandatory exact dependency versions or an exhaustive compatibility matrix. The .NET runtime versions correspond to those used by the installed PowerShell distributions. A separate .NET SDK installation is not required for the managed C# helpers used by the validated research workflows.

#### Validation results

| Test suite | Synthetic checks per platform | Windows | Linux | macOS |
| --- | ---: | ---: | ---: | ---: |
| BF | 68 | 150 | 150 | 150 |
| BIG | 33 | 38 | 38 | 38 |
| BIG compression | 25 | 34 | 34 | 34 |
| BIG extraction | 37 | 42 | 42 | 42 |
| DDS preview | 36 | 101 | 101 | 101 |
| MFT | 34 | 59 | 59 | 59 |
| MFT text preview | 14 | 39 | 39 | 39 |
| MGM | 54 | 73 | 73 | 73 |
| MGM resource links | 30 | 44 | 44 | 44 |
| POP-LZO | 44 | 120 | 46 | 46 |
| Text DAT | 23 | 26 | 26 | 26 |
| **Total** | **398** | **726** | **652** | **652** |

The platform columns describe runs with original game resources and available optional references. These totals include synthetic checks and should not be added to the separate synthetic-only counts.

All 39 PowerShell scripts and modules passed syntax validation on each platform.

The additional Windows checks include 33 differential cases against an optional native miniLZO reference implementation.

Additional validation covered:

- 3,308 valid BIG archive entries.
- 3,302 original resources containing 7,461 recognized POP-LZO blocks.
- 63 original DDS textures and 68 exact RGBA comparisons against Pillow.
- 199 resolved MGM resource references, with no reported attention items.
- Menu prototype generation and five menu scene exports.
- Effects resource generation.
- Python prototype and complete simulation GUI smoke tests.
- Manual launch of both Python interfaces.
- Ghidra Headless camera analysis, including successful decompilation of two referenced functions.

#### Common source integrity

A common manifest of 145 source files was used throughout the final validation campaign:

| Source type | File count |
| --- | ---: |
| PowerShell scripts | 31 |
| PowerShell modules | 8 |
| C# | 2 |
| Python | 86 |
| Java | 18 |
| **Total** | **145** |

SHA-256 checksums confirmed that the selected source files were identical across all three environments before and after validation.

The manifest covered the selected research source tree, not every file in the repository or every external dependency.

Following integration into the primary Windows repository, all 145 reference source files were verified again and all 398 synthetic checks passed.

### Scope and limitations

- Native engine support remains experimental outside the primary development environment.
- Research validation covers selected formats, original resources and workflows, not every Python or Java script.
- The optional native miniLZO reference was tested on **Windows only**.
- Ghidra requires platform-specific dependencies. The tested macOS distribution required compilation of native ARM64 components.
- Ghidra reported non-blocking internal analysis diagnostics; successful targeted analysis does not imply complete executable analysis.
- MFT comparison workflows executed successfully, but original-game visual fidelity remains unverified.
- Cross-platform validation does not establish game playability or guarantee compatibility with future versions.

For research tool installation and reproducible commands, see [Research tool setup](#research-tool-setup) and [Testing and validation](#testing-and-validation).

## Current implementation

The table describes **implementation scope**, not original-game fidelity. A verified native calculation or an error-free Vulkan run does not by itself establish pixel parity or a complete game system.

| Area | Current scope | Important limitations |
| --- | --- | --- |
| Archives and formats | Tested BF/BIG extraction, recognized POP-LZO decoding, selected MGM/DDS/MFT inspection | Limited to validated formats and resource layouts. BIG v37 is the principal tested archive version for Sands of Time |
| Native menu | Rust-drawn screens, profiles, keyboard-label capture, confirmations, gamma/filtering/resolution/V-Sync persistence | No real game saves, gameplay bindings, audio or gameplay |
| Scene and camera | Reconstructed Sands of Time menu scene, texture/material paths, Camera02 nine-second baked transition | Original runtime scripting, full render-state and lighting parity unverified |
| Scene effects | Selected animated UVs, palms, curtains, rain/splash, birds/flies, pollen, fog, cursor glow, fixtures and partial postprocessing | Native timing/random-state synchronization and full effect composition unresolved |
| Prince diagnostics | Original-resource animation/skinning, equipment, lighting, sword reflection and the observed menu idle sequence tied to Camera02 | Absolute startup phase, general action selection, remaining secondary controllers and gameplay are incomplete |
| Platform coverage | Windows primary; bounded native Rust/Vulkan validation and common PowerShell 7.6 LTS research tool validation on Windows, Linux and macOS | Selected hardware, formats and workflows only; no exhaustive toolchain or future compatibility guarantee |

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
4. For archives, resource analysis and research exports, install [PowerShell 7.6 LTS](https://learn.microsoft.com/en-us/powershell/scripting/install/install-powershell?view=powershell-7.6) and follow [Research tool setup](#research-tool-setup) for the relevant platform.

Exporters commonly require **previously generated research reports**. They do not replace archive extraction or automatically reconstruct the full dependency chain from a clean clone. Output directories generally must be new; generated files belong under ignored `reports/`, never under `game/`.

## Project structure

| Location | Responsibility |
| --- | --- |
| `.gitattributes` | Repository-level line-ending policies for cross-platform source files and platform-specific scripts |
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
| Cross-platform | Initial Windows/Linux/macOS Rust validation in recorded configurations; common PowerShell 7.6 LTS research workflows validated on all three platforms | Repeat validation on new versions, hardware and drivers; extend coverage of remaining preparation and research workflows |

There is no reliable overall completion percentage, release date or guaranteed schedule. Test counts and resource coverage are not proxies for overall engine completeness.

## Testing and validation

### Native Rust engine

From `engine/`:

```shell
cargo fmt --all --check
cargo clippy --workspace -- -D warnings
cargo test --workspace
```

These commands are *instructions*, not claims that every check ran on every platform. The specific Linux/macOS outcomes above come from the **2026-11-14** validation. Local Vulkan smoke tests additionally require the relevant GPU/driver, validation layers where applicable, and prepared scene bundles.

### PowerShell research tools

Run the following commands from the repository root using PowerShell 7.6 LTS.

#### Environment verification

```powershell
$PSVersionTable
[System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture
[System.Runtime.InteropServices.RuntimeInformation]::FrameworkDescription
```

#### Syntax validation

```powershell
$psFiles = @(Get-ChildItem -Path ./src,./tests,./tools -Recurse -File -Include *.ps1,*.psm1)
$parseErrors = @(foreach ($file in $psFiles) { $tokens = $null; $errors = $null; $null = [System.Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors); $errors })
if ($parseErrors.Count -eq 0) { "PASS: All $($psFiles.Count) PowerShell files parsed successfully." } else { $parseErrors; throw "PowerShell syntax validation failed." }
```

The 2026-11-26 validation covered 39 PowerShell files.

#### Synthetic tests

```powershell
Get-ChildItem -LiteralPath ./tests -File -Filter 'Test-*.ps1' | Sort-Object Name | ForEach-Object { $timer = [Diagnostics.Stopwatch]::StartNew(); & pwsh -NoProfile -File $_.FullName; $exitCode = $LASTEXITCODE; $timer.Stop(); [PSCustomObject]@{Test=$_.Name;ExitCode=$exitCode;Seconds=[math]::Round($timer.Elapsed.TotalSeconds,2)} }
```

Each test suite runs in a separate PowerShell process. All exit codes must be zero.

The common source version validated on 2026-11-26 passed 398 synthetic checks across eleven test suites on Windows, Linux and macOS.

#### Tests with original game resources

The following commands require local game archives and previously extracted menu resources.

```powershell
$bf = './game/TSoT-GOG/POPData.BF'
$big = './game/TSoT-GOG/prince.bf'
$menu = './reports/POPData-extracted/menu'
$textures = Join-Path $menu 'texture'
$fonts = Join-Path $menu 'fonts'
$textDat = './reports/POPData-extracted/pop4pclocal.dat'
```

Select `$pythonPath` as described in [Research tool setup](#research-tool-setup).

```powershell
pwsh -NoProfile -File ./tests/Test-BF.ps1 -GameArchive $bf
pwsh -NoProfile -File ./tests/Test-BIG.ps1 -GameArchive $big
pwsh -NoProfile -File ./tests/Test-BIGCompression.ps1 -GameArchive $big
pwsh -NoProfile -File ./tests/Test-BIGExtraction.ps1 -GameArchive $big
pwsh -NoProfile -File ./tests/Test-DDSPreview.ps1 -TextureDirectory $textures -PythonPath $pythonPath
pwsh -NoProfile -File ./tests/Test-MFT.ps1 -FontDirectory $fonts
pwsh -NoProfile -File ./tests/Test-MFTTextPreview.ps1 -FontDirectory $fonts
pwsh -NoProfile -File ./tests/Test-MGM.ps1 -MgmDirectory $menu
pwsh -NoProfile -File ./tests/Test-MGMLinks.ps1 -MenuDirectory $menu
pwsh -NoProfile -File ./tests/Test-POPLzo.ps1 -GameArchive $big
pwsh -NoProfile -File ./tests/Test-TextDat.ps1 -TextDat $textDat
```

The original game resources must remain read-only. Generated reports are written to local output directories.

#### Optional native miniLZO reference (Windows)

The managed POP-LZO decoder does not require the native miniLZO reference library.

An optional differential comparison can be performed with a compatible, previously built reference DLL:

```powershell
$referenceDll = Read-Host 'Path to the native miniLZO reference DLL'
pwsh -NoProfile -File ./tests/Test-POPLzo.ps1 -GameArchive $big -ReferenceDll $referenceDll
```

The optional reference build helper is located at `tests/reference/Build-LzoReference.ps1` and currently targets Windows/MSVC.

The recorded cross-platform campaign used an existing reference DLL on Windows. Building the reference library and running the native comparison on Linux or macOS were not part of this validation.

### Python tests

From the repository root, using the Python interpreter configured in [Research tool setup](#research-tool-setup):

```powershell
& $pythonPath -m unittest discover -s tests -p 'test_export_engine*.py'
& $pythonPath -m unittest discover -s tests -p 'test_native_mips.py'
& $pythonPath -m unittest discover -s tests -p 'test_menu_postprocess.py'
& $pythonPath -m unittest discover -s tests -p 'test_menu_blur.py'
```

These are selected test entry points. They were not all independently executed as part of the 2026-11-26 cross-platform research tool validation.

Many other test scripts require private reports or game-derived fixtures. Read the corresponding [observation](docs/observations/) before running them.

Historical numbers such as 27, 30, 37 or 57 passing tests describe **earlier runs**, not the size of the latest suite.

A passing Vulkan smoke run does not prove original-game pixel parity.

## Native menu workflow

The Rust viewer draws the reconstructed menu over the 3D scene in one window. It includes profile creation/selection, navigation, supported display settings and confirmation screens. The disabled Load Game, audio and unsupported controls do not silently perform gameplay operations. Python is **not needed at runtime** when a prepared native menu bundle is available.

### Preparing assets

The following is an **existing-report workflow**, not a clean-clone build recipe. Run from the repository root on the documented research environment; replace report paths with your own generated inputs and use new output directories.

Run these commands using PowerShell 7.6 LTS and the Python interpreter configured in [Research tool setup](#research-tool-setup).

```powershell
& $pythonPath src/assemble_menu_scene.py reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin reports/menu-sky-moon-20261030/source-final --yaw 0 --pitch 0 --fov 59.37908
& $pythonPath src/export_engine_materials.py reports/menu-sky-moon-20261030/source-final reports/camera02-transition-20261026/preview/poses.json reports/palm-runtime-20261101 --palm-source reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin
& $pythonPath src/export_engine_ui.py reports/menu-effects-fix-8796132f9b234657a4a88218be9cb644 reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin reports/engine-ui-20261028
foreach ($size in 10,12,14,16,18,20,22,24,26,28,36,48) { ./tools/Read-MFT.ps1 -Path "reports/POPData-extracted/menu/fonts/atlantis mf regular $size.mft" -OutputDirectory "reports/native-ui-fonts-20261029/$size" | Out-Null }
& $pythonPath src/export_native_menu.py reports/menu-effects-fix-8796132f9b234657a4a88218be9cb644 reports/engine-ui-20261028/menu.ojui reports/engine-ui-scale-20261029 --fonts reports/native-ui-fonts-20261029
```

> [!NOTE]
> These paths document the development workstation's research lineage. A newcomer cannot execute them from a fresh clone without first reproducing the required extractions and reports. Some older bundles do not include later fog, cursor or actor sidecars. The complete historical native asset-preparation pipeline was not independently revalidated on all platforms during the PowerShell migration.

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

These are **experimental validation previews**, not playable characters or general-purpose runtime actor loading. The Prince diagnostic evaluates 62 body bones and 35 body transform channels from a 37-track clip. The dagger uses source-backed sheath constraints, and vertex RGB updates with animated normals. Isolated legacy previews retain captured light parameters; absolute startup phase, other secondary controllers and general action selection remain incomplete. The optional `.idle` sidecar adds the 36 local transform channels of the alternative clip and the observed menu-only sequence.

From `engine/`, with the previously prepared local `.ojscene` and `.actor` sidecar:

```powershell
cargo run -p jade-viewer -- --scene ../reports/prince-sheath-animation-20261114/prince.ojscene --color-pipeline legacy-unorm --validation
```

Keep the `.actor`, `.sheath` and `.actorlight` sidecars beside the isolated scene.

Prepared menu exports now derive ambient and three named light terms from original scene resources. The generated direction now follows the active camera for the placed Prince. [Runtime and final-pixel checks](docs/observations/2026-11-17-camera02-runtime-light.md) verify the calculation, its visible contribution in Vulkan and endpoint frame timings. [Receiver origins](docs/observations/2026-11-17-receiver-origins.md) now follow Spine2 for the support and Head for the face; nine other components retain the Prince root. The [sword reflection](docs/observations/2026-11-17-sword-vulkan.md) now follows animated normals and the active camera, using its original texture and tint; the other two sword groups retain their measured diffuse material. [Material selection](docs/observations/2026-11-22-sword-material-selection.md) now uses the verified last-entry bound from the original pack instead of a sword-specific material key. GOG final-pixel parity remains unresolved. See [source-light validation](docs/observations/2026-11-17-prince-source-lights.md).

The [native idle-action selection investigation](docs/observations/2026-11-22-prince-idle-selection.md) identifies the controller selecting action 24 / clip `330010E9`, its observed direct restart and rate override. [Initialization and return captures](docs/observations/2026-11-23-prince-idle-init-return.md) distinguish original-resource defaults from native table filling and verify action 24 returning to action 1 with controller-selected repetition counts and rates. [Terminal-loop validation](docs/observations/2026-11-23-prince-idle-terminal.md) confirms restart at stage 3 and identifies the event-driven idle gate. [Return-blend and sender measurements](docs/observations/2026-11-23-prince-blend-activation.md) establish the 11/60-second nominal blend, fitted rotation/pelvis agreement, retained spine translation and `Menu_Start_Demo` as the captured event sender. [Clock and menu synchronization](docs/observations/2026-11-23-prince-clock-menu-sync.md) validates 101 rotation poses without phase fitting and ties suspension/reset to Camera02 entry/exit messages in a synchronized New Game capture. [Vulkan idle integration](docs/observations/2026-11-24-prince-idle-vulkan.md) now adds the second source clip, the bounded menu sequence and Camera02 completion/reset routing. The actor remains a non-playable diagnostic; complete native startup phase and general action selection are not implemented.

The first diagnostic sheath cycle is prepared at load time; subsequent steps preserve controller state across body loops. Development builds optimize animation math, and CPU simulation overlaps the previous GPU submission. Bounded profiling distinguishes GPU command execution from CPU presentation waits. See the [CPU performance measurements and limits](docs/observations/2026-11-15-prince-performance.md).

The prepared balcony integration additionally uses `.placement` and preserves the menu's effect sidecars:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-prince-idle-20261123/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

This example requires existing local exports, including `menu.idle` for the new sequence. `src/export_prince_idle.py <scene.actor> <scene.idle> --sources <decoded actor bundles>` generates that optional sidecar from original clip `330010E9`, verifies the source skeleton and refuses to overwrite an existing output. Older packages without `.idle` retain their previous single-clip preview. This example requires existing local exports. Initial Z now comes from the original balcony collision triangle; checkpoint XY and orientation are preserved. The engine applies this placement to animated vertices through `.placement`. See [grounded menu integration](docs/observations/2026-11-15-prince-grounded-integration.md) for source/native comparisons, tests and frame timings. Continuous collision and player movement are not implemented.
The prepared Prince idle menu has subsequently undergone native runtime validation on Linux and macOS. This doesn't establish complete cross-platform validation of every actor diagnostic or preparation workflow.

[Balcony pose and loop validation](docs/observations/2026-11-15-prince-balcony-validation.md) adds five repeatable endpoint-camera captures and a live frame-time baseline. The measured four-second sheath reset discontinuity is corrected by [preserving controller state across native-observed body loops](docs/observations/2026-11-15-prince-sheath-loop.md). Initial collision-based placement is validated; dynamic collision, native startup and general action selection remain unimplemented or unvalidated. See the [ground-placement measurements](docs/observations/2026-11-15-prince-ground-placement.md): the native origin is stable; the subsequent [native contact capture](docs/observations/2026-11-15-prince-native-ground.md) identifies the supporting collision triangle.

Research lineage and reproducible fixture requirements:

- [Isolated head preview](docs/observations/2026-11-13-actor-head-preview.md)
- [Original-resource Prince preview](docs/observations/2026-11-13-prince-resource-preview.md)
- [Source-skeleton animation diagnostic](docs/observations/2026-11-14-prince-skeletal-animation.md)
- [Lighting contribution measurements](docs/observations/2026-11-11-menu-light-contributions.md)
- [Ambient cache and shaders](docs/observations/2026-11-13-ambient-cache-shaders.md)

## Research tool setup

The research toolchain requires **PowerShell 7.6 LTS**.

The core research workflows have been validated on Windows x86_64, Manjaro Linux x86_64 and macOS ARM64. See [Platform and tool validation](#platform-and-tool-validation) for the recorded environments and validation scope.

### PowerShell

Install PowerShell 7.6 LTS for your operating system and architecture:

- [PowerShell releases](https://github.com/PowerShell/PowerShell/releases)
- [Official installation documentation](https://learn.microsoft.com/en-us/powershell/scripting/install/install-powershell?view=powershell-7.6)

On Manjaro Linux, the `powershell-lts-bin` package was used during validation:

```shell
pamac build powershell-lts-bin
```

This is a distribution-specific community package, not a universal Linux installation procedure.

Launch PowerShell from your terminal:

```shell
pwsh
```

Verify the installed version:

```powershell
$PSVersionTable
```

Use `pwsh`, not `powershell.exe`, for the project's research workflows.

### Python

Python is required for selected resource preparation, comparison and research workflows. Pillow and NumPy provide image-processing and numerical functionality. tkinter is required for the optional Python GUI tools.

Python 3.14 and 3.15 were used during the recorded validation campaign. These versions describe the tested environments rather than an exhaustive Python compatibility range.

#### Windows

Install a native Python distribution with tkinter support.

From PowerShell:

```powershell
$pythonPath = (Get-Command python -ErrorAction Stop).Source
```

#### Linux

Install Python and the relevant Tk dependencies using the distribution's package manager.

On the tested Manjaro Linux environment, the additional `tk` package was required:

```shell
pamac install tk
```

From PowerShell:

```powershell
$pythonPath = (Get-Command python3 -ErrorAction Stop).Source
```

#### macOS

Use a native Python installation for the host architecture with tkinter support.

The recorded Apple Silicon validation used Python 3.15.2 from the [official Python distribution](https://www.python.org/downloads/macos/).

Select the installed interpreter explicitly rather than relying on the system-provided Python:

```powershell
$pythonPath = '/Library/Frameworks/Python.framework/Versions/3.15/bin/python3.15'
```

Adjust this path to match the installed Python version.

#### Python virtual environment

Using a dedicated virtual environment is recommended to isolate project dependencies.

The following commands create a virtual environment outside the repository:

```powershell
$venv = Join-Path $HOME '.venvs/openjade'
& $pythonPath -m venv $venv
$pythonPath = if ($IsWindows) { Join-Path $venv 'Scripts/python.exe' } else { Join-Path $venv 'bin/python' }
```

Install the required Python packages:

```powershell
& $pythonPath -m pip install --upgrade pip
& $pythonPath -m pip install Pillow numpy
```

Verify the interpreter and dependencies:

```powershell
& $pythonPath -c "import sys, platform, PIL, numpy, tkinter; print(sys.version); print(platform.machine()); print('Pillow:', PIL.__version__); print('NumPy:', numpy.__version__); print('Tk:', tkinter.TkVersion)"
```

For GUI workflows, verify that tkinter can open a window:

```powershell
& $pythonPath -m tkinter
```

Keep `$pythonPath` available in the PowerShell session for the commands documented below.

### Managed C# components

Selected decoding helpers are implemented in C# and loaded through PowerShell.

- `src/OpenJade.Dds.cs` provides DDS decoding and managed PNG generation.
- `src/OpenJade.Lzo1x.cs` provides managed LZO decoding functionality.

The PowerShell 7 migration replaces the previous `System.Drawing` dependency with a managed PNG encoder using .NET compression and stream APIs.

No separate graphics library installation is required for these managed decoding helpers.

### Optional Ghidra static analysis

Ghidra and a compatible JDK are optional dependencies used for static executable analysis. Neither is required to launch a prepared native Vulkan viewer.

Ghidra 12.1.4 and JDK 21 were used during the recorded validation campaign.

Download Ghidra from its [official releases](https://github.com/NationalSecurityAgency/ghidra/releases) and follow its installation requirements.

Use a JDK and native Ghidra components appropriate for the host platform and architecture.

Set the paths to the installed tools from PowerShell:

```powershell
$ghidraDirectory = Read-Host 'Path to the Ghidra installation'
$javaHome = Read-Host 'Path to the JDK installation'
```

On the tested Manjaro Linux environment, JDK 21 was installed using:

```shell
pamac install jdk21-openjdk
```

The corresponding JDK directory was:

```powershell
$javaHome = '/usr/lib/jvm/java-21-openjdk'
```

On macOS, the installed JDK 21 directory can be selected using:

```powershell
$javaHome = (& /usr/libexec/java_home -v 21).Trim()
```

#### macOS ARM64 native components

The Ghidra distribution used during validation did not initially contain the required native ARM64 decompiler.

The native components were successfully built using the installed Xcode toolchain, JDK 21 and the Gradle wrapper provided with Ghidra.

```powershell
$env:JAVA_HOME = $javaHome
Push-Location (Join-Path $ghidraDirectory 'support/gradle')
./gradlew buildNatives
Pop-Location
```

For the tested distribution, the resulting native decompiler was located at:

```text
Ghidra/Features/Decompiler/build/os/mac_arm_64/decompile
```

The compiled executable was verified as a native Mach-O ARM64 binary.

These instructions describe the tested Ghidra distribution. Other releases may already provide the required native components or use different build procedures.

#### Ghidra Headless validation

From the repository root, using a local game executable:

```powershell
$exe = './game/TSoT-GOG/POP.EXE'
$outputDirectory = Join-Path $PWD "reports/native-camera-$([Guid]::NewGuid().ToString('N'))"
pwsh -NoProfile -File ./tools/Invoke-NativeCameraAnalysis.ps1 -Path $exe -GhidraDirectory $ghidraDirectory -JavaHome $javaHome -OutputDirectory $outputDirectory
```

The PowerShell wrapper selects the platform-appropriate Ghidra launcher.

Inspect the verification report:

```powershell
Get-Content -LiteralPath (Join-Path $outputDirectory 'verification.json')
```

The recorded validation successfully exported and decompiled two referenced camera functions on all three platforms:

- `0045f2a0`
- `00463e10`

The verification report must confirm matching source and snapshot SHA-256 checksums and `GameExecuted: false`.

Ghidra may report missing external libraries and internal analysis diagnostics. These must be evaluated according to their effect on the targeted analysis.

### Filesystem and resource handling

- Run PowerShell commands from the repository root unless otherwise specified.
- Use portable relative paths and `Join-Path` for dynamically constructed paths.
- Preserve the original game resources and their stored byte sequences.
- Historical asset references may differ in letter case from extracted filenames. Selected menu preparation workflows resolve these names independently of filesystem case sensitivity.
- Use new output directories under `reports/`.
- Preserve existing output-directory and symbolic-link safety checks.
- Generated reports use explicit text encodings where applicable.
- Repository source line-ending policies are defined in `.gitattributes`.

Keep original archives read-only. Never use `game/` as an output directory.


## Resource workflows

These are **selected entry points**, not a complete dependency-free export pipeline. Run PowerShell commands from the repository root, adapting input paths to your own legally obtained game installation. Use fresh output directories.

| Task | Command / starting point | Specification or evidence |
| --- | --- | --- |
| Inspect BF index | `./tools/Read-BF.ps1 -Path ./game/TSoT-GOG/POPData.BF` | [BF format](docs/formats/BF.md) |
| Extract BF entry | `./tools/Extract-BF.ps1 -Path ./game/TSoT-GOG/POPData.BF -Entry gamepads.dat -OutputDirectory ./reports/gamepads` | [BF baseline](docs/observations/2026-10-09-bf-baseline.md) |
| Inspect BIG | `./tools/Read-BIG.ps1 -Path ./game/TSoT-GOG/prince.bf -OutputDirectory ./reports/prince-index` | [BIG format](docs/formats/BIG.md) |
| Extract BIG stored bytes | `./tools/Extract-BIG.ps1 -Path ./game/TSoT-GOG/prince.bf -Id '0x03090337' -OutputDirectory ./reports/versiontag` | [Stored extraction](docs/observations/2026-10-09-big-extraction.md) |
| POP-LZO expansion | `./tools/Expand-POPLzo.ps1 -Path ./reports/lzo-input/FD3F0142.stored.bin -OutputDirectory ./reports/lzo-decoded` | [POP-LZO format](docs/formats/POP-LZO.md) |
| Inspect MGM | `./tools/Read-MGM.ps1 -Path ./reports/mgm-input/menu/pop4common.mgm -OutputDirectory ./reports/mgm-common` | [MGM format](docs/formats/MGM.md) |
| Inspect DDS | `./tools/Export-DDSPreview.ps1 -Path ./reports/POPData-extracted/menu/texture/pop.dds -OutputDirectory ./reports/logo-preview` | [DDS format](docs/formats/DDS.md) |
| Inspect MFT | `./tools/Read-MFT.ps1 -Path <extracted-font.mft> -OutputDirectory ./reports/font-atlas` | [MFT observations](docs/observations/2026-10-13-mft.md) |

For less common workflows, see [Text DAT / INI](docs/formats/Text-DAT.md), [MGM resource links](docs/formats/MGM-resource-links.md), [BIG compression investigation](docs/formats/BIG-compression.md), and the dated [research observations](docs/observations/). The original tools distinguish stored extraction from decompression: extracting bytes does not automatically decode a resource.

### Menu resource-preparation validation

The following workflow was validated on Windows, Linux and macOS during the PowerShell 7.6 migration.

It requires previously extracted menu resources, a local reference image and the configured Python interpreter.

```powershell
$menu = './reports/POPData-extracted/menu'
$reference = Read-Host 'Path to the local reference image'
$comparison = Join-Path $PWD "reports/menu-comparison-$([Guid]::NewGuid().ToString('N'))"
$prototype = Join-Path $PWD "reports/menu-prototype-$([Guid]::NewGuid().ToString('N'))"
$pages = Join-Path $PWD "reports/menu-pages-$([Guid]::NewGuid().ToString('N'))"
$effects = Join-Path $PWD "reports/menu-effects-$([Guid]::NewGuid().ToString('N'))"
```

Generate the comparison report and menu prototype:

```powershell
pwsh -NoProfile -File ./tools/Compare-MFTMenu.ps1 -AssetRoot $menu -ReferenceImage $reference -OutputDirectory $comparison -PythonPath $pythonPath
pwsh -NoProfile -File ./tools/Export-MenuPrototype.ps1 -AssetRoot $menu -ReferenceImage $reference -OutputDirectory $prototype -PythonPath $pythonPath
```

Generate the five menu scenes and Effects resources:

```powershell
pwsh -NoProfile -File ./tools/Export-MenuPages.ps1 -AssetRoot $menu -OutputDirectory $pages -PythonPath $pythonPath
& $pythonPath ./src/build_effects_assets.py $menu $effects
```

Assemble the complete simulation report:

```powershell
Copy-Item -LiteralPath $pages -Destination (Join-Path $prototype 'menus-assets') -Recurse
```

Run the GUI smoke tests:

```powershell
pwsh -NoProfile -File ./tools/Show-MenuPrototype.ps1 -ReportDirectory $prototype -PythonPath $pythonPath -SmokeTest
pwsh -NoProfile -File ./tools/Show-MenuSimulation.ps1 -ReportDirectory $prototype -PythonPath $pythonPath -SmokeTest
```

Expected smoke-test results:

```text
GUI smoke test passed: five menu pages, choices, separate bindings, return and disposal.
Complete simulation smoke test passed: ten screens, profiles, editing, scrolling, transactions and quit.
```

These checks validate resource generation, interface initialization and selected interactions. They do not establish original-game visual fidelity.

### Optional Python menu simulation

The Python/Tk simulation is a **historical research/reference interface**, separate from the native Rust menu. It uses previously exported menu resources, approximates layouts from screenshots and does not control a playable game.

The prototype and complete simulation were validated on Windows, Linux and macOS during the PowerShell 7.6 migration.

The optional legacy gamma bridge is not required for native menu settings and was not independently validated across all three platforms.

From the repository root, using the Python interpreter configured in [Research tool setup](#research-tool-setup):

```powershell
$reportDirectory = Read-Host 'Path to the generated menu prototype report'
./tools/Show-MenuPrototype.ps1 -ReportDirectory $reportDirectory -PythonPath $pythonPath
```

To launch the complete simulation:

```powershell
./tools/Show-MenuSimulation.ps1 -ReportDirectory $reportDirectory -PythonPath $pythonPath
```

The complete simulation report must contain `experiment.json`, `menus-assets/catalog.json` and available referenced resources; screenshots alone are insufficient.

See [Menu resource-preparation validation](#menu-resource-preparation-validation), [original simulation evidence](docs/observations/2026-10-16-complete-menu-simulation.md) and [gamma bridge](docs/observations/2026-10-28-gamma-bridge.md).

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
| Prince actor | [Material-pack selection](docs/observations/2026-11-22-sword-material-selection.md), [Native sword mipmaps](docs/observations/2026-11-22-sword-mips.md), [Sword reflection and Vulkan validation](docs/observations/2026-11-17-sword-vulkan.md), [Sheath and balcony integration](docs/observations/2026-11-15-prince-sheath-balcony.md), [Resource preview](docs/observations/2026-11-13-prince-resource-preview.md), [skeletal animation](docs/observations/2026-11-14-prince-skeletal-animation.md), [actor light terms](docs/observations/2026-11-12-actor-light-terms.md) |
| Design decisions and prior work | [Architecture decisions](docs/decisions/), [External research provenance](references/) |

Detailed historical test counts, hashes, byte offsets, resource IDs, fixture requirements and unresolved hypotheses remain in their **dated source observations**. This guide intentionally does not duplicate a chronological research log.

## Contributing and documenting research

- Keep original inputs read-only; never commit game binaries, extracted copyrighted resources, personal captures or generated bundles.
- Document source edition, resource ID, hash, command, expected output, comparison method and test environment where applicable.
- Distinguish **observed behavior**, **implementation**, **hypothesis**, and **unverified interpretation**.
- State the platform, hardware, driver and date for Vulkan/GPU checks. Do not generalize a passing check beyond its measured scope.
- When a later finding supersedes an earlier one, update the **current status** here and link a new dated observation; preserve the earlier record as historical evidence.
- Verify Markdown links, example commands and test-scope claims before publication.
- Use PowerShell 7.6 LTS for new research scripts and modules.
- Prefer portable filesystem paths and avoid introducing platform-specific dependencies into shared research workflows without justification.
- Follow the repository line-ending policies defined in `.gitattributes` and document the platform scope of new validation results.

For licensing and legal conditions, see [LICENSE](LICENSE) and the [main README disclaimer](README.md#license--legal-disclaimer).