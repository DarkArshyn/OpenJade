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

Isolated legacy exports use captured parameters. New menu assembly derives ambient
and three named light terms from original scene resources. For placed actors, the
runtime recalculates the generated direction from the active camera; its RGB remains
the verified package value. Isolated actors retain the captured direction. Original resource normals are animated. This is not a
source-loaded runtime light graph.

## Lighting origins: OJAORG01 (`.actororigins`)

Optional eight-byte magic, u32 actor vertex count, then one u32 for each expanded
actor vertex in sidecar order. `0xFFFFFFFF` selects the actor placement origin;
other values select a validated skeleton bone index. The selected evaluated bone
translation is transformed by actor placement before generated-light evaluation.
These indices describe lighting ownership, not skinning weights. Missing sidecars
retain shared-root behavior; isolated actors without placement remain unchanged.
Counts, exact extent and bone bounds are validated before committing the mapping.

## Placement: OJAPL001 (`.placement`)

Exactly 76 bytes: eight-byte magic, u32 first scene vertex, 16 f32 values for a
row-vector affine rigid matrix. The actor's local index range must fit within the
scene. The viewer evaluates its skeleton and lighting locally, transforms positions
through this matrix, and updates only that vertex range. Without this sidecar,
legacy actor packages continue to require complete scene vertex coverage.

The current balcony export retains checkpoint XY/orientation and derives initial Z
from the original collision geometry. This result is encoded in the existing matrix;
the sidecar does not contain a collision mesh or implement continuous grounding.
See [integration validation](../observations/2026-11-15-prince-grounded-integration.md).

## Sword reflection: OJREFL01 (`.reflection`)

Exactly 32 bytes: eight-byte magic, three u32 values (first scene vertex, vertex
count, reflection texture layer), then three f32 tint components in [0,1].
The range must match a complete opaque draw backed by animated actor normals.
The layer must exist. Missing sidecars disable this optional material.

UVs use unnormalized animated normals after rigid placement, with U = 0.5 minus
half the camera-right dot product and V = 0.5 plus half the camera-up dot product.
The texture is sampled linearly with clamp addressing and LOD zero; the existing
base texture path is unchanged. Assembly offsets vertex and texture bindings.
See [native evidence and validation](../observations/2026-11-17-sword-vulkan.md).

## Sword base mipmaps: OJSWMP01 (`.swordmips`)

Exactly 43,664 bytes: eight-byte magic, u32 texture layer, u32 level count (5),
then packed RGBA8 levels 128x64, 64x32, 32x16, 16x8 and 8x4. The scene texture
must be 128x64 and its base pixels must match. This optional sidecar preserves the
measured native chain; it is not a general texture format. Assembly adjusts the
layer index. See [readback validation](../observations/2026-11-22-sword-mips.md).
