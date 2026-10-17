# Menu background candidates — 2026-10-16

## Scope

This investigation reads existing extracted MGM/localization files and existing
BIG index/POP-LZO validation reports. It does not open the game archive, extract
new payloads, scan all binary contents or investigate audio/video.

## Observed evidence

`pop4mainmenu.mgm` contains three distinct FILE references: `POP.DDS`,
`SHMUEcopy.dds` and `horizontal_shmue2.dds`, all under Texture. Its P_MainMenu
page has one direct IMAGE material reference, POP (the logo). `pop4common.mgm`
contains seventeen distinct FILE references for interface textures. These
references do not explicitly identify the menu3D resources below. This does not
establish how the original runtime selects or loads its background.

Filtering the previously exported prince.bf index names for menu/intro/front/title/
jungle yields nine menu-named entries. Two form the strongest name-based lead:

| Index | ID | Stored name | Payload offset | Stored bytes | Previously decoded bytes |
| --- | --- | --- | --- | --- | --- |
| 257 | `0xFF000CB9` | `menu3D_wow_ff000cb9.bin` | 65,615,876 | 2,238,460 | 4,469,220 |
| 975 | `0xFF000CE0` | `menu3D_wol_ff000ce0.bin` | 162,230,276 | 2,044 | 132 |

The shared menu3D name is evidence of a naming relationship, not proof of a binary
reference between these entries. WOW/WOL semantics and internal formats have not
been established by this investigation. Neither geometry nor textures nor camera
data has been identified inside them.

The prior POP-LZO report records successful reference comparison for both entries.
It reports 35 decoded blocks and 1,799 trailing bytes for the WOW candidate, and
one decoded block and 1,930 trailing bytes for the WOL candidate. Trailing bytes
must remain separate and preserved. Decoded SHA-256 values:

- WOW: `96244FE330C11ACDF2A87A7C8A410225B224F5F1B9F264834425848CBF4D00EB`
- WOL: `678051B19CCA6CC1973B39A1288270EE9C80551F9FC832FEDE2A03452BD9A48E`

Other name matches: MenuBoot WOW/WOL, Menu WOW/WOL, MenuCredits WOW/WOL and
MenuInGame WOW. They are alternative contextual candidates, not proven dependencies.
Their contents were not inspected.

## Availability and limits

The existing test loop decodes real resources in memory and writes metadata to
`decoded-resources.csv`; it does not save every decoded payload. No files for the
two menu3D IDs were found in the current reports file inventory. The retained real
decoded samples are `_fd3f0142.bin` and `2101_antichambre_wow_ff024957.bin`; neither
was assumed to be the menu background or scanned as an unrelated substitute.

The matching prior index summary identifies prince.bf version 37, 3,308 entries,
410,720,256 bytes and SHA-256
`733C12C4896231B28302F9D257AA92BCA033760B0D80679D6876D0FA580628C2`.
This is historical report provenance, not a fresh archive hash verification.

## Reproducible next step

Extract only IDs `0xFF000CB9` and `0xFF000CE0` with `Extract-BIG.ps1`, then decode
each with `Expand-POPLzo.ps1` into new report directories. Compare the decoded
hashes with the recorded values above. This extraction has not been performed in
this investigation, which was limited to already extracted data.

Start with the 132-byte candidate: document its raw fields and test whether it
contains the other ID without assuming that every matching integer is a reference.
Then inspect bounded sections and readable names in the larger candidate to seek
corroborated object, texture and camera relationships. Do not begin a general
archive scan or renderer implementation before establishing that evidence.

## Local evidence sources

OpenJade-generated reports used, with paths relative to the local project root:

- `reports/POPData-extracted/menu/pop4mainmenu.mgm` and `pop4common.mgm`
- `reports/big-f0e09666f0b844f6b0f2937be4632ddc/prince/index.csv` and `summary.json` (2026-10-09)
- `reports/lzo-0f6e08b034b84fd7b6348511da2424ae/decoded-resources.csv` (2026-10-13)
- `tests/Test-POPLzo.ps1`, real-resource validation loop

These reports and game assets are local evidence and are not distributed with
the source repository. No external engine source was consulted for this step.
