# Targeted menu3D extraction — 2026-10-16

Only archive entries FF000CB9 and FF000CE0 were extracted and decompressed with
the existing BIG/POP-LZO tools. Original bytes and trailing bytes are preserved.
Both decoded SHA-256 values match the prior validation report exactly:

| Entry | Decoded bytes | SHA-256 |
| --- | --- | --- |
| FF000CB9 | 4469220 | `96244FE330C11ACDF2A87A7C8A410225B224F5F1B9F264834425848CBF4D00EB` |
| FF000CE0 | 132 | `678051B19CCA6CC1973B39A1288270EE9C80551F9FC832FEDE2A03452BD9A48E` |

## Record envelope observed in these two resources

At each record start, three little-endian uint32 fields occur:
payload length, marker `0xEEFFC099`, and a key. The next record starts at
`offset + 12 + payload_length`. This rule consumes the entire large decoded file
as 633 records, including zero-length payloads, with no uncovered remainder.
The small file is one record with a 120-byte payload. This is a validated boundary
observation for these files, not a universal WOW/WOL specification.

The large file's first key is `0x30000CB9`, distinct from archive ID `0xFF000CB9`.
Its payload begins with `.wow`; `menu3D` occurs at absolute decoded offset 24.
The small file has envelope key `0xCC0003FD` and fifteen eight-byte payload pairs:
a uint32 value followed by literal `.wow`. Its final pair at offset 124 contains
`0x30000CB9`, exactly matching the large file's first record key. This establishes
a concrete shared identifier, but does not prove runtime load order or the
semantics of the other fourteen entries. No arbitrary FF-prefix normalization is
performed and no additional resources were extracted.

## Scene evidence

The large file contains records whose payload begins with `.gao` (109 records).
Readable names include palms, trunks, plants, sky, fog, rain, lamps and cameras:

| Name | Absolute decoded string offset | Containing record start / key |
| --- | --- | --- |
| Camera02.gao | 321370 | 321338 / `0x30000CF0` |
| Menu3D_FarahRoom_CAM_Balcony.gao | 334809 | 334777 / `0x30000D63` |
| Menu3D_FarahRoom_CAM_BalconyTarget.gao | 335002 | 334970 / `0x30000D65` |
| Menu3D_lampions.gao | 343303 | 343271 / `0x3000FCFA` |

Additional names include Menu3D_palm5.gao, Menu3D_ground.gao,
Menu3D_FarahRoom_Balcony.gao, Menu3D_sky.gao, Menu3D_Fog3D.gao and GFX_Rain01.gao.
These provide much stronger scene evidence than the archive filename alone and
are consistent with the supplied menu captures. They do not establish which
camera is active or decode geometry, materials, transforms or texture data.

## Reproduction and validation

`src/probe_menu3d.py <decoded-wow> <decoded-wol> <new-output.json>` inventories
records, absolute name offsets, hashes and candidate key matches. It reads inputs
only and refuses to overwrite its output. Four synthetic regression tests cover
empty records/absolute offsets, truncated headers, truncated payloads and invalid
markers (`tests/test_menu3d_probe.py`). All passed, and the probe consumed both
real decoded inputs completely.

The local `menu3d-focused-4d627a9470c84b73bfc16ae467514310` report contains extraction
and decoding manifests, original/decoded/trailing bytes, strings.txt and
record-inventory.json. Game-derived output stays excluded from Git.

Next: inspect the bounded Camera02 and balcony-camera records and one simple
scene-object record; document their fields and internal key relationships before
attempting a geometry decoder. Audio/video and unrelated archive contents remain
outside this investigation.
