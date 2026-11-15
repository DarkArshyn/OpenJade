# Actor diagnostic sidecars

These are OpenJade interchange formats, not original Jade resource layouts.
All numbers are little-endian; float values must be finite. Keep sidecars beside
the associated `.ojscene`, with the same filename stem.

## Sheath: OJSHT001 (`.sheath`)

Exactly 144 bytes: eight-byte magic, u32 body bone index, then 33 f32 values:
length, inertia coefficient, response coefficient, acceleration XYZ, initial local
endpoint XYZ, and two constraints of four XYZ vectors. Constraint order is hard A,
hard B, soft B, soft A. The selected diagnostic does not serialize external wind.
The bone requires a parent; the body clip period is bounded to ten seconds. The
reader rejects invalid lengths, non-unit constraint vectors and degenerate soft
boundary denominators. Runtime initialization and fixed stepping are diagnostic
policies; see the [validation scope](../observations/2026-11-15-prince-sheath-balcony.md).

## Lighting: OJALIT01 (`.actorlight`)

Eight-byte magic, u32 actor vertex count, then 31 f32 parameters:
ambient RGB; two directional lights (direction XYZ, RGB); two point lights
(position XYZ, RGB, outer range, inverse range width). All are in actor coordinates.
Each actor vertex then has a u32 mode: zero retains its existing material color;
one is followed by one XYZ normal per influence in the `.actor` file, in the same
order and inverse-bind coordinate system. Other modes and trailing data are rejected.
The maximum file size is 8 MiB. Counts must match the actor exactly.

Parameters currently come from explicitly recorded native draw constants; original
resource normals are animated. This is not a source-loaded runtime light graph.

## Placement: OJAPL001 (`.placement`)

Exactly 76 bytes: eight-byte magic, u32 first scene vertex, 16 f32 values for a
row-vector affine rigid matrix. The actor's local index range must fit within the
scene. The viewer evaluates its skeleton and lighting locally, transforms positions
through this matrix, and updates only that vertex range. Without this sidecar,
legacy actor packages continue to require complete scene vertex coverage.

The original checkpoint supplies the current balcony placement; observed native
height differs slightly and no collision correction is encoded here.
