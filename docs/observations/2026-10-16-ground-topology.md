# Ground topology candidate — 2026-10-16

This follows the [camera/ground inspection](2026-10-16-menu3d-camera-ground.md).
Only the existing decoded menu3D resource was read. No new archive extraction or
external engine code was used.

## Observed layout

Record key `0x30000C80`, envelope offset 512717, has 280 payload bytes. Payload
offsets +176/+180 contain uint32 4 and 20. At +184, four stride-20 records start
with float32 XYZ values identical to the four stride-12 triplets at +44. Each
stride-20 record has eight remaining zero bytes; UV semantics are not established.

At +264, uint32 12 equals the remaining byte count. Reading the final twelve bytes
at +268 as six little-endian uint16 yields `(2,0,3,1,3,0)`. As a triangle list,
these form `(2,0,3)` and `(1,3,0)`. Both have valid indices, nonzero signed XY area
and the same winding; they share edge 0–3 and cover the near-rectangular point set.
Combined area matches the XY bounding rectangle within relative tolerance 1e-6.
This supports the triangle-list interpretation on this sample, not a universal
mesh format or verified render topology for other resources.

## Material investigation

The ground object's other key, `0x30000CB3`, identifies a 152-byte record. Its
first three uint32 values are 4, 0, 35; the remaining 140 bytes hold 35 keys:
`0x30000C93` through `0x30000CB2`, then `0x30000D43`, `0x3000FCCD`, `0x3000FCCE`.
The role of this collection and the active ground entry are not established.

As a bounded check, the first three linked records C93/C94/C95 were inspected.
Each is 48 bytes, starts with uint32 5 and 6 and contains another matching key at
payload +44: C5A (21880 bytes), D45 (5536 bytes), C5C (43744 bytes), respectively.
These sizes and links do not prove a material/texture format; those larger
payloads were not decoded. Selecting the first entry as the ground texture would
be unjustified.

## Outputs and checks

`src/preview_menu3d_ground.py` accepts only the known decoded source SHA-256,
checks the two coordinate arrays, count/stride, candidate indices, winding and
area, then creates a new output directory. It exports `ground.json`, an
untextured local-space `ground-candidate.obj` and `ground-preview.svg`.
No guessed normal, UV, material, world transform or camera is applied.
Five regression tests cover a valid planar fixture, out-of-range indices,
coordinate disagreement, a degenerate triangle and truncation; all passed.

Local report `reports/ground-preview-20261016` also includes a PNG plot, visually
inspected. The two fill colors distinguish triangles and are not game materials.
Generated game-derived geometry remains in reports, excluded from Git.

```powershell
python .\src\preview_menu3d_ground.py <decoded-menu3D-file> <new-report-directory>
python .\tests\test_ground_preview.py
```

Next: corroborate the mesh layout on a second simple object and determine the
per-object selection within the 35-key collection before attempting textures.
