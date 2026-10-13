# POP block-envelope decoding

Date: 2026-10-13. Scope: classic LZO1X and equal-size verbatim blocks within
recognized PC GOG POP envelopes. See [research provenance](../../references/lzo.md).

## Inputs and boundaries

`tools/Expand-POPLzo.ps1` accepts a stored payload produced by `Extract-BIG.ps1`,
not a whole BIG archive. It requires the existing
[bounded envelope probe](BIG-compression.md) to recognize the input. Unknown
resources are refused rather than guessed to be uncompressed.

Every block uses the declared size pair from the probe. Equal sizes select
a verbatim copy. Unequal sizes select the classic LZO1X decoder. A compressed
block must consume every stored byte, terminate with the canonical `11 00 00`
marker, and produce exactly its declared length. Invalid dictionary distances,
truncated instructions, excessive output and bytes after the end marker fail.
Each block has a separate dictionary. Overlapping matches copy forward.
The decoded resource must preserve the candidate marker at decoded offset 4.

Maximum decoded block length is 131,072 bytes. Stored input is capped at 64 MiB;
total decoded output defaults to 64 MiB and can be reduced with MaxDecodedBytes.
Limits are checked before allocating the combined output. Linux LZO-RLE,
preset dictionaries, compression/repacking and other envelope variants are
outside the supported scope. These limits deliberately bound this research tool.

## Output contract

OutputDirectory must be new, outside the project's game directory, and have
no reparse-point ancestors. Input is opened read-only with writes/deletion
denied while processing. Decoding completes before the output directory is
created. Subsequent I/O failure may leave partial outputs; retry in a new path.

| File | Meaning |
| --- | --- |
| source.stored.bin | Exact unchanged copy of the input payload |
| decoded.bin | Concatenation of decoded or verbatim block data |
| trailing.bin | Exact bytes after the parsed envelope, including nonzero bytes |
| decoding.json | Source path, hashes, sizes, per-block ranges/methods and output verification |

All three output data files are read back for SHA-256 verification before the
manifest is written. Block offsets are relative to the stored payload; decoded
offsets refer to the concatenated output. Keep the original extraction manifest
to relate the source payload hash to the archive ID and absolute byte range.
An explicit zero-pair terminator is inside ParsedLength and remains in the
stored copy. Trailing bytes are not assumed to be disposable padding.

OutputVerified means written files match the computed bytes. It does not mean
resource semantics or rendering behavior are understood. The earlier structural
probe continues to return CodecValidated=false because it does not decode.

## Implementation and tests

PowerShell handles file paths, reports and framing. `src/OpenJade.Lzo1x.cs`
handles the byte-level decoder and is compiled locally by Add-Type on module
import. No external codec DLL is needed for ordinary use. Restart PowerShell
after changing that C# source, since loaded types cannot be replaced in-place.

```powershell
.\tools\Extract-BIG.ps1 -Path .\game\TSoT-GOG\prince.bf -Id '0xFD3F0142' -OutputDirectory .\reports\lzo-input
.\tools\Expand-POPLzo.ps1 -Path .\reports\lzo-input\FD3F0142.stored.bin -OutputDirectory .\reports\lzo-decoded
.\tests\Test-POPLzo.ps1
```

Synthetic tests require no game data or reference DLL. Optional ReferenceDll
enables official-miniLZO differential checks; optional GameArchive decodes
every currently recognized candidate and writes per-resource hashes. These
tests retain reports, not a full decoded copy of the archive. See
[recorded results](../observations/2026-10-13-lzo.md).
