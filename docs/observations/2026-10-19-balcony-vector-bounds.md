# Balcony vector bounds — 2026-10-19

## Result and scope

The principal arithmetic in dynamic function 5b83 is **component-wise bounding**
of its vector argument, conditional on object fields. This follows the
[located function bodies](2026-10-19-camera-function-bodies.md).
For ordinary finite values with ordered limits, each output component is:

`clamp(input[i], field464[i] - field172[i], field512[i] + field172[i])`

The operation is repeated for the three components. This is a static interpretation,
not a native execution test or a complete floating-point specification. NaNs,
infinities, inverted bounds and mixed scalar types have not been validated.
No camera position, matrix or viewer behavior was changed.

## Native corroboration

The known PC GOG executable hash applies. Selected table entries resolve to:

| ID | Handler VA | Evidence |
| --- | --- | --- |
| Category 04: 0200 / 0201 / 0202 | 004654c0 / 004654e0 / 00465520 | Select float component at byte offset 0 / 4 / 8; preserve a destination reference |
| 08a7 | 004a0070 | Scalar subtraction (float path used for vector components) |
| 08a8 | 004a0160 | Scalar addition (float path used here) |
| Category 03: 17e5 | 0049b2b0 | Compare input with upper and lower limits, select bounded scalar |
| 0898 | 004a0a20 | Assign selected scalar to destination reference |
| 08a1 | 0049f600 | Equality comparison; relevant mode operands are integers |
| 0804 | 0049ee40 | Advance one node without another stack operation |

The 17e5 comparison and selection were checked against its assembly. The final
export decompiled ten functions successfully. Results are local under
`reports/native-vector-bounds-20261019/evidence/`.

## Conditional paths

In B60024E5's 5b83 body, argument local 0 is first copied to result local 12.
Mode field 436 selects paths:

- Value 2: the branch also checks object-related field 396 and includes a call
  to 1007 on one side path; that call's effects remain unexamined. Bounding then
  requires field 276 to be nonzero.
- Values 3 or 4: an alternative path also requires field 276 to be nonzero and
  contains the same three component-bound expressions.
- Other mode values, or a false field-276 gate on these paths: the result local
  stays unchanged by the bounding expressions.

Selected target calculations confirm the exits: 5912 + 59*8 = 6384,
5984 + 49*8 = 6376, 6376 + 61*8 = 6864,
6448 + 52*8 = 6864, 6464 + 49*8 = 6856, and 6856 + 1*8 = 6864.
The result is copied to local 24, transferred to the return stack and returned.
The field labels above are offset-based descriptions, not recovered variable names.

## Stored field evidence

The frozen Menu3D SHA-256 is
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
Fields were matched by identifier between definition B60024E8 and instances
30000D61 (CAM_Balcony) and 3C00144B (CAMALT_Balcony).

| Definition offset | Identifier | Stored definition | CAM_Balcony / CAMALT_Balcony |
| ---: | --- | --- | --- |
| 0 | D1F1EDB4 | (0,0,0) | No matching instance entry |
| 172 | 43087E2F | (0,0,0) | No matching instance entry |
| 276 | C4E1F69A | 0 | No matching instance entry |
| 396 | 3A1A5C4C | 0 | 30000D63 / 3C00144D, matching the respective GAO keys |
| 436 | D5C3E471 | 0 | 2 / 2 |
| 464 | BD8A1B61 | (0,0,0) | No matching instance entry |
| 512 | 833FD3E9 | (0,0,0) | No matching instance entry |

Identifiers and reference values are hexadecimal; offsets/scalars are decimal.
A missing instance entry is **not** proof of a runtime zero, a disabled behavior,
or a fixed default: initialization and later writes may populate these fields.
In particular, the archived zero bounds must not be used to collapse the camera
vector to zero in a simulation. Object activation and coordinate space are unknown.

## Tools and validation

```powershell
python .\src\inspect_balcony_bounds.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\balcony-bounds-new
python .\tests\test_balcony_bounds.py
```

The reader validates the source hash, unique selected records and field identity,
type compatibility and value bounds. It preserves raw bytes, upper type flags and
explicit absence of instance entries. Two synthetic tests cover flagged vectors,
array rejection and value overrun. Real-data inspection verifies seven fields
against both instances. Recorded output: `reports/balcony-bounds-20261019/fields.json`.

Native script `OpenJadeVectorBounds.java` uses the established headless workflow
with `-readOnly -noanalysis`, a new report directory and the existing project.
Temporary function creation is discarded; recovered code stays in ignored reports.

Next: trace writes to fields 172, 276, 464 and 512 in this model's linked behavior
blocks, to determine how the gate and limits are initialized or updated. This is
needed before applying the bounded-vector behavior to a reconstructed camera.
