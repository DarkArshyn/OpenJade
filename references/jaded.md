# External reference: hogsy/jaded

Reviewed: 2026-10-20. Maintainer: Mark "hogsy" Sowden and contributors.
Repository: [hogsy/jaded](https://github.com/hogsy/jaded).
Pinned revision, resolved through the GitHub API from `develop`:
`8d55704c80adfcec4f3bcaeb2445dc9f68ef960e`.

The project's [README](https://github.com/hogsy/jaded/blob/8d55704c80adfcec4f3bcaeb2445dc9f68ef960e/readme.md)
describes a community-modified Ubisoft engine based on a copy from approximately
late May / early June 2006. This is a later reference, not proof of compatibility
with the TSoT executable. The README itself reports a material-flag
compatibility issue with the original Rayman 4 prototype data.

## Provenance and use

The inspected repository tree has licenses for particular dependencies and
runtime mappings, but no root LICENSE or COPYING file was found. This review
does not establish permission to reuse the Ubisoft engine code. Public
availability is not treated as permission. OpenJade imports no Jaded code,
headers, binaries or assets in this comparison.

Jaded names provide external hypotheses. Findings must remain separately
attributed and checked against the frozen TSoT executable and extracted data.
This comparison does not claim a clean-room process: the external source was
consulted. OpenJade's implementation remains independently written.

## First comparison: bounding volumes

Primary sources at the pinned revision:

- [OBJstruct.h, lines 63–92](https://github.com/hogsy/jaded/blob/8d55704c80adfcec4f3bcaeb2445dc9f68ef960e/src/libraries/ENGine/Sources/OBJects/OBJstruct.h#L63-L92)
- [OBJconst.h, OBBox flag](https://github.com/hogsy/jaded/blob/8d55704c80adfcec4f3bcaeb2445dc9f68ef960e/src/libraries/ENGine/Sources/OBJects/OBJconst.h#L37)
- [OBJBoundingVolume.h, accessors](https://github.com/hogsy/jaded/blob/8d55704c80adfcec4f3bcaeb2445dc9f68ef960e/src/libraries/ENGine/Sources/OBJects/OBJBoundingVolume.h#L39-L114)
- [OBJload.c, bounding-volume loading](https://github.com/hogsy/jaded/blob/8d55704c80adfcec4f3bcaeb2445dc9f68ef960e/src/libraries/ENGine/Sources/OBJects/OBJload.c#L348-L374)
- [OBJBoundingvolume.c, sphere predicate](https://github.com/hogsy/jaded/blob/8d55704c80adfcec4f3bcaeb2445dc9f68ef960e/src/libraries/ENGine/Sources/OBJects/OBJBoundingvolume.c#L43-L61)

| Topic | Jaded evidence | Independent TSoT evidence |
| --- | --- | --- |
| Initial limits | `st_GMinIn` and `st_GMaxIn`, exposed by GMinInit/GMaxInit accessors | Loader 0067df50 fills +0x18/+0x24; operations 2bc3/2bc5 read these offsets |
| Current values | `st_GMin`, `st_GMax` precede the initial limits | Loader copies the initial triplets to +0/+0x0c |
| Extended volume | OBBox flag 0x80000; adds `st_LMin`/`st_LMax` | Constructor 0067cf60 selects 0x30/0x48-byte allocation with the same bit |
| Editor layout | An extra leading pointer exists with ACTIVE_EDITORS | Observed TSoT allocations and accesses match the four/six-triplet layout without that pointer |
| Sphere distinction | Predicate tests the integer bits of GMax.z for -1 | Inspected TSoT getters accept both 0xFFFFFFFE and 0xFFFFFFFF through a mask |

The first four rows support a structural correspondence. The last row is a
concrete difference between the inspected predicates, not a claim about every
Jaded or TSoT caller. Jaded names do not establish TSoT's runtime coordinate
space: even the letters "G" and "L" must not replace a verified transform chain.

See the [TSoT serialized-bounds observation](../docs/observations/2026-10-20-balcony-geometry.md)
for native evidence locations, offsets, source hash validation and the two
balcony objects. Their flags are 0xA020, with 0x80000 clear. Neither upper-triplet
Z value matches the special sentinel when loaded. The comparison strengthens
the interpretation of the stored pairs as initial box limits.

No runtime change follows from this comparison. Field 276 activation, later
bound updates, callback timing and the active camera remain unresolved.
