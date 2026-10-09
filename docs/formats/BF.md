# BF: observed index layout

Status: implementation model established through local research; not a general Jade
Engine specification. Reviewed 2026-10-09.

Reproducible implementation: `src/OpenJade.BF.psm1`. Validation procedure:
`tests/Test-BF.ps1`. Both are included in this project. See the dated BF
observation record for the local dataset used to verify this model.

| Offset/position | Size | Interpretation used by the tools |
| --- | ---: | --- |
| File offset 0 | 4 | Unsigned little-endian header size |
| File offset 4 | variable | Consecutive index entries |
| `4 + HeaderSize` | variable | Data area |

Each index entry has five unsigned little-endian 32-bit fields, followed by the
filename bytes:

| Field | Current interpretation |
| --- | --- |
| EntryOffset | Preserved; exact meaning not independently established |
| DataOffset | Offset relative to the data area |
| DataLength | Number of stored bytes to extract |
| Unknown | Preserved without interpreting it |
| FileNameLength | Number of filename bytes |

`AbsoluteDataStart = 4 + HeaderSize + DataOffset`.
`AbsoluteDataEnd = AbsoluteDataStart + DataLength` (exclusive).
The index must end exactly at the data area. No decompression is performed.

The initial reader accepts ASCII filenames and trims trailing NUL bytes. It
rejects other filename bytes rather than guessing an encoding. Extraction
rejects duplicate/colliding names, absolute paths, traversal, Windows device
names, existing output roots and reparse points in existing output ancestors.
It does not claim protection against concurrent hostile filesystem changes.

Unknowns: other BF variants, general filename encoding, compression in other
archives, the semantics of EntryOffset/Unknown and archive reconstruction.
Do not infer support for `prince.bf` from success on `POPData.BF`.
