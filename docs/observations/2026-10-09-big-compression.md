# BIG compression candidates — 2026-10-09

Source: OpenJade local inspection under Windows PowerShell 5.1 of the PC GOG
`prince.bf`. Archive SHA-256 before and after inspection:
`733C12C4896231B28302F9D257AA92BCA033760B0D80679D6876D0FA580628C2`.

## Measured results

| Measurement | Result |
| --- | --- |
| Indexed resources inspected | 3,308 |
| Bounded envelope candidates | 3,302 |
| Recognized markers with invalid candidate chains | 0 |
| Resources without a recognized envelope | 6 |
| Candidate blocks | 7,461 |
| Blocks with unequal declared decoded/stored sizes | 7,442 |
| Blocks with equal sizes | 19 |
| Maximum blocks in one candidate | 65 |
| Sum of declared decoded sizes (not decoded output) | 604,645,164 bytes |
| Entries with metadata size high bit set | 0 |
| Codec-validated resources | 0 |

All candidates contain `99 C0 FF EE`: one starts at payload offset 12, 3,034 at
offset 13, and 267 at offset 14. All chains end with a short block under the
tested hypothesis. These observations do not prove LZO decoding correctness.
The metadata high bit cannot identify the candidates in this dataset.

| Example ID | Name | Blocks | Declared decoded bytes | Parsed bytes | Remaining bytes |
| --- | --- | --- | --- | --- | --- |
| 0xFD3F0142 | _fd3f0142.bin | 1 | 14,126 | 7,283 | 905 |
| 0xFF024957 | 2101_antichambre_wow_ff024957.bin | 10 | 1,296,307 | 1,019,153 | 747 |
| 0xFF0B5CEA | MenuBoot_wol_ff0b5cea.bin | 1 | 20 | 28 | 2,016 |

The last example has equal block sizes. Its name alone establishes no menu
behavior. Remaining bytes are retained, not discarded as assumed padding.

The six unrecognized resources are `ps2.ico`, `DefCon_Background.bin`,
`DefCon_Wheel.bin`, `versiontag.bin`, `WOLInfo.bin` and `size.grs`.
This status does not prove they are uncompressed. In particular, the two
resources selected for the previous extraction tests do not exercise this
candidate envelope.

## Verification and reproduction

```powershell
.\tests\Test-BIGCompression.ps1 -GameArchive .\game\TSoT-GOG\prince.bf
$probe = .\tools\Read-BIGCompression.ps1 -Path .\game\TSoT-GOG\prince.bf -OutputDirectory .\reports\compression
$probe.Summary
```

34 checks passed: 25 synthetic checks and nine local archive/report checks.
Synthetic fixtures deliberately contain no real LZO stream: this verifies
that structural candidates are never mislabeled as codec-validated. Cases
include both marker variants, equal and unequal sizes, multiple blocks,
short/full endings, zero terminator, trailing data, marker outside the block,
malformed sizes, truncated headers, unknown data and bounded stream ranges.
Real checks cover report completeness, source integrity and output restrictions.
Reparse-point rejection is implemented but not exercised by this suite.

Test runs store `verification.json` and the complete CSV evidence under unique
`reports/big-compression-*` directories, excluded from Git. No assets are
included here. See [the probe contract and next validation gate](../formats/BIG-compression.md).
