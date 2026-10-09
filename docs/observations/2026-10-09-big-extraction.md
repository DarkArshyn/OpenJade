# BIG stored extraction — 2026-10-09

OpenJade local verification, Windows PowerShell 5.1, PC GOG reference dataset.

`tests/Test-BIGExtraction.ps1 -GameArchive .\game\TSoT-GOG\prince.bf`
passed 42 checks: 37 synthetic/contract checks and five real-data checks.
`tests/Test-BIG.ps1` with the same archive passed its existing 38 checks.
The source archive SHA-256 before and after extraction was:
`733C12C4896231B28302F9D257AA92BCA033760B0D80679D6876D0FA580628C2`.

| ID | Metadata name | Payload offset | Stored bytes | SHA-256 |
| --- | --- | --- | --- | --- |
| 0x03090337 | versiontag.bin | 34582532 | 2044 | 8F0463FD9746B28361603EEEAB003EC6895BB6DDEDA4E963C53C93495D5DBB96 |
| 0xF402E7E7 | DefCon_Background.bin | 34054148 | 264188 | 8C5393859A291CDDD2EC0145886D72E55D354F23D46E0F7DF0F3B22388B13BDB |

Each output was compared against a separate read of its source range. These
two samples do not establish coverage for every resource or build.

Synthetic checks cover a 150,003-byte payload crossing multiple copy buffers,
an empty payload at EOF, unsigned maximum ID in hex and decimal, raw size flag
preservation, offsets and hashes, embedded traversal names kept as metadata,
invalid/missing IDs, duplicate IDs, malformed ranges, metadata size mismatch,
unsupported version, existing outputs and game output refusal. Source hashes
remain unchanged. Reparse-point rejection is implemented but not tested here.

Run these scripts from the project root. Each run creates a unique directory
under `reports` containing `verification.json`. Extraction runs retain the
payloads and manifests. These local outputs are excluded from Git. Synthetic
tests need no game assets.

Stored extraction excludes the size prefix. No compression scheme, payload
format or rendering behavior is established by these results. Next: inspect
selected payloads and test compression hypotheses separately while preserving
stored bytes and provenance.
