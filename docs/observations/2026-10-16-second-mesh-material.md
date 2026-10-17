# Second mesh and material selection hypothesis — 2026-10-16

Read-only investigation of the existing FF000CB9 decoded scene.

SHA-256 : `96244FE330C11ACDF2A87A7C8A410225B224F5F1B9F264834425848CBF4D00EB`.
No additional archive extraction or external source was used.

## Second object: Menu3D_fake_fog.gao

The object refers to mesh candidate `0x30000C7A`, record offset 486865,
payload size 668. At payload +408, uint32 values 10 and 20 describe a candidate
vertex count and stride. The following ten XYZ triplets exactly equal the ten
triplets at +44. At +616 a uint32 value 48 equals the remaining index byte count.
The twenty-four uint16 values form eight nondegenerate triangles, all indices
within 0..9. They consume the record exactly:

`(5,6,0), (0,1,5), (7,5,1), (1,2,7), (8,7,2), (2,3,8), (9,8,3), (3,4,9)`.

This corroborates the ground's count/stride/XYZ and terminal triangle-list
interpretation on a second, larger object. The additional two floats per vertex
are retained as raw candidate attributes, not exported as verified UVs.

## Selection field

The ground repeats uint32 25 at payload +112 and +160. Fake fog repeats 24 at
+248 and +392. In each final group the latter occurrence is sixteen bytes before
the vertex-count/stride header, followed by the triangle count. Both objects
refer to the same 35-key collection `0x30000CB3`.

A bounded corroboration searched only the same single-group layout inside the
already decoded scene. Ten records satisfy duplicate XYZ, stride 20, complete
terminal index-byte extent and matching triangle count:

| Record key suffix (prefix 0x3000) | Candidate selector | Vertices | Triangles |
| --- | --- | --- | --- |
| 0C70 | 0 | 45 | 40 |
| 0C76 | 24 | 6 | 4 |
| 0C77 | 25 | 34 | 55 |
| 0C7A | 24 | 10 | 8 |
| 0C7E | 0 | 45 | 40 |
| 0C80 | 25 | 4 | 2 |
| 0C84 | 0 | 45 | 40 |
| 0C86 | 3 | 120 | 128 |
| 0C87 | 23 | 20 | 16 |
| 0C88 | 20 | 10 | 8 |

Repeated zero values support zero-based indexing rather than an ordinary
one-based index. This does not exclude a special zero sentinel or prove the
runtime semantics. The best current selection hypothesis is:

| Object | Zero-based slot | Material candidate | Its key at payload +44 | Linked payload bytes |
| --- | --- | --- | --- | --- |
| Ground | 25 | 0x30000CAC | 0x30000C67 | 736 |
| Fake fog | 24 | 0x30000CAB | 0x30000C66 | 11000 |

The two material candidates are 48-byte records beginning with uint32 5 and 6.
Their linked payloads have repeated structured headers; raw uint16 pairs at +12
are (32,32) and (128,64), respectively. These could be texture dimensions, but
the image format and sampling/binding semantics have not been decoded here.
No texture has been assigned to the exported meshes.

## Evidence and limits

`reports/menu3d-second-object/comparison.json` stores exact vertex/attribute
values, triangles, selectors and both zero-based and one-based alternatives.
Two untextured OBJ exports accompany it. Assertions passed for duplicate XYZ,
complete byte coverage, index bounds, triangle counts and nonzero 3D triangle
areas for ground and fake fog. These are targeted research checks, not a claim
of general format coverage or verified visual equivalence.

Next: inspect the two linked texture candidates and validate their pixel formats
and dimensions before testing the selected materials on these meshes.
