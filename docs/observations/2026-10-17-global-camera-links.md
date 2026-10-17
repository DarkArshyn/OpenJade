# Global camera links — 2026-10-17

Source: CameraAndGlobal decoded resource, SHA-256
`68c1323218f0c5479c5064a53ac3c60a329e45cba6c11c7f08affbb649484582`.
Local evidence: `reports/global-camera-links-20261017/global-camera-links.json`.
All offsets below are relative to individual record payloads.

## Reference chain

Camera.gao (CC000403) references 057CC738 at offset 197. That eight-byte payload
contains B60024E2 and 057CC737. B60024E2 is exactly 34 key/type pairs; its first
pair is B60024E1 with `.ova`. Remaining pairs use `.ofc` and `.ttt` tags.
These tags are observed strings, not decoded execution semantics.

057CC737 has three descriptors, three identifiers and a 20-byte value area at
64. B60024E1 has 211 descriptors, 211 identifiers and a 2028-byte value area at
3392. All three instance identifiers match exactly one definition identifier.
Their low 16-bit type tags agree; definition tags additionally contain 0x80000.
The first header words (812 and 892) are retained as opaque values. They must not
be rejected merely because earlier controller samples started with zero.

| Identifier | Instance offset / value | Definition offset / value | Tags |
| --- | --- | --- | --- |
| 2D0ED330 | 64 / approximately 0.01 | 4900 / approximately 0.1 | 22 / 80022 |
| A61FCA47 | 68 / approximately 0.1 | 5108 / 0.5 | 22 / 80022 |
| 39449276 | 72 / (0,0,8) | 5112 / (0,0,0) | 25 / 80025 |

Identifiers and tags are hexadecimal; offsets are decimal. The common field
identities, compatible widths and differing values support an instance/definition
relationship with instance-specific parameters. Actual override precedence and
runtime usage are not proven. No field is named as speed, timing or camera offset.
The (0,0,8) triplet is not yet a verified translation of Camera.gao.

## Secondary link

Camera.gao also references 55000013 at offset 201. This 43-byte record begins
with key 55000012, whose payload is 42 bytes. Both raw payloads are preserved in
the JSON. Their remaining encoding is unresolved; neither is decoded as CF1.
This branch does not yet establish animation, interpolation or active-camera state.

## Implementation and validation

`inspect_global_camera_links.py` requires the exact source hash, rejects missing
or duplicate selected record keys, checks field-table bounds and unique identifier
matches, and retains upper type bits and unknown trailing data. It decodes only
the selected single float/triplet field types, not the whole behavior language.
Three synthetic tests pass: nonzero headers/flagged tags, truncation and field
extent overrun. The real two tables and three field correspondences pass checks.

```powershell
python .\src\inspect_global_camera_links.py <CameraAndGlobal-decoded.bin> <new-output-directory>
python .\tests\test_global_camera_links.py
```

No game data was modified. No camera motion or field-driven transformation was
applied to the viewer. Next: trace use of these identifiers through the referenced
behavior records, or identify the 55000013/55000012 encoding with independent
evidence. Names and effects must remain unknown until that relationship is verified.
