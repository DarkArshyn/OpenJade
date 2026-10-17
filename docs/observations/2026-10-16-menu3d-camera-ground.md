# Menu3D cameras and ground — 2026-10-16

## Scope and provenance

Read-only inspection of six GAO records and their selected direct/two-hop key
matches in the previously decoded FF000CB9 resource. No additional archive entry
was extracted.

SHA-256: `96244FE330C11ACDF2A87A7C8A410225B224F5F1B9F264834425848CBF4D00EB`.
Record boundaries come from `probe_menu3d.py`; all offsets below are decimal.
Payload offsets exclude the twelve-byte record envelope.

## Common fields and transform hypothesis

All six payloads start with `.gao`, uint32 values 10 and 8, then a varying word.
At payload offset 16 a uint32 N identifies a variable name slot starting at 20.
The name is null-terminated within that slot; slot length must not be inferred
from visible text length alone. Following ten additional bytes, offset `30+N`
contains three groups of four float32 values followed by three more floats.

The first three values of each group form orthonormal axes in all six examples:
each pairwise dot product differs from its identity-matrix expectation by less
than 0.00001. Each group's fourth value is zero. The final three floats are
plausible positions. This supports a transform interpretation but does not yet
establish local/global coordinates, units, handedness or row/column convention.

The next four bytes are **not** safely a homogeneous matrix element: Camera02
and ground contain `F6 2E E1 77`, whereas the balcony objects contain float32 1.
They remain an opaque field; do not normalize them or treat the block as a
validated standard 4x4 matrix.

| Object | Key | Record start | Candidate position |
| --- | --- | --- | --- |
| Camera02 | 0x30000CF0 | 321338 | (-83.5890, 1.3887, -2.6619) |
| CAM_Balcony | 0x30000D63 | 334777 | (-92.8020, -0.9649, 3.9322) |
| CAM_BalconyTarget | 0x30000D65 | 334970 | (-107.1956, -7.4955, 5.2016) |
| CAMALT_Balcony | 0x3C00144D | 353317 | (-97.7174, -6.9166, 3.1833) |
| CAMALT_BalconyTarget | 0x3C00144E | 353513 | (-107.4541, -4.8054, 4.0272) |
| Menu3D_ground | 0x30000CCD | 68201 | (-100.6810, -2.6483, -9.5561) |

## Camera key relationships

Exact four-byte key matches, scanned without requiring four-byte alignment:

- Camera02 payload +159 matches record `0x30000CEF` at 1248089 (24 bytes).
  Interpreting its bytes as four uint32 and two float32 yields
  `(6, 0, 1, 0, 1000.0, approximately 1.216)`. Projection type, far plane and
  field of view are possible interpretations, **not established fields**.
- CAM_Balcony +177 matches `0x30000D62`, an eight-byte record at 1259609.
  Its second uint32 matches `0x30000D61` (324-byte payload). That payload contains
  CAMALT_Balcony's key at +248, BalconyTarget's key at +260 and Balcony's key at
  +276. This supports a relationship among these objects without proving which
  is the active camera or the runtime transition behavior.
- CAMALT_Balcony +180 matches `0x3C00144C`, whose second uint32 matches
  `0x3C00144B` (312 bytes). The latter contains AlternateTarget at +248 and
  AlternateCamera at +264.

## Simple object: ground

The ground GAO has identity candidate orientation. At payload +164 it contains
key `0x30000C80`, whose record begins at 512717 and has a 280-byte payload.
That payload contains four float32 triplets at +44 with stride 12:

| Point | X | Y | Z |
| --- | --- | --- | --- |
| 0 | -80.183655 | -79.845383 | -0.258669 |
| 1 | 80.513756 | -79.845390 | -0.258669 |
| 2 | -80.183655 | 80.027916 | -0.258668 |
| 3 | 80.513756 | 80.027916 | -0.258668 |

The same four triplets occur **bit-for-bit identically** at +184 with stride 20.
They describe an almost planar rectangle. Their extrema agree approximately
with six floats at ground-GAO +140 (differences of roughly 0.000008 or less).
This corroborates a small geometry/bounds interpretation. Triangle topology,
normals, UVs and material binding are not yet decoded. Integer words near the end
must not be labelled triangle indices without further structural evidence.

Other ground matches are `0x30000CB3` at +168, Ambient light GAO at +210 and
Fog_BG light GAO at +214. The role of `0x30000CB3` remains unknown.

## Evidence and next step

Local report `reports/menu3d-camera-ground/analysis.json` preserves exact values,
absolute offsets, dot products and candidate key matches. Payload hex dumps for
the six objects and four selected linked records accompany it. Checks verified
orthonormality in all six samples and equality of the two ground coordinate arrays.
These are targeted research assertions, not a general-purpose GAO decoder.

Next: decode the ground record's topology and material relationship, then create
a minimal geometry preview. Camera activation and projection still require
independent evidence; the current data is insufficient to reproduce the view.
