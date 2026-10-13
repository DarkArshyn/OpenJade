# OpenJade

An independent research project aimed at reimplementing *Prince of Persia: The Sands of Time* and the necessary Jade Engine functionality from scratch, without Ubisoft's source code.

Native Windows, Linux, and macOS support is a long-term objective and is not currently available.

- **Development environment:** Windows.
- **PowerShell baseline:** Windows PowerShell 5.1.
- **Reference game:** *Prince of Persia: The Sands of Time* (PC GOG edition).
- **Game data:** Provided by a local installation; not included in this repository.
- **Implementation status:** Research tools are being developed incrementally. Some archive inspection, extraction, and resource analysis capabilities have been implemented and tested. The independent game runtime and renderer have not yet entered development.
- **Date format:** `YYYY-MM-DD` (ISO 8601).

## Roadmap — 2026-10-13

- **Reference dataset:** *Prince of Persia: The Sands of Time* (PC GOG edition).
- **Current status:** Research tools are under development. Work on an independent game runtime and renderer has not yet begun.

The information presented here reflects the current state of research. It does not imply complete format coverage or constitute an exhaustive specification of the future engine.

### Completed research capabilities

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
| External research | Pinned sources checked against local data | [Swyter/poptools](references/poptools.md) and [FulGerNet/pop-bf-lab](references/pop-bf-lab.md) |

Counts refer to the recorded test runs, not to a new test execution whenever
this README is edited. Tested source game files remained unchanged.

### Next milestones, in order

> [!IMPORTANT]
> **Current focus: the main menu's MFT font**
>
> The main-menu logo texture is decoded and its MGM reference verified.
> The viewer supports experimental input and reads state colors from the MGM.
> Next: compare state behavior with the original game and investigate transitions.

| Milestone | Deliverable / completion criterion | Current status |
| --- | --- | --- |
| 1. BIG extraction | Extract a resource by numeric ID into a new directory; preserve stored bytes and record name, range, size and SHA-256 | Implemented; [42 checks](docs/observations/2026-10-09-big-extraction.md), including two real resources |
| 2. Compression | Identify candidate compressed blocks and validate decompression separately, retaining traceability to stored bytes | Implemented for recognized POP envelopes; [differential validation](docs/observations/2026-10-13-lzo.md) on all 3,302 candidates |
| 3. Menu textures and fonts | Decode the DDS/MFT data required by a selected screen and verify its interpretation | DDS preview verified; MFT atlas and raw metrics exported; font layout remains unverified |
| 4. One screen's behavior | Document layout, dimensions, colors, draw order and dependencies against observations of the original game | Structural data available; behavior not established |
| 5. First rendered screen | Display one reconstructed menu screen using the project's own rendering code and extracted game resources | Partial: static logo/text prototype displayed in a desktop viewer; 3D background absent |
| 6. Interactive menu | Reproduce selection, input, navigation and transitions for that screen | Experimental viewer navigation and simulated actions; original behavior and transitions not reproduced |
| 7. Game systems | Investigate and implement required scene, object, animation, collision, audio and gameplay systems with tests | Not started; full scope remains to be established |
| 8. Native ports | Build and validate the independent implementation on Linux/macOS | Not started |

Windows PowerShell 5.1 remains the primary interface for research tools and
orchestration. Complementary languages are already used where processing and
display requirements call for them:
- C# helpers handle binary decoding and image export.
- Python with Pillow and NumPy supports image analysis, comparison and prototype assembly.
- Python with tkinter provides the experimental desktop viewer.

These choices meet current research needs; the language and architecture
of the future independent game runtime have not been decided. Continue to focus
on selected resources and visible menu milestones.

The future runtime must target Windows, Linux and macOS with a shared codebase
and minimal platform-specific changes. Language selection must account for
portable graphics, window/input handling, audio, build tooling and dependencies,
not just language availability. Platform-specific integration should remain
isolated.

The current Windows research environment and Python viewer do not
establish runtime portability; builds and behavior will need validation on all
three operating systems before support can be claimed.

### Progress indicators and limits

No reliable overall completion percentage is available: the work required to
reproduce the whole game has not yet been scoped. Tool counts and passing tests
are not a percentage of engine implementation.

| Measured check | Result on the reference dataset |
| --- | --- |
| BIG entries with accepted names | 3,308 / 3,308 — 100% of this check |
| BIG metadata lengths matching block prefixes | 3,308 / 3,308 — 100% of this check |
| Material/font references with unique local declarations in the three tested MGM files | 199 / 199 — 100% of this check |
| Independent display and game execution | Experimental logo/text viewer available; game execution not implemented |

These ratios do not establish full understanding of a format, verified font
contents, rendering fidelity or support for another game/platform/build.
Update this snapshot and its evidence links as milestones are completed.

## Start here

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

## Layout

| Directory | Purpose |
| --- | --- |
| `src` | Reusable PowerShell modules |
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

## Current scope

The BF component reads the supported index layout and extracts individual
entries or all entries. It is not a universal BF decoder. Text DAT/INI tools
preserve Windows-1252 content without parsing or rewriting its properties.
The MGM reader exposes observed structure and materials, without rendering menus.

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

## License & Legal Disclaimer

OpenJade is an independent research and reverse-engineering project.
It is not affiliated with, endorsed by, or associated with Ubisoft.
All trademarks and product names belong to their respective owners.
Prince of Persia and the Jade Engine are associated with Ubisoft.

Game data and assets are not included in this repository.
Users must obtain their own game files.

OpenJade is licensed under the GNU General Public License v3.0 or later
(GPL-3.0-or-later). See [LICENSE](LICENSE) for details.

> [!NOTE]
> This is a hobby project, and no completion date is planned at this time. Any project contributions are welcome 😊
