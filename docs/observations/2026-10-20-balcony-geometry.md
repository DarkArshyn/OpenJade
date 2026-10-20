# Serialized balcony bounds — 2026-10-20

## Evidence and scope

The previously exported PC GOG loader `0067df50` connects GAO data to the
structure at object +0x10. Its allocation in `0067cf60` is 0x30 bytes when object
flag 0x80000 is clear, and 0x48 when set. Both selected balcony GAOs have stored
flags 0x0000A020, so the smaller branch applies to their initial construction.

Assembly at `0067e2b5` onward reads two consecutive triplets through `00424630`
into structure offsets +0x18 and +0x24. It also copies them to +0 and +0x0c.
Those first destinations are exactly the normal-branch inputs used by the
previously inspected operations 2bc3 and 2bc5.

The compact layout is important: the loader has a two-byte versus four-byte
metadata branch and an optional four-byte skip before the triplets. The observed
records match the compact branch (two bytes, no skip). This observation is not a
general GAO parser or a dynamic observation of loader globals.

Local native evidence, checked against assembly:
`reports/native-gao-volume-20261019/evidence/0067df50-assembly.txt` and
`reports/native-gao-layout-20261019/evidence/` (constructor and triplet/matrix
readers). These reports remain excluded from Git. No recovered implementation is
included in the independent inspector.

## Stored values

Offsets below are decimal and relative to the GAO payload. Values are rounded
here; the JSON report preserves decoded float values and the original 24 bytes.

| GAO key | Name suffix | Triplets offset | Lower triplet | Upper triplet |
| --- | --- | ---: | --- | --- |
| 30000D63 | CAM_Balcony | 131 | (-11.817912, -5.711825, -2.830470) | (-8.514531, -0.577225, 1.478624) |
| 3C00144D | CAMALT_Balcony | 134 | (-6.821115, -4.201357, -0.476645) | (-6.490778, -3.687897, -0.045735) |

Both records have version 10 and the same flags. A name length N precedes the
name; the 68-byte matrix begins at N+30, and these triplets at N+98.
The trailing 26 bytes are preserved without assigning new semantics.

The loaded word at structure +0x14 comes from the last component of the upper
triplet. Neither selected value matches the special masked sentinel used by
2bc3/2bc5. Therefore their initial stored structures select the paired-triplet
case, not the symmetric scalar case, if unchanged before those operations run.

This establishes the serialized source for the limits used by
[callback index 5](2026-10-19-bounds-writers.md). It does **not** establish the
runtime coordinate frame, later mutations, active camera, callback scheduling,
or the enabling value of field 276. No limits are applied in the viewer yet.

## Reproduction and validation

```powershell
python .\src\inspect_balcony_geometry.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\balcony-geometry-new.json
python .\tests\test_balcony_geometry.py
```

The reader requires the frozen Menu3D SHA-256 used by the earlier inspectors,
unique selected keys, the observed header/flags, exact compact extents, a
terminated name, finite values and ordered triplets. Three synthetic tests
cover correct offsets, unsupported/truncated layouts and invalid limits.
The real-data check reads both objects without changing the source.

Next: trace field 276 activation and possible native mutation of these bounds
before using this static evidence to constrain the camera preview.
