# OpenJade developer guide

[Project overview](README.md) · Research snapshot: **2026-10-20**

This guide describes the Windows research tools and experimental menu simulation.
Dated observation records preserve earlier experiments; their limitations are not
necessarily the status of the latest implementation. Game resources remain read-only.

## Development environment

- Windows and Windows PowerShell **5.1** for command scripts and orchestration.
- C# helpers compiled locally by PowerShell for binary decoding and image export.
- Python with **Pillow**, **NumPy** and **tkinter** for analysis and the desktop viewer.
- Optional native analysis: Ghidra 12.1.4, full JDK 21 and a Java evidence-export script; see [setup](#native-camera-analysis).
- English source comments and documentation.
- Dates use `YYYY-MM-DD` (ISO 8601).

These research dependencies do not establish Linux/macOS runtime support.

## Project layout

| Directory | Purpose |
| --- | --- |
| `src` | PowerShell modules, C# decoding helpers and Python analysis/viewer code |
| `tools` | User-facing command scripts |
| `tests` | Synthetic tests and optional local-data checks |
| `docs/formats` | Observed format layouts and unresolved questions |
| `docs/observations` | Reproducible observations and verification records |
| `docs/decisions` | Project decisions and reasons |
| `references` | Reference provenance, without game assets |
| `reports` | Local generated outputs; excluded from Git |
| `game` | Local read-only game data; excluded from Git |

> [!NOTE]
> The extracted game is located in the directory: `game\TSoT-GOG`

Both `README.md` and `README-dev.md` live at the repository root. The future
`engine/` directory will separate runtime development from research when it begins.

## Research status and validation

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

## Roadmap and milestones

The current focus is a visible menu milestone and selected background resources,
not a general scan of every game format. Audio/video work remains deferred.

| Milestone |Deliverable / completion criterion | Current status |
| --- | --- | --- |
| 1. BIG extraction | Extract a resource by numeric ID into a new directory; preserve stored bytes and record name, range, size and SHA-256 | Implemented; [42 checks](docs/observations/2026-10-09-big-extraction.md), including two real resources |
| 2. Compression | Identify candidate compressed blocks and validate decompression separately, retaining traceability to stored bytes | Implemented for recognized POP envelopes; [differential validation](docs/observations/2026-10-13-lzo.md) on all 3,302 candidates |
| 3. Menu textures and fonts | Decode the DDS/MFT data required by a selected screen and verify its interpretation | DDS preview verified; MFT atlas and raw metrics exported; font layout remains unverified |
| 4. One screen's behavior | Document layout, dimensions, colors, draw order and dependencies against observations of the original game | Partial: MGM evidence and seventeen 800x600 screenshots document layouts and visible states; some behavior remains assumed |
| 5. First rendered screen | Display one reconstructed menu screen using the project's own rendering code and extracted game resources | Partial: ten simulated screens use MFT text and DDS assets; 3D background and pixel-exact fidelity remain absent |
| 6. Interactive menu | Reproduce selection, input, navigation and transitions for that screen | Partial: single-window navigation, session profiles, eighteen action rows, sliders and confirmations; persistence, actual input bindings and transition timing remain unimplemented |
| 7. Game systems | Investigate and implement required scene, object, animation, collision, audio and gameplay systems with tests | Runtime implementation not started; focused scene research is underway |
| 8. Native ports | Build and validate the independent implementation on Linux/macOS | Not started |

No reliable overall completion percentage is available. Passing tool tests and
resource counts are not a measure of engine completion. The detailed geometry,
texture and camera investigations below are research, not a playable runtime.

## Getting started

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

The current simulation follows the supplied PC GOG menu captures at **800x600**,
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

The background remains neutral: the original 3D scene, animations and transition
timing are not implemented. Layouts are screenshot-based approximations, not
pixel-identical reproductions. The DDS cursor is a candidate whose identity and
hotspot still need verification.

Default Settings restores **simulation baselines**, not verified factory defaults.
Resolution/gamma choices are simulated; no graphics or audio setting affects the
system. Load is disabled, and New Game/Credits lead to explicit placeholders.

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
These are offline diagnostics, separate from the menu simulation. Camera-linked
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

Latest: [dynamic function table and callers](docs/observations/2026-10-18-native-function-table.md). Three direct resolver callers, descriptor construction/lookup/cleanup, and an execution consumer have been inspected. The descriptor registry is distinct from the category-dispatch table; camera token meanings remain unverified.

Latest category evidence: [dispatch mapping and vector-copy motif](docs/observations/2026-10-18-category-dispatch.md). Serialized IDs are remapped before execution. A selected three-word copy handler supports field-to-local copying in two camera-resource motifs; execution and camera-transform effects remain unverified.

Latest flow evidence: [local vector and callers](docs/observations/2026-10-18-local-vector-flow.md). The two field-copy motifs are alternative paths in dynamic function 5755; its selected vector is returned, then copied or added by two callers. The upstream 5b82 calculation and actual camera effects remain unresolved.

Latest continuation: [vector descriptors and consumers](docs/observations/2026-10-18-vector-consumers.md). Signatures for 5b82/5b83 are located; the sum passes through 5b83 and feeds a vector subtraction. Two linked tables are ambiguous, and the function bodies and coordinate space remain unresolved.

Latest resolution: [5b82/5b83 bodies and balcony-object links](docs/observations/2026-10-19-camera-function-bodies.md). Both bodies are located in Menu3D record B60024E5 and linked to the populated 263c/005d descriptor table. Shared balcony-camera behavior is established; active camera, field meaning and full 5b83 arithmetic remain unverified.

Latest arithmetic: [balcony vector bounds](docs/observations/2026-10-19-balcony-vector-bounds.md). Function 5b83 conditionally bounds each component; both balcony instances select mode 2. Runtime initialization of the gate and limits, active camera and coordinate space remain unknown.

Latest writes: [bounds-writing callback](docs/observations/2026-10-19-bounds-writers.md). Callback index 5 links to four confirmed writes of fields 464/512. No direct writer for 172/276 was found in the eight linked blocks; live initialization and activation remain unresolved.

Gate follow-up: [field 276 and operation 1007](docs/observations/2026-10-20-bounds-gate.md). A scoped identifier search finds only the model definition in Menu3D and no occurrence in CameraAndGlobal. The inspected 1007 wrapper/helper shows no direct gate assignment; indirect effects and runtime initialization remain unresolved.

Current visual milestone: assemble the menu scenery under a fixed camera, shared across menu pages. The user's observation of the original PC game places the balcony camera transition and playable Prince sequence after New Game; these are separate later milestones. Gate 276 research is deferred. The [io_scene_pop comparison](references/io-scene-pop.md) identifies 55 candidate objects with recognized geometry headers and uniquely resolved geometry/material-pack links; this does not yet mean complete or correctly rendered meshes.

External comparison: [Jaded bounding volumes](references/jaded.md), pinned to revision `8d55704c80adfcec4f3bcaeb2445dc9f68ef960e`. Its initial-limit fields and OBBox flag corroborate the observed TSoT layout. Editor-dependent fields and a different sphere predicate prevent assuming binary compatibility. Jaded is a later Ubisoft-derived reference; no source code is imported, and reuse permission has not been established. Activation and coordinate space still require TSoT evidence.

Latest serialized source: [balcony geometry](docs/observations/2026-10-20-balcony-geometry.md). Both balcony GAOs contain the paired triplets loaded into the structure read by operations 2bc3/2bc5. A targeted inspector preserves their offsets and raw bytes; activation, subsequent mutation and runtime coordinate space remain unresolved.

## Testing and evidence

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

## Architecture decisions and future runtime

Windows PowerShell 5.1 remains the research entry point, complemented by C# and
Python where decoding and display require them. The future runtime language and
architecture have not been selected. Its intended targets are Windows, Linux and
macOS with a shared codebase and isolated platform-specific integration.
Graphics, input, audio, build tooling and dependencies must be evaluated together;
actual builds and behavior must be tested before platform support is claimed.

See [foundation decisions](docs/decisions/0001-foundation.md),
[external research provenance](references), and the
[license and legal disclaimer](README.md#license--legal-disclaimer).
















Fixed-camera assembly: [textured menu scene diagnostic](docs/observations/2026-10-20-fixed-menu-scene.md). The new assembler exports 26 objects / 4,026 triangles as OBJ/MTL and an 800x600 preview. Unsupported resources are reported; original lighting, blending and exact camera framing remain unverified.


Primary geometry and colors: [colored menu assembly](docs/observations/2026-10-20-colored-menu-scene.md) now renders 39 objects / 6,056 triangles, with stored RGB on 38 objects. A manual one-anchor camera adjustment approaches the supplied screenshot; full framing and native fog/lighting remain unresolved. Sixteen geometry candidates remain excluded.


Missing objects and fog: [October 21 experiment](docs/observations/2026-10-21-menu-objects-fog.md) adds the detailed balcony and zero-UV ground, reaching 41 objects / 14,956 triangles. Two existing fog panels have an explicit experimental alpha-blending pass and a baseline comparison. Native fog blending and the third panel's transform remain unresolved.


Native fog verification: [transform, blend and constant-color evidence](docs/observations/2026-10-21-native-fog-state.md) enables the third panel (42 objects / 14,960 triangles). The three panels now use verified source-over/no-depth-write flags and material constant color instead of black vertex RGB. Dynamic UV animation and full scene lighting remain unresolved.


Fog UV motion: [native-derived time samples](docs/observations/2026-10-21-fog-uv-motion.md) add --fog-time in effective engine seconds. The shared material rate is decoded from its packed UV words; phase zero and forward time are explicit diagnostic choices. This remains an offline renderer, not a live animated menu.


Material color dispatch: [per-group color investigation](docs/observations/2026-10-21-material-color-dispatch.md) corrects nine non-fog groups (200 triangles) using native constant-color mode 2. Modes 0 and 3 remain explicitly unresolved lighting approximations. The renderer exports a previous-colors.png comparison and per-group evidence in scene.json.


Tree lighting and scene audit: [selected trunk and 42 stored transforms](docs/observations/2026-10-21-tree-lighting-scene-audit.md) identifies the direct instance-color branch for Menu3D_tronc4, which clears the subsequent dynamic-light enable bit for the examined state. A numbered object image and transform report make placement checks reproducible. Native color upload, runtime transforms and exact screenshot framing remain unverified; no global brightness or object-position correction is applied.


Camera constraints and GPU upload: [landmark fitting and dynamic vertex transfer](docs/observations/2026-10-21-camera-fit-gpu-upload.md) adds a reproducible three-landmark balcony fit, with two ambiguous foreground candidates explicitly excluded. The dynamic color packing/copy path is traced to Direct3D submission. An opt-in --tree-upload-check preview applies the bounded tronc4 case; default camera and general lighting remain unchanged. Cached-buffer execution and whole-scene alignment remain unverified.


External geometry cross-check: [PoP BF Lab comparison, October 22](docs/observations/2026-10-22-pop-bf-lab-geometry-comparison.md) matches all 42 assembled objects against the supplied Jade Z-up OBJ. Triangle counts and ordered corner coordinates agree within 0.000001 scene unit, including the third fog panel. This supports stored geometry; native camera, runtime transforms, UV/material parity and lighting remain separate questions.


Native camera matrices: [October 22 static trace](docs/observations/2026-10-22-native-camera-matrices.md) identifies the camera-block rigid inverse, axis-conversion routine and PC projection coefficients, including radian half-angle tangent, aspect branch, vertical sign and fixed depth term. Four synthetic tests cover the independent math module. Active-menu field writers and complete matrix composition remain unresolved; default rendering is unchanged.


Active camera writers: [October 23 static trace](docs/observations/2026-10-23-active-camera-writers.md) identifies the attached-object transform callback, the explicit FOV setter and the per-render copy into the camera block. Instruction checks confirm the full matrix copy and angle writes. The menu's selected object and final runtime values remain unverified; renderer defaults are unchanged.

Camera object selection: [pointer setter and callers](docs/observations/2026-10-23-camera-object-selection.md) identifies the write to camera-entry +0x88, two native callers supplying the current logic object, and interpreter handler 30D4. Both native callers set FOV before changing the attachment. The main-menu object identity and live final values remain unverified.

Camera behavior/object links: [native bindings and resource chains](docs/observations/2026-10-23-camera-behavior-object-links.md) connects selection caller 0051DFA0 to behavior 3200043D on the global Camera.gao. Cam_Manager.gao references that global camera through its native logic. The second caller's behavior is absent from the two inspected containers. Three synthetic tests and a hash-checked resource audit validate these static links; menu activation and Camera02 pose sourcing remain unresolved.

Global camera transitions: [request fields and behavior selection](docs/observations/2026-10-23-camera-state-transition.md) traces 005C02E0 through the request/applied fields and behavior-slot writes. The menu-manager request can select either B6002512 or 55000018 depending on the object referenced at camera field +0x410. Five native bindings and typed resource links were verified; that object's identity and the live branch remain unresolved.

Camera source pointer: [field +0x410 writers](docs/observations/2026-10-23-camera-source-pointer-writers.md) identifies setter 005A9770, conditional/reset clears, the manager's indexed input list and the camera's eight-candidate selection path. Store bytes, object-field metadata and reset behavior links were verified. List population is now traced in [camera list population and named balcony zones](docs/observations/2026-10-24-camera-list-population.md): two registration behaviors link to CAM_Balcony and CAMALT_Balcony. Actual runtime selection and initialization of zone field +0x88 remain unresolved.

Balcony zone initialization: [pose references and remaining eligibility question](docs/observations/2026-10-24-balcony-zone-pose.md) verifies that both balcony zone instances reference themselves at field +0x18C. Native behavior 005ADE10 initializes derived vectors from that object in mode 2. The vector convention, writer of zone +0x88 and live camera selection remain unresolved.

Camera vector transfer: [vector semantics and global position writes](docs/observations/2026-10-24-camera-vector-transfer.md) identifies the negative second basis axis, the translation-free transpose product, and a conditional position path through 005602E0 to the global camera matrix. The direct path recomputes the reference position; transfer of cached zone vectors and final orientation are not established.

Menu camera orientation: [named targets, candidate poses and render readiness](docs/observations/2026-10-24-menu-camera-orientation.md) traces target-based direction and matrix construction. Two numerical balcony poses support an offline comparison; live selection, settled pose and FOV still need validation before claiming a faithful menu background.

Balcony camera render comparison: [four diagnostic renders](docs/observations/2026-10-24-balcony-camera-renders.md) reuse 42 objects and 35 materials at vertical FOV 50/75 degrees. Neither candidate matches the stationary menu framing in these tests. Startup camera selection remains the priority; audio is deferred.

Menu startup source: [Camera02 to global camera](docs/observations/2026-10-24-camera02-menu-startup.md) verifies that Menu_Start_Demo behavior 0059F140 copies Camera02 position, direction and up, then sets angle 1.3 radians. Two unadjusted renders remain diagnostic; view-axis/projection conventions and motion state need reconciliation.

Projection correction: [horizontal view-axis sign](docs/observations/2026-10-25-camera-projection-sign.md) fixes mirrored output in both diagnostic rasterizers. Two projection regression tests and four native math tests pass. Earlier renders and manually fitted camera adjustments predate this correction and require reassessment.

## Courtyard object completion (2026-10-25)

The [missing courtyard objects investigation](docs/observations/2026-10-25-menu-missing-objects.md) adds the scaled liana and supported groups of three light fixtures to offline renders. Multi-stage fixture materials remain omitted; the 59.38-degree vertical FOV is provisional.
