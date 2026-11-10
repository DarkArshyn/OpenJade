# OpenJade developer guide

[Project overview](README.md)

Current implementation status: **2026-11-10**. Original game inputs remain read-only.

Latest completed work: dynamic fog emitters and MGM-driven cursor glow in Vulkan.
Earlier work includes original logo/cursor pixel dimensions, linear UI filtering
and resolution-aware selection among twelve MFT variants. Detailed menus are composed and controlled directly in
Rust/Vulkan, with gamma, filtering, window resolution, V-Sync and local profile/
settings persistence. A prepared native menu no longer needs a running Python
controller. Unsupported audio, gameplay and graphics controls are disabled;
keyboard bindings are stored but do not drive gameplay. Original visual fidelity
remains unverified. See [native menus](#native-menu-prototype),
[implementation evidence](docs/observations/2026-10-28-native-menus.md) and
[validation](#testing-and-evidence).

## Development environment

- Windows is the tested host; Windows PowerShell 5.1 remains the research shell.
- Rust/Cargo 1.99.1, MSVC C++ build tools, ash, winit and Vulkan for the native viewer.
- Vulkan SDK `glslc` compiles shaders; Khronos validation is optional at launch.
- Python with Pillow and NumPy for export/analysis; tkinter for the separate simulation.
- C# helpers support research decoding.
- Ghidra 12.1.4 and a compatible JDK support optional native static analysis.
- Source comments and documentation are English. Dates use YYYY-MM-DD.

Other GPU/OS combinations remain unverified. See [engine prerequisites](engine/README.md).

## Project layout

| Directory | Purpose |
| --- | --- |
| `engine` | Rust workspace: asset/package loading, Vulkan renderer and native viewer |
| `src` | PowerShell/C#/Python research tools, exporters and Python simulation |
| `tools` | User-facing command scripts and Ghidra helpers |
| `tests` | Synthetic and optional local-data research checks |
| `docs/formats` | Native resource findings and OpenJade interchange specifications |
| `docs/observations` | Dated research evidence; historical limitations are not current status |
| `docs/decisions`, `references` | Decisions and external-source provenance |
| `reports` | Generated assets, screenshots and reports; excluded from Git |
| `game` | Read-only local game installation; excluded from Git |

Both README files live at the repository root. The current local game directory
is `game/TSoT-GOG`; no path is a bundled dependency or permission to redistribute assets.

## Roadmap and milestones

| Milestone | Deliverable / completion criterion | Current status |
| --- | --- | --- |
| 1. BIG extraction | Extract by numeric ID with stored bytes, ranges and hashes preserved | Implemented for tested layouts; [42 checks](docs/observations/2026-10-09-big-extraction.md), including two real resources |
| 2. Compression | Trace stored blocks and validate decompression | Recognized POP envelopes; [3,302 resources differentially validated](docs/observations/2026-10-13-lzo.md) |
| 3. Menu textures and fonts | Decode required DDS/MFT resources and verify interpretation | DDS checked; MFT atlas/metrics used for experimental text. Exact layout/style remains unverified |
| 4. Screen behavior | Document layout, colors, order and dependencies against original observations | Partial: MGM evidence and seventeen 800x600 screenshots; some behavior remains reconstructed |
| 5. First rendered screen | Render reconstructed UI and original resources with independent code | Native detailed menu UI overlays 50 decoded 3D objects. Native scene texture dimensions, filtering/mipmap and color-pipeline comparisons, plus post-composition gamma are implemented. Lighting/fog fidelity and high-resolution UI remain unfinished |
| 6. Interactive menu | Reproduce selection, input, navigation and transitions | Native detailed screens, profile creation/selection/deletion, keyboard-binding capture, settings/quit confirmations and Camera02 playback. Gamma, filtering, window resolution and V-Sync affect the viewer; committed preferences/profiles persist in an OpenJade file. Unsupported systems remain disabled; binding storage is not gameplay input |
| 7. Game systems | Implement scene/object/animation/collision/audio/gameplay with tests | Early rendering runtime: depth, textures, fog/fixture passes, scene blur, partial masked additive composition, explicit color paths and gamma; baked Camera02 playback, palm/curtain deformation and two native rain emitters. General animation, remaining particle effects, collision, audio, actors and gameplay are unimplemented. Native lighting fidelity and rain synchronization remain unresolved |
| 8. Native ports | Build and validate Linux/macOS | Not started |

No reliable overall completion percentage is available. Test counts and resource
coverage do not establish engine completeness or visual equivalence.

## Getting started

Choose a workflow:

1. For the native preview, install the [engine prerequisites](engine/README.md),
   prepare the local bundles below, then run from `engine/`.
2. For historical/reference interface experiments, use [Python menu simulation](#menu-simulation).
3. For archive/resource work, use the format-specific commands later in this guide.

A fresh checkout does not contain generated reports, textures, game binaries or
scene bundles. Export commands below require the previously generated research
reports; they are not archive extraction commands.

## Native menu prototype

The native UI includes profile creation/selection, main menu, Options, Keyboard,
Gamepad, Game, Graphics Effects/Advanced, Sound and a credits notice. Confirmations
are drawn in the same window. Load Game remains disabled. Original credits,
gamepad capture, audio and gameplay are not implemented.

The current `OJUI0003` bundle supplies 1,151 glyph/sprite entries in six images,
plus Camera02 samples. Rust builds the text/widget geometry each frame; it does
not call Python. The old `OJUI0001` baked-page bundle remains readable for regression
and the optional legacy gamma bridge.

From the repository root, with the existing local reports:

```powershell
python src/assemble_menu_scene.py reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin reports/menu-sky-moon-20261030/source-final --yaw 0 --pitch 0 --fov 59.37908
python src/export_engine_materials.py reports/menu-sky-moon-20261030/source-final reports/camera02-transition-20261026/preview/poses.json reports/palm-runtime-20261101 --palm-source reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin
python src/export_engine_ui.py reports/menu-effects-fix-8796132f9b234657a4a88218be9cb644 reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin reports/engine-ui-20261028
# Decode the twelve font variants once into separate, new directories.
foreach ($size in 10,12,14,16,18,20,22,24,26,28,36,48) {
    .\tools\Read-MFT.ps1 -Path "reports/POPData-extracted/menu/fonts/atlantis mf regular $size.mft" -OutputDirectory "reports/native-ui-fonts-20261029/$size" | Out-Null
}
python src/export_native_menu.py reports/menu-effects-fix-8796132f9b234657a4a88218be9cb644 reports/engine-ui-20261028/menu.ojui reports/engine-ui-scale-20261029 --fonts reports/native-ui-fonts-20261029
```

Outputs must be new directories. These bundles already exist on the development
host; skip export when using them. Use the widgets-capable menu report, not the
older prototype catalog without widget entries.

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/palm-runtime-20261101/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --validation
cargo run -p jade-viewer -- --scene ../reports/palm-runtime-20261101/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --validation --smoke
```

Mouse hover/click and Up/Down/Tab + Enter/Space navigate. Left/Right adjusts a
focused slider; clicking/dragging its bar also works. Wheel or DDS arrows scroll
the eighteen action rows. Select a keyboard binding and press a key or mouse button;
Escape cancels capture. Profile names accept 1-20 printable ASCII characters,
typed directly (clipboard paste is not implemented), with five profiles maximum.
Escape returns or opens quit confirmation; during/after Camera02 it resets to
the initial menu camera. The viewport stays 4:3 on resize, including hit testing.

**Native settings applied after confirmation:** gamma (0..100), ordinary-material filtering,
window client size (640x480 through 1600x1200), and V-Sync. Disabling V-Sync requests
Vulkan IMMEDIATE; if unavailable it stays enabled with an on-screen explanation.
Resolution changes the window, not the desktop mode. Fog/fixture samplers remain
linear; native mipmaps are recovered for the verified leaf and trunk textures. Other graphics, mouse/camera, game
and audio controls are visibly disabled rather than pretending to affect absent systems.

On leaving changed options with Back (or Escape), Yes applies and saves the draft,
No discards it, and Cancel returns to editing without applying it. Gamma, filtering,
window size and V-Sync remain at their committed values while editing and while
the confirmation is open. Default Settings changes only the draft to research baselines,
not independently verified original factory defaults. The committed settings,
keyboard labels and up to five menu profiles are saved beside the native bundle
as `menu.ojmenu` (`OJMNU001`). Settings are global, not per-profile. Creating,
selecting or deleting a profile also saves profile state, without committing an
unconfirmed settings draft. These profiles are independent menu identities,
not original saved games; the game's `Profiles` directory is never used.
Use one viewer per state file. Malformed state fails startup without overwriting
the file; save errors are displayed. The first run asks for a profile, later runs
use the saved active profile. Local `.ojmenu` files are ignored by Git.

Native menus own gamma directly and reject `--settings` to prevent conflicting
controllers. Their initial gamma is zero; `--gamma` can override the loaded value.
Saved filtering takes precedence over the initial `--texture-filter` setting.

Start New Game hides the UI and plays 541 precomputed poses at 60 Hz over nine
seconds, then holds the final balcony pose. This ports playback into Rust, not the
native track decoder or original game scripting. The action is wired explicitly
by OpenJade; the original binary label/action chain is not newly proven here.
No Prince, collision, BIK playback or next-level loading follows the transition.

The 48-object scene uses 15,813 geometric triangles, 16,365 submitted triangles
across 90 passes and 39 scene texture layers. The native UI adds six
images (45 textures total), preserving the 800x600 layout coordinate system. OJSCN004 advances the three fog panels and four hangfire passes from their
exported phase using elapsed runtime seconds; lampion offsets remain static.
The initial phase is chosen, not synchronized with the original game. Transparent passes are re-sorted by center depth for the active camera
each frame; intersecting surfaces remain unresolved. Scene textures preserve native base-level dimensions.
Linear filtering is the default, with optional generated mipmaps for comparison; native
lighting/color-space parity remains unresolved. Stored constant-color rules and
supported blend factors do not establish faithful whole-scene illumination.

### Runtime material animation

The [UV animation report](docs/observations/2026-10-30-material-animation.md)
documents seven moving passes. Generate the optional animated format from the
existing sky/moon source export (the output directory must not already exist):

```powershell
python src/export_engine_materials.py reports/menu-sky-moon-20261030/source-final reports/camera02-transition-20261026/preview/poses.json reports/menu-uv-motion-20261030/runtime --animate-uv
```

`--time` selects the initial sampled phase. Without `--animate-uv`, the exporter
still writes a fixed OJSCN003 package. Existing OJSCN001/002/003 packages stay
supported and static. OJSCN004 appends one pair of float32 UV rates per draw after
the native-dimension table; the reader requires exact extent, finite rates and
absolute rates <= 1024 cycles/second. This bound is a local format guard.

A Presenter-owned monotonic clock survives swapchain rebuilds and is independent
of Camera02 playback/reset. Runtime offsets use `(offset + rate * elapsed) mod 1`
in f64 before uploading f32 fragment constants; zero-rate components are left
unchanged. Scale, alpha, gain, blend, camera and geometry remain unchanged.
The clock starts with viewer initialization and continues across menu pages;
the original game's phase origin and pause semantics are not established.

Validation: 37 workspace Rust tests, four exporter tests, Clippy with warnings
denied, and an 80-frame Vulkan smoke run with zero validation errors. The new
package preserves the previous binary payload byte-for-byte apart from its
version header and the appended 720-byte rate table. Local evidence is in
`reports/menu-uv-motion-20261030/verification.json`. This verifies integration,
not original-game visual parity or light emission.

### Texture dimensions, filtering and mipmaps

The OJSCN003/004 exporter preserves all 39 source PNG base images exactly,
including rectangular textures (32x32 through 256x256 in this scene). Padded
512x512 transport slots are cropped without resampling before individual Vulkan
image uploads. Older OJSCN001/002 packages remain readable, but dimensions lost
in their earlier resampling cannot be restored: regenerate the scene package.

Add `--texture-filter nearest`, `--texture-filter linear` (default), or
`--texture-filter trilinear` to the native viewer command above. Nearest/linear
select ordinary-material base-level filtering; the previously supported fog and
fixture samplers retain bilinear filtering and their address modes. Trilinear
enables generated mipmaps for scene textures without imported native chains.
The verified plante2/tronc1 passes use their native five/six-level chains with
trilinear sampling independently of this diagnostic switch. UI images use linear/base-level filtering.
No anisotropy or LOD bias is applied. These are comparison settings, not recovered
original-game filtering settings.

The PNG bridge carries only the base image. The bounded `menu.leaf` and
`menu.trunk` sidecars now preserve native lower levels for two verified textures.
For other textures, diagnostic mipmaps are generated by linear Vulkan blits down
to 1x1 in the selected sRGB or UNORM format. Broader native mip selection, compressed-chain tails,
and one fixture's extra data remain unresolved. Generated alpha mipmaps do not
preserve cutout coverage and may thin distant foliage.

See the [focused texture validation](docs/observations/2026-10-28-native-textures.md).

### Color modulation and gamma

Use `--color-pipeline srgb` (default) or `--color-pipeline legacy-unorm` with
the same `--texture-filter linear` to compare explicit sRGB conversion against
stored-value arithmetic. Both are diagnostic; original live states remain
unverified. Without native menus, gamma is bypassed unless `--gamma` or the legacy
`--settings` bridge is selected. Native menus apply their selected gamma directly
after scene/UI composition; zero uses the recovered ramp, not a perfect identity.
See the [gamma calculation and bridge](docs/observations/2026-10-28-gamma-bridge.md)
and the preceding [color audit](docs/observations/2026-10-28-color-pipeline.md).

A [bounded balcony comparison](docs/observations/2026-10-29-balcony-modulation.md)
tests direct recorded vertex colors with texture MODULATE2X. It changes only
13 mode-0 balcony draws in the original diagnostic. The default export now applies RGB MODULATE2X to the 20 masonry triangles of material `0x30000CA0` on instance `0x30000CD9`. Two GOG Direct3D 9 captures matched the 60 native indices (FNV-1a `F90761B1`). Stage 0 combined TEXTURE and DIFFUSE with MODULATE2X for RGB and MODULATE for alpha. The second capture confirmed a null pixel shader. The broader balcony override remains opt-in. For this masonry draw the exporter defaults to `--masonry-fog normal` (GOG `InvertFogRange=0`). Use `inverted` for the measured value 1 or `off` for comparison. The vertex shader uses camera depth, the captured 8 to 35 range and strength 0.6. The legacy UNORM path blends toward RGB (52, 78, 95) after texture modulation. A subsequent fixed-menu capture matched the same shader and fog state on 16 balcony groups, both trunk groups across eight instance transforms and two groups of Menu3D_plante5. These 34 opaque draws now use the selected fog mode.

The 72-triangle non-indexed draw on plante2 (instance 30000CCF, material 30000CB0) also uses normal vertex fog and MODULATE2X. Its 216 live diffuse RGB values match the export in draw order. Shader 45B71404 passes the color through and declares an unused normal. For this draw, keep the generated `menu.leaf` file beside the scene. It carries 216 native corner alpha bytes and four lower BC3 mip levels decoded to RGBA.

The tronc1 draw (instance 30000CBF, material 30000C95) now uses the live-verified RGB MODULATE2X operation. All 384 exported corner colors matched the GOG vertex buffer; the shader passes them through. The [trunk filtering audit](docs/observations/2026-11-03-trunk-filtering.md) also verifies native base texels and six mip levels; the `menu.trunk` sidecar now supplies all six levels for the verified tronc1 pass.

The [background contribution measurement](docs/observations/2026-11-03-leaf-background.md) identifies tronc1 behind the sampled leaf pixel. For plante2, the viewer uses all five levels with trilinear filtering, tests texture alpha times vertex alpha strictly above 150/255, blends by source alpha, tests depth and does not write depth. The earlier depth-write assumption was corrected by a direct GOG capture. The [aligned framebuffer comparison](docs/observations/2026-11-03-native-mips-aligned.md) confirms tronc1, plante2 and fog3 contributions at the measured patch. Two later native contributions and phase alignment remain unresolved; no global lighting adjustment was made. The constants were captured in the menu pose; reuse during the balcony zoom is provisional.
The [cached-buffer and completeness audit](docs/observations/2026-10-29-menu-completeness.md)
now verifies identical cached/primary balcony colors and unchanged static GPU
upload. Active runtime state on the other mode-0 balcony draws remains unverified. The [sky and moon restoration](docs/observations/2026-10-30-sky-moon.md)
adds two scaled objects with bounded material states: 48 objects and 39 image
layers are now exported. Bird cards and fly-effect objects remain excluded.
The preceding 46-object audit found source slots 32/36/37 unsubmitted; slot 32
is now submitted. The [native viewer now re-sorts transparent passes each frame](docs/observations/2026-10-30-camera-transparency.md)
using the active camera; centroid-based ordering remains approximate.
Nineteen named light objects are inventoried, not implemented as dynamic lights.
Fog probes find only partial balcony coverage; neither a global light addition
nor denser fog is justified by this audit alone.

The UI now uses linear minification/magnification, independently of scene
filtering. OJUI0003 retains decoded logo pixels at 1024x256 and cursor pixels at
128x128; their layout sizes remain 480x120 and 40x40 in the 800x600 reference space.
All twelve MFT variants (10..48, with the original gaps) are exported. For each
label, the renderer chooses the smallest available size at least as large as
`label_size * 1.25 * viewport_width / 800`, or 48 when none is large enough.
For an 18-unit label, this chooses 24 at 800x600 and 48 at 1600x1200.
The 1.25 factor remains the existing layout hypothesis; this selection policy is
OpenJade's, not a recovered original-game rule. Very large text can still enlarge
the largest bitmap. Other DDS widgets have not all been restored to source size.
See [UI scaling evidence](docs/observations/2026-10-29-ui-scaling.md).

### Native fog particles and fullscreen composite

The [direct GOG postprocess audit](docs/observations/2026-11-03-menu-postprocess.md)
identifies two additional contributions to the measured menu patch: dynamic fog
quads using texture `2E004FE4`, linked to `Menu3D_Fog3D` / `Menu3D_Fog3D2`, and a
fullscreen blend with a blurred scene render target. The latter is independently
reproduced from captured inputs to within one byte level per channel across the
800x600 image, using the captured alpha 104/255. The subsequent [blur construction audit](docs/observations/2026-11-03-menu-blur-construction.md)
recovers four current-frame passes: two native-gain copies/reductions followed
by two three-tap filters. An independent reference reconstructs three consecutive
outputs within 2/255; no previous-frame scene contribution is observed in this
menu state. The [measured blur is now integrated in Vulkan](docs/observations/2026-11-03-vulkan-menu-blur.md),
before UI and gamma. Dynamic fog-particle simulation is now implemented in the integration below. Matching the measured fog3 UV phase reduces
part of the remaining difference; global illumination has not been adjusted.
The separate additive chain is now partially implemented below; dynamic fog particles are now implemented below.

### Menu effects: inventory and native rain

The [luminous point capture](docs/observations/2026-11-04-menu-luminous-points.md) separates the two fly meshes from the additive pollen emitter and identifies four vegetation modifier candidates. [GOG vegetation captures](docs/observations/2026-11-04-menu-vegetation.md) verify all four in the native viewer, including the upper-right vine silhouette. The [native pollen integration](docs/observations/2026-11-04-vulkan-pollen.md) reproduces birth, translation, rotation and packed colors in the viewer.

The [splash emitter investigation](docs/observations/2026-11-04-splash-emitter-link.md) resolves a reference to Cam_Manager.gao and separates isolated spawn behavior from live activation.

The [rain, birds and flies inventory](docs/observations/2026-11-03-menu-effects-inventory.md)
resolves 24 selected objects and five effect descriptors in the frozen menu.
Two rain instances share byte-identical descriptors; eight splash instances share
one descriptor. Mesh birds, named bird particles and flies use distinct resources.
Texture keys have multiple records, individually checked with the texture decoder. The [native rain reader and update](docs/observations/2026-11-03-rain-native-parameters.md)
now establish emission, three timer phases and fixed-step acceleration. The bounded
decoder matches the original x86 reader, and four isolated movement cases match
native output. The [creation and lifetime checks](docs/observations/2026-11-03-rain-spawn-life-transform.md)
now cover three random seeds, six phase boundaries, both stored emitter matrices
and the matrix override branch. [Live menu observations](docs/observations/2026-11-03-rain-live-state.md) confirm both
effective emitter matrices, capacity 150, accumulator updates and additive
SRC_ALPHA/ONE drawing with depth writes disabled. [Rain appearance validation](docs/observations/2026-11-03-rain-appearance.md) now
reproduces all 4,602 captured corners, UVs and packed colors across 767 particle
observations in three phases. Texture modulation and additive alpha blending are
identified. [Rain now runs in Vulkan](docs/observations/2026-11-03-vulkan-menu-rain.md):
the optional `menu.rain` sidecar carries both effective stored matrices, native
parameters, four phase colors and the original 32x32 texture. Rust emits and updates
bounded populations, uploads six corners and byte alpha per particle, and draws
with MODULATE2X, SRC_ALPHA/ONE, depth testing and no depth writes or applied fog.
The Rust port matches the same 4,602 captured corners exactly. Fixed-time Vulkan
checks at 0, 1 and 2 seconds are stable and error-free; rain changes the image at
1 and 2 seconds. An 80-frame native-menu resize smoke test also passes.
This validates integration, not full visual equivalence: a private seed and 60 Hz
research clock are used, original shared RNG/time synchronization is unresolved,
and exact dynamic fog composition remains open. [Menu birds and flies](docs/observations/2026-11-04-menu-birds-and-flies.md) now render two native bird particle emitters and two fly swarms. The [three mesh birds](docs/observations/2026-11-04-menu-mesh-flight.md) also run in Vulkan. Their native waypoint boxes and weighted local wing deformation have been checked against GOG draws over multiple laps. Eight native splash emitters now run alongside rain using the optional menu.splash file. The [capture and runtime checks](docs/observations/2026-11-04-splash-emitter-link.md) cover their birth vectors, phase colors, oriented quads and draw state. The fixed-menu splash fog matches the measured GOG InvertFogRange=0 color and vertex-depth curve. Isolated native draw replays changed RGB by at most 2/255 with this setting and 51/255 with the inverted setting.

Regenerate a local package with `export_engine_materials.py --palm-source` to add
the rain sidecar. Existing packages without it retain their previous behavior.
Keep all sidecars next to the scene. From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-rain-20261103/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

Add `--no-rain` for an otherwise identical comparison. See the linked report for
the export command, native-capture checks and GPU regression commands.

### Cursor glow and dynamic fog

[Native draw isolation](docs/observations/2026-11-05-cursor-dynamic-fog.md) and
[lifecycle replay](docs/observations/2026-11-05-fog-cursor-lifecycle.md) identify
the two cursor textures and both dynamic fog emitters. The
[Vulkan integration](docs/observations/2026-11-08-vulkan-fog-cursor.md) now loads
both emitters from `menu.fog`, alongside the existing panels. OJUI0004 carries
the cursor's MGM alpha tracks and second texture. Earlier UI bundles remain supported.

Native Rust replay matches 21,348 fog corners with exact colors and UVs.
The workspace has 57 passing ordinary tests. The complete menu passes the
80-frame resize/transition smoke with zero Vulkan validation errors.
Private random streams, exact cursor activation/quantization, native transparent
ordering and final fog composition remain limitations. Global lighting is unchanged.

```powershell
# From engine/
cargo run -p jade-viewer -- --scene ../reports/menu-fog-cursor-20261108/menu.ojscene --menu ../reports/menu-fog-cursor-20261108/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

Use `--no-fog` to isolate the two dynamic emitters without removing the panels
or vertex fog. Keep all sidecars beside the scene. Fresh material and UI exports
produce the new sidecar and cursor tracks from local original resources.

### Fixture animation and lighting receivers

The [hangfire and lighting audit](docs/observations/2026-11-10-hangfire-lighting.md)
identifies two sequential, group-limited vertex modifiers on each suspended fixture.
A native replay checks 124 modifier outputs with maximum local error below `6e-8`.
Weight loading is verified: primary mesh alpha bytes are copied unchanged and
scaled by 1/256; GAO instance colors are a different buffer. All 124 captured
49-color buffers match the mesh exactly. The [Vulkan integration](docs/observations/2026-11-10-vulkan-fixtures.md)
now animates 672 expanded corners across both flame passes of the two fixtures.
Its native Rust replay checks 41,664 corners; fixed-time captures and the 80-frame
resize/transition smoke pass with zero Vulkan validation errors. Keep `menu.fixtures`
with the prepared scene. Native startup from zero and 4,804 phase updates are now verified bit-for-bit using captured engine deltas. Independent wall-clock/video alignment remains unverified. A bounded
lighting capture records 341 accumulation calls on 11 unresolved objects, while
identified balcony, trunk and fixture draws retain cached colors. This does not
validate global lighting parity or justify adding illumination to every object.

From `engine/`, launch the prepared fixture package:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-fixtures-20261110/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

### Native menu blur in Vulkan

The prepared native menu enables the measured blur with `--color-pipeline legacy-unorm`.
Keep `menu.trunk` and the other sidecars with the scene. Add `--no-menu-blur` for
an unblurred comparison. The sRGB diagnostic path retains its previous behavior;
the blur is not bound to the simulated Special Effects setting.

```powershell
# From engine/
cargo run -p jade-viewer -- --scene ../reports/palm-runtime-20261101/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

The 3D scene passes through the native-size intermediate targets and is composed
before sharp UI and gamma. The independent fixed-image GPU check differs by at
most 1/255 per RGB channel. Resize/gamma smoke validation reports zero errors.
See [runtime design, limits and GPU regression](docs/observations/2026-11-03-vulkan-menu-blur.md).

The [masked additive chain](docs/observations/2026-11-03-vulkan-menu-additive.md)
is also implemented before the blur composite. A new `menu.glow` sidecar binds the
verified 24-triangle balcony draw and its native alpha 184/255. Other native mask
writers remain unimplemented; this is partial emitter coverage, not complete bloom
fidelity. Ordinary texture opacity is excluded from the mask. Use
`--no-menu-additive` to isolate the blur; `--no-menu-blur` bypasses both chains.
The additive chain uses the current scene, with no previous-frame history.

```powershell
python tests/integration_menu_additive.py reports/menu-additive-20261103/menu.ojscene reports/menu-additive-gpu-check
python -m unittest discover -s tests -p 'test_menu_additive.py'
```

### Live Gamma control from the Python menus

This optional **legacy OJUI0001** workflow is retained for comparison. It is not
needed by the native detailed menus above. From the repository root, start the
Python controls first (create/select a local
simulation profile, then Options -> Graphics -> Advanced -> Gamma):

```powershell
python -B src/menu_simulation.py reports/menu-effects-fix-8796132f9b234657a4a88218be9cb644 --settings reports/engine-gamma-20261028/menu.ojsettings
```

In a second terminal, from `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-uv-motion-20261030/runtime/menu.ojscene --menu ../reports/engine-ui-20261028/menu.ojui --settings ../reports/engine-gamma-20261028/menu.ojsettings --validation
```

Gamma previews live in Vulkan. Yes saves it, No restores the saved value, Cancel
keeps the pending preview, and Default Settings previews zero. The committed gamma
survives Python restarts in this OpenJade file; other settings remain session-only
and simulated. One Python writer per file. This legacy path uses two windows;
the OJUI0003 native interface has its own direct controls and `.ojmenu` persistence.

For an independent fixed-value test, replace `--settings ...` with `--gamma 50`
(integer 0..100). Omit both to bypass gamma. No OS display ramp is modified.
See [calculation, transactions and limits](docs/observations/2026-10-28-gamma-bridge.md).

## Testing and evidence

Current focused checks:

```powershell
# From engine/
cargo fmt --all --check
cargo clippy --workspace -- -D warnings
cargo test --workspace
# From the repository root
python -m unittest discover -s tests -p 'test_export_engine*.py'
python -m unittest discover -s tests -p 'test_native_mips.py'
python -m unittest discover -s tests -p 'test_menu_postprocess.py'
python -m unittest discover -s tests -p 'test_menu_blur.py'
python -B -m unittest discover -s tests -p 'test_graphics_settings.py'
python -B tests/check_native_ui_resources.py reports/engine-ui-scale-20261029 reports/POPData-extracted/menu/texture
# Optional GPU blur check: prepared native scene and Vulkan SDK screenshot layer.
python tests/integration_menu_blur.py reports/palm-runtime-20261101/menu.ojscene reports/menu-blur-gpu-check
# Optional integration check: requires prepared local bundles, Tk and Vulkan.
python -B tests/integration_gamma_bridge.py
```

The integrated native-menu Vulkan smoke test presents 80 frames, resizes 800x600
-> 1600x1200 -> 800x600, starts an accelerated test transition and returns to the menu. On the
AMD Radeon RX 9070 XT it completed with zero validation errors. This does not
measure original-game parity. Runtime interaction was separately inspected.
Latest validation on 2026-10-29: 30 Rust tests passed. Confirmation coverage
verifies that all four effective display controls remain unchanged during editing,
Back, Cancel and No, and apply together on Yes; defaults and reload are covered.
The earlier UI scaling checks also passed, including font selection and
rectangular UI texture bounds/row preservation. Logo and cursor decoded pixels
match their DDS sources byte-for-byte. The OJUI0003 legacy-unorm smoke and an
interactive 1600x1200 inspection passed without Vulkan validation errors.

Previous native-menu validation on 2026-10-28: 27 Rust tests passed, including
transactions, profile/binding persistence, bounded input, dragging and native UI
geometry. Formatting and Clippy with all targets/warnings denied passed. The
new native-menu smoke traverses pages, changes gamma/filter/V-Sync, checks
Cancel/No and plays Camera02 with resize; zero Vulkan validation errors.
Interactive inspection also checked profile creation, Graphics Gamma, discard
confirmation, Keyboard and quit in the actual Vulkan window.

Earlier that day, three Python graphics-settings tests passed. The earlier three focused material-export tests also passed.
Rust coverage includes package bounds, native texture rows, navigation, Camera02,
letterboxing, presentation-format selection, settings parsing and all 101 gamma
ramps. The complete Python simulation smoke passed with the bridge enabled.
The live integration test observed previews 100 -> 0 -> 42 -> 0 through the real
Python handlers and Vulkan consumer, including Cancel, No, Yes and Defaults;
80 frames and two resizes completed with zero validation errors. Explicit gamma
tests passed in both color pipelines, as did the bypass/checker regression.
Historical research tests below are not rerun implicitly.

Local evidence includes `reports/engine-ui-scale-20261029/` and
`reports/native-ui-fonts-20261029/`. Earlier evidence is grouped by milestone: `reports/engine-native-menu-20261028/`,
`reports/engine-ui-20261028/`,
`reports/engine-textures-20261028/`, `reports/native-colors-20261028*`,
`reports/native-gamma-20261028*` and `reports/engine-gamma-20261028/`.
Screenshots, game-derived bundles, decompilation and `.ojsettings`/`.ojmenu` preferences
are excluded from Git. The actual game installation is not changed.

## Architecture decisions and future runtime

Rust + ash + Vulkan is the selected runtime direction. Windows is the current
implementation/test host; platform abstraction and Linux/macOS validation remain
future work. `jade-assets` reads bounded research bundles; `jade-render-vulkan`
owns graphics resources; `jade-viewer` handles input and the prototype state machine.
The current native UI uses MFT/DDS sprite atlases, dynamic Rust text/quads, hit
testing and a transaction model. It remains a focused menu implementation, not
a general game UI framework. The legacy baked-page reader remains compatible. Static resources are rebuilt on swapchain recreation;
resource caching and a dedicated UI/animation architecture remain future work.

PowerShell, C# and Python remain research/export tools. Python is not required
while running a prepared native menu. The optional Python gamma bridge remains
a legacy diagnostic controller. A broader input/game-settings system, per-profile
game state and device bindings remain future work.
See [foundation decisions](docs/decisions/0001-foundation.md), [external sources](references)
and [license/legal notice](README.md#license--legal-disclaimer).

## Research status and validation

The following table records historical research-tool results, not current feature limits. Native runtime checks are listed
under [Testing and evidence](#testing-and-evidence); these are separate scopes.

| Area | Implemented capability | Recorded validation |
| --- | --- | --- |
| Project foundation | Separate modules, commands, tests, documentation and local reports; English comments; Git exclusions | [Project decisions](docs/decisions/0001-foundation.md) |
| POPData.BF | Index reading and single/all-entry extraction | 80 files checked against source ranges; [119 checks](docs/observations/2026-10-09-bf-baseline.md) |
| Text DAT / INI | Byte-preserving Windows-1252 conversion | [26 checks](docs/observations/2026-10-09-text-dat.md), including the real pop4pclocal.dat round trip |
| MGM structure and materials | Hierarchy, values, byte ranges, raw text, self-closing tags and diagnostics; distinct definitions/references | [73 checks](docs/observations/2026-10-09-mgm.md); 21 definitions and 41 references in three files |
| Menu resource links | Local material/font name resolution and resource path matching | [44 checks](docs/observations/2026-10-09-mgm-links.md); 199 local name references resolved; MFT files remain filename candidates |
| BIG v37 / prince.bf | Numeric index, names, offsets, stored lengths and raw metadata | [38 checks](docs/observations/2026-10-09-big-metadata.md); 3,308 names and matching metadata lengths |
| BIG compression assessment | Bounded block-chain candidates, declared sizes and remaining-byte evidence | [34 checks](docs/observations/2026-10-09-big-compression.md); 3,302 candidates; no codec validation |
| POP-LZO decoding | Classic LZO1X and verbatim blocks; stored bytes and tails preserved | [120 checks](docs/observations/2026-10-13-lzo.md); 7,442 compressed blocks agree with official miniLZO |
| Menu DDS textures | Single-level DXT1/DXT5 decoding, transparent PNGs and inspection previews | [96 checks](docs/observations/2026-10-13-dds-logo.md); 63 real textures match Pillow pixel for pixel |
| MFT font data | Fixed-record reader, raw metrics and grayscale atlas export | [59 checks](docs/observations/2026-10-13-mft.md); 12 fonts, 2,688 records; text layout unverified |
| Experimental MFT text | ASCII specimens with traceable glyph placements and explicit layout hypotheses | [39 checks](docs/observations/2026-10-13-mft-text.md); layout remains experimental |
| Main-menu text comparison | Six labels reconstructed at 800x600 and compared with a supplied capture | [Placement and contour experiment](docs/observations/2026-10-13-menu-comparison.md); approximate agreement, pixel fidelity unverified |
| Static menu prototype | Logo plus six MFT labels at 800x600; twelve style variants compared | [Prototype experiment](docs/observations/2026-10-13-menu-prototype.md); offline PNG only, exact styling unverified |
| Interactive research viewer | Fixed-size window, keyboard/mouse selection and simulated actions | [Viewer validation](docs/observations/2026-10-13-menu-viewer.md); navigation tests and Windows GUI smoke test passed |
| Viewer state colors | MGM-driven enabled, selected, hover, pressed and disabled palettes | [State checks](docs/observations/2026-10-13-viewer-states.md); six palettes verified, event behavior remains experimental |
| Options / Effects research panel | Four MGM-backed choice groups, in-memory settings and return navigation | [Effects experiment](docs/observations/2026-10-13-options-effects.md); native research widgets, no graphics settings applied |
| Effects visual prototype | MFT labels and choices, DDS panels, MGM placement and interactive return | [Styled Effects](docs/observations/2026-10-13-effects-style.md); partial canvas, resolution/gamma absent |
| Additional menu scenes | Resource-based Options, Advanced, Keyboard and Gamepad pages with simulated choices and binding labels | [Five-page viewer](docs/observations/2026-10-13-menu-pages.md); screenshot text substitutions recorded, no device configuration |
| DDS navigation widgets | Linked arrows, slider bars, minus/plus buttons and selectors with bounded interactions | [Widget experiment](docs/observations/2026-10-13-menu-widgets.md); raw MGM ranges, no real settings applied |
| Menu simulation | Ten screenshot-based screens, session profiles, complete 18-action list, settings and confirmations | [Simulation scope and launch command](docs/observations/2026-10-16-complete-menu-simulation.md); model/render checks and GUI smoke test |
| External research | Pinned sources checked against local data | [Swyter/poptools](references/poptools.md), [FulGerNet/pop-bf-lab](references/pop-bf-lab.md), [hogsy/jaded](references/jaded.md), [morluto/rea](references/rea.md), and [kugelrund/io_scene_pop](references/io-scene-pop.md) |

The table includes earlier experiments as well as the current simulation; limitations
in older observation records describe those earlier stages.

Counts refer to the recorded test runs, not to a new test execution whenever
this README is edited. Tested source game files remained unchanged.

Recent 3D investigations and their recorded checks are indexed under [3D scene investigations](#3d-scene-investigations).


## Research tools: local setup

Run commands from the repository root. Choose a Python installation with tkinter:

```powershell
$pythonPath = (Get-Command python -ErrorAction Stop).Source
& $pythonPath -m pip install Pillow numpy
& $pythonPath -c "import tkinter, PIL, numpy; print('Research dependencies available')"
```

Place your local game files under `game/TSoT-GOG`, or pass another input path.
Keep generated output under `reports`, which is excluded from Git. Do not place
output in `game`. Extraction and export commands require new destinations.

### Prepare the menu simulation

The current prototype pipeline also requires a local **800x600 main-menu reference
capture**. This is an analysis input, not the rendered background; screenshots and
game assets are not supplied by the repository. Keep the extracted resources and
report at their generated locations because the report references local paths.

```powershell
.\tools\Extract-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF -All -OutputDirectory .\reports\menu-data
$referenceImage = Read-Host 'Path to your 800x600 main-menu reference capture'
.\tools\Export-MenuPrototype.ps1 -AssetRoot .\reports\menu-data\menu -ReferenceImage $referenceImage -OutputDirectory .\reports\menu-prototype -PythonPath $pythonPath
.\tools\Export-MenuPages.ps1 -AssetRoot .\reports\menu-data\menu -OutputDirectory .\reports\menu-prototype\menus-assets -PythonPath $pythonPath
.\tools\Show-MenuSimulation.ps1 -ReportDirectory .\reports\menu-prototype -PythonPath $pythonPath
```

If these directories already exist, use new paths consistently or launch an
existing complete report. A folder of screenshots alone is not a prototype report.

## BF inspection and extraction

Open Windows PowerShell in the project root (currently `C:\OpenJade`). Paths to
modules are resolved relative to scripts, not hard-coded to that location.

```powershell
# Read the archive index; this does not extract anything.
.\tools\Read-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF | Format-Table Index, FileName, DataLength

# Extract one entry into a NEW directory.
.\tools\Extract-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF -Entry gamepads.dat -OutputDirectory .\reports\gamepads

# Run synthetic regression tests; no game installation is needed.
.\tests\Test-BF.ps1

# Optional: verify extraction against the archive's source byte ranges.
.\tests\Test-BF.ps1 -GameArchive .\game\TSoT-GOG\POPData.BF
```

Extraction never overwrites an existing output directory. Use a new destination
for another run. Test runs use unique directories inside `reports`. The tools
open BF inputs for reading only. Do not use `game` for output.

## Menu simulation

The separate Python simulation follows the supplied PC GOG menu captures at **800x600**,
using English labels, extracted MFT text and DDS interface assets. All pages and
confirmations use one window.

- Main menu and Options navigation.
- Graphics Effects and Advanced, Game and Sound settings.
- Keyboard and Gamepad pages with eighteen actions, scrolling and editable binding labels.
- Creation, selection and confirmed deletion of up to five session profiles.
- Save/discard/cancel for changed settings, reset to simulation baselines and quit confirmation.

The simulation starts at profile creation. Type a name and press Enter or select
Create. Profiles and settings exist only in memory and are lost on exit; settings
are shared across simulation profiles. The original game's profiles and configuration
are neither read nor modified.

### Launch and checks

Use Python with **Pillow and tkinter** and an existing generated prototype report
containing `experiment.json` and `menus-assets/catalog.json`. The extracted menu
resources referenced by that report must still be accessible. An arbitrary folder
of screenshots is not a valid report.

```powershell
# Select your Python executable and an existing generated prototype report.
$pythonPath = (Get-Command python -ErrorAction Stop).Source
$reportDirectory = Read-Host 'Path to the generated menu prototype report'

.\tools\Show-MenuSimulation.ps1 -ReportDirectory $reportDirectory -PythonPath $pythonPath

# Optional model/render checks and hidden-window interaction check.
& $pythonPath .\tests\test_simulation_screens.py $reportDirectory
.\tools\Show-MenuSimulation.ps1 -ReportDirectory $reportDirectory -PythonPath $pythonPath -SmokeTest
```

Use the mouse or Tab/arrow keys and Enter to navigate. Escape goes back or dismisses
a confirmation. Control-list arrows advance five rows; the mouse wheel advances
one row. Click a binding to edit its ASCII label, then press Enter to accept or
Escape to cancel. This does not capture or bind a keyboard/gamepad device.

### Current limits and next work

In the separate Python window the background remains neutral. The decoded 3D
scene and Camera02 transition are rendered in the native Vulkan window.
Python layouts are screenshot-based approximations, not
pixel-identical reproductions. The DDS cursor is a candidate whose identity and
hotspot still need verification.

Default Settings restores **simulation baselines**, not verified factory defaults.
With `--settings`, Gamma previews the emulated output ramp in the connected
Vulkan viewer and its committed value persists. Without the bridge it remains a
simulation control. Resolution and other graphics/audio choices remain simulated;
no desktop display configuration is changed. Load is disabled, and Python
New Game/Credits lead to explicit placeholders. See [live Gamma setup](#live-gamma-control-from-the-python-menus).

See [simulation evidence](docs/observations/2026-10-16-complete-menu-simulation.md).

## Text DAT / INI

These commands apply to Windows-1252 text such as `pop4pclocal.dat`, not arbitrary
binary DAT files. No byte-order mark is added and line endings are preserved.
Use a new output filename for each conversion. If editing the INI, save it as
Windows-1252 without a BOM. UTF-8 without a BOM cannot reliably be detected.

```powershell
.\tools\Extract-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF -Entry pop4pclocal.dat -OutputDirectory .\reports\localization
.\tools\Convert-DatToIni.ps1 -Path .\reports\localization\pop4pclocal.dat -Output .\reports\localization\pop4pclocal.ini
.\tools\Convert-IniToDat.ps1 -Path .\reports\localization\pop4pclocal.ini -Output .\reports\localization\pop4pclocal-roundtrip.dat
.\tests\Test-TextDat.ps1
```

See `docs/formats/Text-DAT.md` for the supported scope and validation rules.

## MGM structure

```powershell
# Extract one MGM file into a new directory.
.\tools\Extract-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF -Entry menu/pop4common.mgm -OutputDirectory .\reports\mgm-input

# Read and write a human-readable report with CSV tables.
$mgm = .\tools\Read-MGM.ps1 -Path .\reports\mgm-input\menu\pop4common.mgm -OutputDirectory .\reports\mgm-common
$mgm.Summary
$mgm.Materials | Format-Table Type, Name, Offset, EndOffset
$mgm.Diagnostics | Format-Table Code, Offset, Message

# No game data required for synthetic tests.
.\tests\Test-MGM.ps1
# Optional: use a directory of extracted MGM files.
.\tests\Test-MGM.ps1 -MgmDirectory .\reports\mgm-input\menu
```

Omit OutputDirectory to read without generating files. Full source bytes are
available in `$mgm.Bytes`; raw text uses a reversible byte mapping. Unclosed
and mismatched tags are reported without invented repairs. See
`docs/formats/MGM.md` for range conventions, supported syntax and limitations.

## Menu resource links

Extract the full archive to a new directory so texture and font files are
available beside the MGM files. AssetRoot must be the extracted **menu** folder.

```powershell
.\tools\Extract-BF.ps1 -Path .\game\TSoT-GOG\POPData.BF -All -OutputDirectory .\reports\menu-data
$links = .\tools\Resolve-MGMResources.ps1 -Path .\reports\menu-data\menu\pop4mainmenu.mgm -AssetRoot .\reports\menu-data\menu -OutputDirectory .\reports\mainmenu-links
$links.Summary
$links.Elements | Format-Table ElementType, ElementName, ReferenceName, ReferenceStatus, ResourceStatus
.\tests\Test-MGMLinks.ps1
# Optional real-data checks:
.\tests\Test-MGMLinks.ps1 -MenuDirectory .\reports\menu-data\menu
```

Open `references.txt` for readable chains, or `elements.csv` and `links.csv`
for node IDs, byte offsets and evidence. Exact local names, case differences,
missing or ambiguous references and font filename candidates are distinguished.
The link resolver does not decode textures or fonts. Texture previews are
available separately below. See `docs/formats/MGM-resource-links.md`.

## Main BIG archive inspection

`prince.bf` and `POPData.BF` use different layouts. For the local BIG v37 file:

```powershell
$big = .\tools\Read-BIG.ps1 -Path .\game\TSoT-GOG\prince.bf -OutputDirectory .\reports\prince-index
$big.Summary
$big.Entries | Select-Object -First 10 | Format-Table Index, IdHex, Name, StoredLength, NameStatus, LengthMatches
.\tests\Test-BIG.ps1
# Optional real archive verification:
.\tests\Test-BIG.ps1 -GameArchive .\game\TSoT-GOG\prince.bf
```

This inspects numeric IDs, names, metadata and byte ranges for the tested PC
GOG v37 layout. Payload formats and folder relationships are not decoded.
Invalid metadata remains visible through diagnostics and raw name bytes.
See `docs/formats/BIG.md`. The initial external research reference is
documented with its pinned revision in `references/poptools.md`; the additional
metadata reference is in `references/pop-bf-lab.md`.

## Main BIG stored extraction

Select one resource by its unsigned ID. Quote hexadecimal IDs so PowerShell
preserves values above its signed integer range. The destination must be new.

```powershell
.\tools\Extract-BIG.ps1 -Path .\game\TSoT-GOG\prince.bf -Id '0x03090337' -OutputDirectory .\reports\versiontag
.\tests\Test-BIGExtraction.ps1
# Optional: verify two selected resources against local source byte ranges.
.\tests\Test-BIGExtraction.ps1 -GameArchive .\game\TSoT-GOG\prince.bf
```

The example writes `03090337.stored.bin` and `extraction.json`. The manifest
records the original name, archive hash, source range and verified payload hash.
Embedded names are metadata only; output filenames use IDs. The four-byte size
prefix is excluded. No decompression or resource decoding is performed.
Extraction refuses archives with diagnostics. See [the extraction contract](docs/formats/BIG.md#stored-extraction-contract)
and [recorded validation](docs/observations/2026-10-09-big-extraction.md).

## BIG compression assessment

```powershell
$compression = .\tools\Read-BIGCompression.ps1 -Path .\game\TSoT-GOG\prince.bf -OutputDirectory .\reports\compression
$compression.Summary
.\tests\Test-BIGCompression.ps1
# Optional full-index inspection and report verification:
.\tests\Test-BIGCompression.ps1 -GameArchive .\game\TSoT-GOG\prince.bf
```

The read-only probe reports 3,302 bounded envelope candidates, containing
7,461 blocks, and six unrecognized resources on the reference dataset.
These are structural observations, not validated decompression. Unknown
resources are not assumed uncompressed, and trailing bytes are not discarded.
See [the probe contract](docs/formats/BIG-compression.md) and
[recorded evidence](docs/observations/2026-10-09-big-compression.md).

## POP-LZO decoding

```powershell
.\tools\Extract-BIG.ps1 -Path .\game\TSoT-GOG\prince.bf -Id '0xFD3F0142' -OutputDirectory .\reports\lzo-input
.\tools\Expand-POPLzo.ps1 -Path .\reports\lzo-input\FD3F0142.stored.bin -OutputDirectory .\reports\lzo-decoded
.\tests\Test-POPLzo.ps1
```

The decoder writes `source.stored.bin`, `decoded.bin`, `trailing.bin` and
`decoding.json` into a new directory. Stored and trailing bytes remain intact.
PowerShell 5.1 compiles the small C# decoder locally; no external codec is
needed for normal use. Input and decoded output are each capped at 64 MiB.
This handles recognized POP envelopes, not every binary resource. See
[the format contract](docs/formats/POP-LZO.md), [verification results](docs/observations/2026-10-13-lzo.md)
and [optional reference tests](references/lzo.md).

## Menu texture previews

The extracted textures are under `menu/texture` and MFT fonts under `menu/fonts`.
The main menu's Logo element references the POP material and `texture/pop.dds`.

```powershell
.\tools\Export-DDSPreview.ps1 -Path .\reports\POPData-extracted\menu\texture\pop.dds -OutputDirectory .\reports\logo-preview
.\tests\Test-DDSPreview.ps1
# Optional: inspect every extracted texture without changing it.
.\tests\Test-DDSPreview.ps1 -TextureDirectory .\reports\POPData-extracted\menu\texture
```

`texture.png` preserves transparency; `preview.png` uses a checkerboard to make
it visible. The original DDS and a hash manifest are retained. Only single-level
2D DXT1/DXT5 is supported. This is a texture preview, not a reconstructed menu.
See [the DDS contract](docs/formats/DDS.md) and [logo provenance and validation](docs/observations/2026-10-13-dds-logo.md).

See `docs/decisions/0001-foundation.md` and `docs/formats/BF.md`.

## MFT font inspection and text experiments

The observed MFT reader exports raw metrics and grayscale atlases. Glyph mapping,
coverage and text layout remain experimental; this is not a general font converter.

```powershell
$fontPath = Read-Host 'Path to an extracted MFT font'
.\tools\Read-MFT.ps1 -Path $fontPath -OutputDirectory .\reports\font-atlas
.\tools\Export-MFTTextPreview.ps1 -Path $fontPath -OutputDirectory .\reports\font-text -Text 'OpenJade'
.\tests\Test-MFT.ps1
.\tests\Test-MFTTextPreview.ps1
```

See [MFT observations](docs/observations/2026-10-13-mft.md) and
[text layout hypotheses](docs/observations/2026-10-13-mft-text.md).

## 3D scene investigations

Targeted resources from the existing Menu3D extraction support selected mesh,
UV and material experiments, a textured fog panel and four courtyard landmarks.
The investigations below began as offline diagnostics. Their decoded resources now also feed the native viewer; the older reports retain their original scope and limitations. Camera-linked
blocks now expose common field identifiers and camera/target references; runtime
activation, controller behavior and transform hierarchy remain unknown.
Lighting, complete scene assembly and original render-state behavior are not verified.

The evidence below is chronological. In particular, the landmark investigation
corrects the earlier BC1 candidate offset: the previous transparent-ground result
must not be treated as a verified interpretation of the actual ground texture.
The controller investigation also separates identifier words from float values.

- [Background candidates](docs/observations/2026-10-16-menu-background-candidates.md)
- [focused camera/ground inspection](docs/observations/2026-10-16-menu3d-camera-ground.md)
- [ground topology candidate](docs/observations/2026-10-16-ground-topology.md)
- [second-mesh comparison](docs/observations/2026-10-16-second-mesh-material.md)
- [texture candidates](docs/observations/2026-10-16-menu3d-textures.md)
- [textured fog-panel experiment](docs/observations/2026-10-17-fog-panel.md)
- [three-object diagnostic assembly](docs/observations/2026-10-17-menu3d-assembly.md)
- [textured landmark diagnostic](docs/observations/2026-10-17-menu3d-landmarks.md)
- [camera projection experiment](docs/observations/2026-10-17-camera-projection.md)
- [Camera-linked field tables](docs/observations/2026-10-17-camera-controllers.md)

- [Camera02 CF1 sequence](docs/observations/2026-10-17-camera-cf1.md): 32 byte/float-triplet records; leading bytes sum to the stored value 512. Track semantics and timing remain unverified.

- [CF1 packed-rotation candidates](docs/observations/2026-10-17-camera-cf1-prefix.md): four near-unit quaternion candidates; size-like words make the earlier timing hypothesis ambiguous. Camera composition remains unknown.

- [Camera comparison and global-resource lead](docs/observations/2026-10-17-camera-comparison.md): targeted comparison found CameraAndGlobal referenced by the Menu3D WOL; no second complete CF1 encoding confirmed. Duplicate keys are retained by the new inventory tool.

- [Global camera instance and definition links](docs/observations/2026-10-17-global-camera-links.md): three matching field identifiers have different instance/definition values; runtime effects and the secondary encoding remain unknown.

- [Global camera field-use candidates](docs/observations/2026-10-17-global-camera-field-uses.md): six offset/type matches in three linked behavior blocks; instruction semantics and camera effects remain unverified.

- [Camera behavior token boundaries](docs/observations/2026-10-17-camera-behavior-tokens.md): three bounded eight-byte token areas align the six field candidates; two blocks share a 96-byte sequence. Opcode semantics remain unknown.

- [Vector motif and native follow-up](docs/observations/2026-10-17-camera-native-followup.md): repeated triplet-field motif and three native diagnostic-string leads; REA reviewed as tooling, not an opcode reference. Interpreter semantics remain unverified.

The linked observations contain sample hashes, offsets, commands and local report
names. Reports are excluded from Git; their absence in a fresh checkout is expected.

### Palm deformation research

Seven palms use the type-1 vertex deformation in the native viewer. The
[component layout](docs/observations/2026-10-30-palm-component-layout.md)
identifies the instance parameters. The [runtime verification](docs/observations/2026-11-01-palm-runtime.md)
covers effective frame time, the 1,024-entry sine table and both local-axis
modes. The OJSCN005 export adds 4,536 animated corners and includes the OJSCN004
material motion. Palm6, palm7 and palm9 require further layout research.
Two left-side foliage patches in the original recording show a cycle of about
4.17 seconds, consistent with the predicted 4.19 seconds. See the
[video period measurement](docs/observations/2026-11-01-palm-video-period.md).

### Balcony curtain deformation

The frozen menu export with `--palm-source` also writes four curtain sidecars (`menu.rido1` through `menu.rido4`) beside
`menu.ojscene`. The viewer matches the 96 render corners to the 25 control
points before enabling the cloth. It applies the local curtain field, 40 ordered
distance links and, for rido1 and rido2, the instance collision plane at a fixed 60 Hz simulation step.
Set `OPENJADE_CAPTURE_SECONDS` to a nonnegative time in seconds for repeatable poses.
Four close-up Vulkan captures at 0, 0.5, 1 and 2 seconds kept all 13 marked
points stationary while the free points moved up to 0.9613 scene units.
At two seconds the maximum corner displacement was 0.9613 units for rido2 and 0.6372 for rido4. Enabling rido4 changed 1,647 pixels against the single-curtain capture at that time and zero pixels at rest. Agreement with the original balcony
sequence, native frame timing and collisions with other scene objects remain open.

## Native camera analysis

Portable Ghidra and JDK installations support static analysis of a verified
executable copy. See [installation and launch instructions](docs/decisions/native-analysis-setup.md)
and [confirmed entry-point evidence](docs/observations/2026-10-17-native-camera-entry-points.md).
The initial three diagnostic references resolve to two functions; variable loading and
reference fixups are the current leads. The camera interpreter and token
semantics remain unverified. No original game code is executed by this workflow.

`tools/Invoke-NativeCameraAnalysis.ps1` invokes the independent Java export script
in `tools/ghidra/`. Executable copies, databases and recovered code remain local
under ignored `reports/`; these optional dependencies are not needed for the menu
simulation. Original game files remain read-only.

Historical step: [dynamic function table and callers](docs/observations/2026-10-18-native-function-table.md). Three direct resolver callers, descriptor construction/lookup/cleanup, and an execution consumer have been inspected. The descriptor registry is distinct from the category-dispatch table; camera token meanings remain unverified.

Historical category evidence: [dispatch mapping and vector-copy motif](docs/observations/2026-10-18-category-dispatch.md). Serialized IDs are remapped before execution. A selected three-word copy handler supports field-to-local copying in two camera-resource motifs; execution and camera-transform effects remain unverified.

Historical flow evidence: [local vector and callers](docs/observations/2026-10-18-local-vector-flow.md). The two field-copy motifs are alternative paths in dynamic function 5755; its selected vector is returned, then copied or added by two callers. The upstream 5b82 calculation and actual camera effects remain unresolved.

Historical continuation: [vector descriptors and consumers](docs/observations/2026-10-18-vector-consumers.md). Signatures for 5b82/5b83 are located; the sum passes through 5b83 and feeds a vector subtraction. Two linked tables are ambiguous, and the function bodies and coordinate space remain unresolved.

Historical resolution: [5b82/5b83 bodies and balcony-object links](docs/observations/2026-10-19-camera-function-bodies.md). Both bodies are located in Menu3D record B60024E5 and linked to the populated 263c/005d descriptor table. Shared balcony-camera behavior is established; active camera, field meaning and full 5b83 arithmetic remain unverified.

Historical arithmetic: [balcony vector bounds](docs/observations/2026-10-19-balcony-vector-bounds.md). Function 5b83 conditionally bounds each component; both balcony instances select mode 2. Runtime initialization of the gate and limits, active camera and coordinate space remain unknown.

Historical writes: [bounds-writing callback](docs/observations/2026-10-19-bounds-writers.md). Callback index 5 links to four confirmed writes of fields 464/512. No direct writer for 172/276 was found in the eight linked blocks; live initialization and activation remain unresolved.

Gate follow-up: [field 276 and operation 1007](docs/observations/2026-10-20-bounds-gate.md). A scoped identifier search finds only the model definition in Menu3D and no occurrence in CameraAndGlobal. The inspected 1007 wrapper/helper shows no direct gate assignment; indirect effects and runtime initialization remain unresolved.

Current visual milestone: assemble the menu scenery under a fixed camera, shared across menu pages. The user's observation of the original PC game places the balcony camera transition and playable Prince sequence after New Game; these are separate later milestones. Gate 276 research is deferred. The [io_scene_pop comparison](references/io-scene-pop.md) identifies 55 candidate objects with recognized geometry headers and uniquely resolved geometry/material-pack links; this does not yet mean complete or correctly rendered meshes.

External comparison: [Jaded bounding volumes](references/jaded.md), pinned to revision `8d55704c80adfcec4f3bcaeb2445dc9f68ef960e`. Its initial-limit fields and OBBox flag corroborate the observed TSoT layout. Editor-dependent fields and a different sphere predicate prevent assuming binary compatibility. Jaded is a later Ubisoft-derived reference; no source code is imported, and reuse permission has not been established. Activation and coordinate space still require TSoT evidence.

Historical serialized source: [balcony geometry](docs/observations/2026-10-20-balcony-geometry.md). Both balcony GAOs contain the paired triplets loaded into the structure read by operations 2bc3/2bc5. A targeted inspector preserves their offsets and raw bytes; activation, subsequent mutation and runtime coordinate space remain unresolved.

## Research test commands

The validation table records historical runs, not tests rerun for each documentation
change. Synthetic tests use constructed fixtures; optional real-data checks require
the user's local files. Preserve input hashes and unknown bytes in research outputs.

Useful focused checks, run from the root:

```powershell
.\tests\Test-BF.ps1
.\tests\Test-MGM.ps1
& $pythonPath .\tests\test_landmark_preview.py
& $pythonPath .\tests\test_camera_projection.py
& $pythonPath .\tests\test_camera_controllers.py
```

For the simulation's report-dependent model/render checks and GUI smoke test, see
[Menu simulation](#menu-simulation). Do not interpret one script's success as a
full-suite result. Format-specific commands above document optional real-data checks.


## Historical 3D research index

These dated reports preserve the findings and open questions **at their original date**.
Use the current milestones above for implementation status.

- [textured menu scene diagnostic](docs/observations/2026-10-20-fixed-menu-scene.md)
- [colored menu assembly](docs/observations/2026-10-20-colored-menu-scene.md)
- [October 21 experiment](docs/observations/2026-10-21-menu-objects-fog.md)
- [transform, blend and constant-color evidence](docs/observations/2026-10-21-native-fog-state.md)
- [native-derived time samples](docs/observations/2026-10-21-fog-uv-motion.md)
- [per-group color investigation](docs/observations/2026-10-21-material-color-dispatch.md)
- [selected trunk and 42 stored transforms](docs/observations/2026-10-21-tree-lighting-scene-audit.md)
- [landmark fitting and dynamic vertex transfer](docs/observations/2026-10-21-camera-fit-gpu-upload.md)
- [PoP BF Lab comparison, October 22](docs/observations/2026-10-22-pop-bf-lab-geometry-comparison.md)
- [October 22 static trace](docs/observations/2026-10-22-native-camera-matrices.md)
- [October 23 static trace](docs/observations/2026-10-23-active-camera-writers.md)
- [pointer setter and callers](docs/observations/2026-10-23-camera-object-selection.md)
- [native bindings and resource chains](docs/observations/2026-10-23-camera-behavior-object-links.md)
- [request fields and behavior selection](docs/observations/2026-10-23-camera-state-transition.md)
- [field +0x410 writers](docs/observations/2026-10-23-camera-source-pointer-writers.md)
- [camera list population and named balcony zones](docs/observations/2026-10-24-camera-list-population.md)
- [pose references and remaining eligibility question](docs/observations/2026-10-24-balcony-zone-pose.md)
- [vector semantics and global position writes](docs/observations/2026-10-24-camera-vector-transfer.md)
- [named targets, candidate poses and render readiness](docs/observations/2026-10-24-menu-camera-orientation.md)
- [four diagnostic renders](docs/observations/2026-10-24-balcony-camera-renders.md)
- [Camera02 to global camera](docs/observations/2026-10-24-camera02-menu-startup.md)
- [horizontal view-axis sign](docs/observations/2026-10-25-camera-projection-sign.md)
- [missing courtyard objects investigation](docs/observations/2026-10-25-menu-missing-objects.md)
- [two-pass fixture materials](docs/observations/2026-10-25-fixture-materials.md)
- [projection initialization trace](docs/observations/2026-10-25-projection-initialization.md)
- [Native Camera02 track decoding](docs/observations/2026-10-25-camera02-tracks.md)
- [Camera02 activation and relative composition](docs/observations/2026-10-25-camera02-activation-composition.md)
- [Camera02 event-track follow-up](docs/observations/2026-10-26-camera02-events.md)
- [Camera02 transition preview](docs/observations/2026-10-26-camera02-transition-preview.md)
