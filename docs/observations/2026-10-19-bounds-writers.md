# Bounds-writing callback — 2026-10-19

## Confirmed writes

The eight OFC records linked by B60024E9 contain a short writer in `3200000F`.
Its token area has 23 nodes. Payload offsets are decimal:

| Offset | Effect supported by previously decoded assignment handlers |
| ---: | --- |
| 48 | field464 = result of object-associated triplet operation 1fa5 |
| 72 | field512 = field464 |
| 96 | field464 += result of 2bc3 |
| 120 | field512 += result of 2bc5 |

Thus the stored zero triplets are not sufficient to model the effective bounds.
If this callback executes, it constructs both limits from object-associated data.
Neither the execution time nor the active camera has been observed dynamically.

## Source triplets

The PC GOG native table maps 2bc3 to `00485ee0`, and 2bc5 to `00486040`.
Both use the structure referenced at object offset 0x10:

- Normal branch: 2bc3 reads components at 0x18/0x1c/0x20; 2bc5 reads
  0x24/0x28/0x2c.
- Special branch: when the word at 0x14 satisfies the inspected mask comparison,
  both use the scalar at 0x0c, negated for 2bc3 and positive for 2bc5, repeated on
  all three axes.

These symmetric scalar and paired-triplet cases support a geometric-bound
interpretation. The exact native structure type, coordinate system and source
resource mapping remain unverified. The earlier 1fa5 handler uses the
object-associated triplet helper discussed in [vector consumers](2026-10-18-vector-consumers.md).
No original implementation is copied into project code.

Other operations in this writer were inspected to avoid confusing their writes
with variable-field writes: 178e updates a byte at +0x2c in the structure reached
through object +0x18; 2baf conditionally updates a byte in another indexed object
structure. Neither inspected handler explicitly assigns the requested variable
fields 172 or 276. This does not exclude indirect side effects elsewhere.

## Why this is an initialization lead

After the definition-variable values in B60024E8, the trailing data contains five
fixed callback references followed by a count of six indexed callbacks. Index 4
references 32000010; **index 5 references 3200000F**. The populated indexed entry
is at payload offset 2020. Empty entries retain their indices.

Native loader `0045f2a0` reads the count and resolves the indexed references into
runtime fields +0x2c/+0x30. Dispatcher `00463490` selects the corresponding entry
by its second argument and invokes the evaluator with that object's context.
Its flags can suppress execution. The previously examined function `0067a060`
calls this dispatcher with argument 5 during its object-processing path after
reference resolution. This gives a static callback/initialization chain, not a
proven event name, scheduling guarantee or live invocation on a balcony object.

## Fields 172 and 276 remain unresolved

The scoped inventory found 31 direct category-14 references to the four requested
fields across eight linked blocks. The uses of 172 and 276 are confined to the
already decoded 5b83 reader: component arithmetic for 172 and branch conditions
for 276. No direct assignment to either field was found in this scope.

Both have stored zero defaults in B60024E8 and no matching entries in the two
balcony instances. This establishes archived values only. It does not prove
runtime zeros, that bounding is disabled, or that no other object/native path
writes them. Indirect writes, alternate categories, callbacks attached elsewhere
and live override precedence remain outside the demonstrated result.

## Tools and validation

```powershell
python .\src\inspect_balcony_writers.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\balcony-writers-new
python .\tests\test_balcony_writers.py
```

The reader verifies the frozen Menu3D hash, unique selected records, linked token
extents, exact twelve-node writer sequence and callback-array bounds. It preserves
all selected use windows without labeling every nearby assignment a field write.
Two synthetic tests verify callback index preservation and malformed extents.
The real-data run confirms eight blocks, 31 uses, four writes and callback index 5.

Local report: `reports/balcony-writers-20261019/writers.json`.
Native evidence: `reports/native-bounds-callbacks-20261019/evidence/` (seven
functions decompiled), plus the earlier loader and caller reports. Native script:
`tools/ghidra/OpenJadeBoundsWriters.java`, using the established
`-readOnly -noanalysis` headless command and a new output directory.
Game data remains unchanged; native evidence stays excluded from Git.

Next: identify the serialized structure behind object +0x10 to recover the actual
geometric limits. Separately investigate activation-field 276 through loading and
external behavior references before deciding whether to apply bounding in the viewer.
