# Global camera field-use candidates — 2026-10-17

Source: CameraAndGlobal decoded resource, SHA-256
`68c1323218f0c5479c5064a53ac3c60a329e45cba6c11c7f08affbb649484582`.
This follows the [instance/definition correspondence](2026-10-17-global-camera-links.md).

## Identifier versus offset evidence

Each of the three identifiers occurs exactly twice in this resource: once in the
instance table 057CC737 and once in definition table B60024E1. None occurs in the
linked behavior payloads. Therefore searching identifiers alone does not locate
behavior uses. This does not establish how the runtime resolves them.

Searching the definition-relative field offsets within the `.ofc`/`.ttt` records
listed by B60024E2 gives these six matches:

| Field identifier | Value offset | Record key | Payload match offset | Following word |
| --- | ---: | --- | ---: | --- |
| 2D0ED330 | 1508 | B6002512 | 5072 | 14000022 |
| 2D0ED330 | 1508 | 080009C9 | 6256 | 14000022 |
| A61FCA47 | 1716 | B6002512 | 3760 | 14000022 |
| A61FCA47 | 1716 | 080009C9 | 5768 | 14000022 |
| 39449276 | 1720 | B60024DE | 19016 | 14000025 |
| 39449276 | 1720 | B60024DE | 19160 | 14000025 |

Keys and following words are hexadecimal; offsets are decimal. All matched
records are listed as `.ofc`. In all six cases the low 16 bits of the following
word match the field type: 22 for a float candidate, 25 for a triplet candidate.
This recurring offset/type pattern supports field-access candidates. It is not
an instruction decoder and does not establish reads, writes or execution order.

The scalar candidates occur in two shared blocks, while both triplet candidates
occur in B60024DE. A candidate neighborhood for the triplet is
`25 00 00 05 b8 06 00 00 25 00 00 14`; the four bytes `b8 06 00 00`
encode 1720. The preceding and following words remain uninterpreted.
No movement, speed, damping or offset meaning is assigned to these fields.

## Reproduce and checks

```powershell
python .\src\trace_global_camera_fields.py <CameraAndGlobal-decoded.bin> <new-output.json>
```

Local evidence: `reports/global-camera-field-uses-20261017/field-uses.json`.
The script checks the source hash and record envelopes, limits offset searching
to explicitly linked `.ofc`/`.ttt` records, preserves duplicate record occurrences,
and exports contexts with payload offsets and following words. The real-data
report confirms two identifier occurrences and two typed-offset candidates per
field. No additional test-suite run is claimed for this observation.
All game inputs remain read-only.

Next: establish instruction boundaries and operand conventions in B60024DE,
B6002512 and 080009C9, ideally using an independently corroborated behavior
format. Do not infer camera effects from these byte patterns alone.
