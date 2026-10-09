# BIG payload compression assessment

Date: 2026-10-09. Scope: local PC GOG BIG v37 payloads.

## Hypothesis and provenance

FulGerNet's [lzo.py](https://github.com/FulGerNet/pop-bf-lab/blob/76ac78a10751a08fda67e8d5f711171e6f2d9605/bf_lab/lzo.py)
at revision `76ac78a10751a08fda67e8d5f711171e6f2d9605` describes a POP envelope
around LZO blocks. OpenJade independently tests the size-pair and marker
hypothesis against archive bytes. No upstream decoder, DLL or engine source
is imported. The referenced decoder has not been validated by this work.

The observed byte sequence `99 C0 FF EE` is not a universal LZO magic number.
Its position is only an initial candidate filter. The reference also mentions
`99 C0 FF FE`; that variant is tested synthetically, not observed locally.

## Structural probe

At payload offset zero, the candidate begins with two little-endian UInt32
values: declared decoded size and stored block size. The block data starts
eight bytes later. The next pair is immediately after those stored bytes.

The first marker must fit inside the first declared block. At payload offset
12, the two sizes must be equal; at offset 13 or 14, decoded size must exceed
stored size. This is a limited recognition hypothesis, not exhaustive detection.

For each block, declared decoded size must be 1 through 131,072 (0x20000),
stored size must be positive, and stored data must fit inside the payload.
A decoded size below 131,072 ends the candidate chain. After a full block,
another block, an explicit zero/zero pair or the exact payload boundary is
accepted. A partial header is invalid. Zero sizes elsewhere are rejected.

The probe does not allocate a decoded buffer or execute a codec. Equal sizes
are recorded, not taken as proof of a raw block's semantics. Declared decoded
totals remain unverified. All trailing bytes stay outside the parsed chain;
only their length and first 32 bytes are recorded. They are not assumed to
be padding, zero-filled throughout, or safe to discard.

## Results and commands

`Get-OpenJadeBlockEnvelope` inspects a seekable stream range and returns relative
block offsets. `Get-OpenJadeBIGCompression` reads the archive index and exposes
absolute archive offsets in its Blocks table. Inputs are read-only. Archive
diagnostics prevent inspection. Prefixes and headers are read in bounded ranges;
the archive hash still requires a full source read.

`tools/Read-BIGCompression.ps1` returns Summary, Entries and Blocks. Optional
OutputDirectory writes `summary.json`, `entries.csv` and `blocks.csv`. It must
be a new directory outside `game`, without reparse points in its path.

| Status | Interpretation |
| --- | --- |
| BoundedCandidate | Marker and block sizes satisfy the tested structural hypothesis |
| InvalidCandidate | Marker found, but size/position/chain checks failed |
| NoRecognizedEnvelope | This probe found no supported marker; compression remains unknown |

`CodecValidated` is always false. A bounded candidate can still contain an
invalid compressed stream. False negatives are possible because compression
without these markers or with different framing is outside this probe.

## Next validation gate

Before exposing decompression, validate an independent LZO1X decoder using
known vectors and an independent implementation. Test truncated input, invalid
back-references, output limits, end markers, exact consumed lengths and exact
decoded lengths. Then compare selected single/multiple-block game payloads,
retaining input/output hashes and original stored bytes. No recompression or
game archive modification is required.
