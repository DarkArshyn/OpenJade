# MFT: observed PC GOG font layout

Status: partial, based on the twelve Atlantis MF Regular files extracted from
POPData.BF. This is not a general specification for all Magma Font variants.
All integer and float fields below are little-endian. Ranges are half-open.

| Offset | Length | Observed interpretation |
| --- | --- | --- |
| 0 | 11 | ASCII `Magma Font` followed by NUL |
| 11 | 4 | Header word 110; version semantics unconfirmed |
| 15 | 64 | NUL-terminated ASCII name slot, including preserved padding |
| 79 | 4 | Size word matching the filename's number |
| 83 | 1 | Unknown byte |
| 84 | 5152 | 224 records of 23 bytes, codes 32 through 255 |
| 5236 | 8 | Unknown bytes; float32 interpretations -2.078125 and 0.3125 in this corpus |
| 5244 | 2 | Atlas width |
| 5246 | 2 | Atlas height |
| 5248 | width * height | Uncompressed one-byte pixels |

Each glyph record contains a uint16 code at +0, five bytes at +2, and four
float32 UV coordinates at +7. The first two byte fields match rectangle width
and height minus one in the UV-derived geometry. The remaining bytes are
exported as Metric2Raw, Metric3Raw and Metric4Raw. Bearings, signedness,
baseline and advance interpretations are hypotheses, not validated semantics.

For every observed record, `u0 * width - 0.5`, `v0 * height - 0.5`,
`u1 * width - 0.5`, and `v1 * height - 0.5` are integral. Their horizontal
and vertical differences equal the respective metric plus one. The reader
rejects layouts that do not satisfy these observed constraints. Exported
AtlasRight/AtlasBottom are those coordinate values, not a certified crop rule.

Mapping raw pixel values directly to grayscale produces recognizable upright
glyphs. Alpha coverage, filtering, exact crop boundaries, extended character
encoding, spacing and game rendering remain unverified. Code numbers are
retained without assuming a Unicode or Windows-1252 mapping.

## Usage

Run from the repository root in Windows PowerShell 5.1:

```powershell
.\tools\Read-MFT.ps1 -Path '.\reports\POPData-extracted\menu\fonts\atlantis mf regular 36.mft' -OutputDirectory '.\reports\font-36'
.\tests\Test-MFT.ps1 -FontDirectory '.\reports\POPData-extracted\menu\fonts'
```

The output directory must be new. Exports include the unchanged source.mft,
atlas.png (opaque grayscale), glyphs.csv (raw metrics, UVs and byte offsets),
and font.json (source SHA-256, dimensions, unknown fields and interpretation
limits). The complete source copy preserves name padding and every unknown
byte. No game source is modified. Omitting OutputDirectory only reads data.
