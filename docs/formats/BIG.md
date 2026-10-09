# BIG v37: bounded index inspection

Date: 2026-10-09. External reference: Swyter's
[BIG template, version 2023.01.30](https://github.com/Swyter/poptools/blob/c1535e8df1e0e0a4336ba813ec041d0bc86f0ed8/pop_prince_bf.bt).
See `references/poptools.md` for provenance. Local checks are recorded in
`docs/observations/2026-10-09-big.md`.

The implemented model distinguishes BIG from POPData.BF:

| Byte offset | Observed interpretation |
| --- | --- |
| 0 | Four-byte signature 42 49 47 00 |
| 4 | Little-endian UInt32 version; only 37 is accepted |
| 8 | Little-endian UInt32 index entry count |
| 68 | Start of numeric entries, each an offset/ID pair of UInt32 values |
| Referenced block offset | UInt32 stored length followed by payload bytes |

PayloadOffset is BlockOffset + 4. EndOffset is exclusive and includes the
declared payload length. Unknown header words are preserved by offset; their
meaning is not inferred. Payloads are not decoded.

Names are read from bounded 84-byte metadata records, associated by index ordinal.
The table begins at `68 + 8 * Capacity`, where Capacity is the UInt32 at header
offset 32. This is distinct from the active entry count. The supported metadata
model requires the word at 36 to be 1 and the declared index offset at 52 to be
68. Other descriptor layouts retain numeric results with a diagnostic and no
invented names. Other BIG versions and byte orders remain refused.

| Relative record offset | Meaning used by the reader |
| --- | --- |
| 0 | Raw size word; low 31 bits compared with the block prefix |
| 4, 8, 12, 16 | Uninterpreted UInt32 values, exported by relative offset |
| 20 | 64-byte name slot with NUL termination |

The size high bit is retained separately, not treated as proof of compression.
Names are accepted only when non-empty, NUL-terminated and printable ASCII.
Whitespace is not trimmed. Invalid names retain all 64 raw bytes as hexadecimal
and receive a diagnostic. No synthetic filename replaces missing evidence.
Metadata outside the file or overlapping indexed blocks is not decoded.

External research reference: FulGerNet/pop-bf-lab, revision
`76ac78a10751a08fda67e8d5f711171e6f2d9605` (2026-09-27),
[archive reader](https://github.com/FulGerNet/pop-bf-lab/blob/76ac78a10751a08fda67e8d5f711171e6f2d9605/bf_lab/archives.py).
The table arithmetic was independently checked against the local PC GOG file.

## Tool contract

`tools/Read-BIG.ps1` returns Summary, HeaderHex, HeaderFields, Entries and
Diagnostics. It uses a read-only stream and does not load the whole archive
into memory. Computing the SHA-256 still reads the full file.

Malformed headers, unsupported versions and an index that cannot fit cause an
error. Individual invalid block ranges, duplicate IDs and overlapping blocks
remain in the report with diagnostics. Invalid metadata names or mismatched
lengths also receive diagnostics. Overlap is an observation, not proof of
corruption. Zero-length payloads and an empty index are supported.

With OutputDirectory, reports include index.csv, header-fields.csv,
header-hex.txt, summary.json and diagnostics.json. The directory must be new.
No extraction, decompression or archive rewriting is performed.

## Stored extraction contract

`tools/Extract-BIG.ps1` selects exactly one entry by unsigned decimal ID or a
quoted hexadecimal ID. It copies exactly `StoredLength` bytes from
`PayloadOffset`, excluding the four-byte size prefix. No decompression or
payload interpretation is performed. The metadata size high bit is preserved.

The destination must be new. Output under the project's `game` directory or
through a reparse point is refused. The filename is `XXXXXXXX.stored.bin`,
derived from the ID; embedded names never become paths. Any archive diagnostic,
including duplicate IDs, prevents extraction. Missing IDs fail before writing.

A read-only source handle remains open during indexing and copying; on Windows
it denies concurrent write/delete access. Copying uses a 64 KiB buffer. The
archive SHA-256 requires a full source read. The payload is hashed during copy,
then the output is read back to check its hash and length. `extraction.json`
records the name, ID, source range, raw size metadata, archive and payload
hashes. EndOffset is exclusive. `Verified` describes copy integrity only.

Existing outputs are never overwritten. An I/O failure may leave partial
output; no verified manifest is written before copy verification succeeds.
Use a fresh directory when retrying. Generated game resources remain local.
