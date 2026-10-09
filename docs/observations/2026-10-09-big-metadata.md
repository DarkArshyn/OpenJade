# BIG metadata verification — 2026-10-09

Dataset: Prince of Persia: The Sands of Time, **PC GOG** installation.
Procedure: `tests/Test-BIG.ps1 -GameArchive .\game\TSoT-GOG\prince.bf`,
Windows PowerShell 5.1. Result: **38 checks passed**.

| Observation | Value |
| --- | ---: |
| Active entries | 3308 |
| Capacity word | 193237 |
| Computed metadata start | 1545964 (0x1796EC) |
| End of active metadata records, exclusive | 1823836 |
| Accepted names | 3308 |
| Metadata size / block prefix matches | 3308 |
| Diagnostics | 0 |

Examples: index 0 / ID 0x0B00572C is named `ps2.ico`; index 1 / ID 0xF402E7E7
is `DefCon_Background.bin`; index 3 / ID 0x03090337 is `versiontag.bin`.
An embedded filename is not evidence of a different platform for the archive.

SHA-256 unchanged before/after:
`733C12C4896231B28302F9D257AA92BCA033760B0D80679D6876D0FA580628C2`.

Synthetic tests additionally cover capacity versus entry count, oversized or
unsupported metadata layouts, overlap, size mismatch, raw high-bit preservation,
unknown words and empty/non-ASCII/control/unterminated names. No payload was
extracted, decompressed or modified. Folder relationships remain uninterpreted.
