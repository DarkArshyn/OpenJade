# Camera controller field tables — 2026-10-17

Source: the same frozen FF000CB9 decoded payload used by the camera projection
experiment (SHA-256 `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`).
Evidence: local `reports/camera-controllers-20261017/controllers.json`.

## Structural result

Three camera-linked blocks fit the same bounded layout:

1. uint32 zero and descriptor byte length;
2. 12-byte descriptors: value offset, count, type tag;
3. one opaque uint32;
4. one four-byte identifier per descriptor;
5. uint32 value byte length followed by that value area;
6. preserved trailing bytes (20 zero bytes in these three samples).

| Block | Descriptors | Values start | Values length |
| --- | ---: | ---: | ---: |
| 30000D61 (Balcony-linked) | 14 | 240 | 64 |
| 3C00144B (Alternate-linked) | 13 | 224 | 68 |
| 30000CF2 (Camera02-linked) | 4 | 80 | 16 |

Offsets are decimal and payload-relative. All descriptor counts are one.
Field widths are derived from consecutive offsets and the value-area length.
Type meanings remain hypotheses: 0x21 integer-like, 0x22 float-like,
0x25 three floats, 0x28 object-key-like. Camera02 uses 0x2D for its object key.
The identifiers may be hashes, but their algorithm and source names are unknown.

## Stable field identities

Matching identifiers align the fields despite differing descriptor order:

| Identifier | Tag | Balcony-linked value | Alternate-linked value |
| --- | --- | --- | --- |
| 40799682 | 28 | 30000D65 (BalconyTarget) | 3C00144E (AlternateTarget) |
| 3A1A5C4C | 28 | 30000D63 (Balcony GAO) | 3C00144D (Alternate GAO) |
| 8EBECF87 | 25 | approximately (1e-10, 0, 0) | same |
| D5C3E471 | 21 | uint32 2 | uint32 2 |
| 7AEFD6E7 | 22 | float32 1.29999995 | same |

Identifiers, tags and keys in the table are hexadecimal. Balcony additionally
has field CE36F96D/tag28 referencing Alternate (3C00144D), and field 496E1004/tag21
with uint32 value 3. Alternate instead has field 411B340F/tag25 containing a
zero triplet. These differences do not prove switching, interpolation or timing.
Camera02-linked block 30000CF2 has field 3B2F660C/tag2D referencing Camera02.

## Positioning implications and corrections

The nonzero world-position candidates remain in the referenced GAO transforms;
these controller value areas contain no matching nonzero position triplets.
The inspector exports those GAO names and candidate positions alongside the
references. Shared camera and target fields strengthen the interpretation of a
camera/target relationship, but do not establish the runtime orientation rule.
A controller could calculate a position from these references at runtime.
Its executable behavior, active state and interpolation are not decoded here.

Previously inspected float-like numbers such as 3.899811 and 9.700210 occur in
this identifier table, not the value area. They must not be interpreted as
camera distances, timing or coordinates. The common actual value 1.3 remains
semantically unknown: it is not established as FOV, speed or duration.

## Reproduce

```powershell
python .\src\inspect_camera_controllers.py <decoded.bin> <new-output-directory>
python .\tests\test_camera_controllers.py
```

The inspector checks the source hash, descriptor bounds, value extents and
single-item counts; it preserves raw values and trailing bytes. Three synthetic
tests pass, covering field extraction, truncation and invalid extents. All three
real blocks pass the parser. Input is read-only and output must be new.

Next: investigate behavior attached to the controller identifiers and the
Camera02-linked 30000CF1 record. Its encoding is not identified; treating it as
an aligned float array or assuming it is a camera animation would be premature.
