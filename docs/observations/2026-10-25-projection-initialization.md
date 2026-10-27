# Projection initialization and the 59.38-degree hypothesis

Analysis date: 2026-10-25. Frozen PC GOG executable SHA256:
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
Native evidence was exported with Ghidra read-only, no reanalysis.

## Observed chain

- `00416850` creates the graphics context through `00425F30`, stores it in
  `0080C0C8` and `00AF4478`, installs the PC callbacks via `00425CF0`, then
  invokes `00426CB0`.
- `00425F30` zeroes the context and explicitly sets context `+AC = 0`,
  `+C8 = 2`, and `+B4 = 1.0`. These are constructor defaults.
- `00413CD0` initializes configuration dimensions `+90 = 800`, `+94 = 600`.
  `004264A0` reads these fields from `0080C0C4`, copies them to context
  `+A4/+A8`, and calls `004384C0(context+AC, context+CC, width, height)`.
  `004384C0` reads the selector; its writes target the camera block, not +AC.
- `00426C40` assigns the active-context global `009EC518` when attaching the
  world. Its own body has no write to +AC or +C8. `00426600` handles texture
  setup; the inspected body has no direct selector write. This is not a proof
  about every callee or possible alias.
- `006D6CD0` transfers the active camera angle to context `+D8` and calls the
  projection callback. `0059F140` supplies the menu angle float32 1.3, as
  established in the [menu startup study](2026-10-24-camera02-menu-startup.md).
- `00660690` uses height/width for context +C8 in 1..6. With selector
  **mask 0x4 clear**, P00=cot(a/2), P11=-cot(a/2)/(height/width).
  Therefore a is horizontal in this branch. Mask 0x4 means bit index 2;
  older prose saying 'bit 4' referred to its value, not a 0x10 mask.

For 800x600 and a=float32(1.3):

`horizontal = degrees(a) = approximately 74.48451 degrees`

`vertical = degrees(2*atan(tan(a/2)*600/800)) = approximately 59.38 degrees`

This strengthens the previous visual choice with an initialization path. It
still does not establish the settled menu's runtime context or Camera02 motion
state. No live debugger capture was performed, and no camera coordinates were
changed. The previous 59.38-degree rendering remains the relevant comparison.

## Search scope and limitations

`OpenJadeProjectionRefs.java` searches functions with direct references to
009EC518 for accesses with scalar displacement AC/C8. A broader local scan
looked for direct writes containing displacement AC in known functions.
Several candidates were unrelated geometry/configuration fields; 00409530 is
an untyped thiscall setter reached by 00402840/004029F0, not established as a
render-context writer. Neither search proves absence of indirect writes,
interior pointers, bulk copies, missing functions or aliasing. Do not promote
constructor defaults to a confirmed runtime state on this evidence alone.

## Reproducibility

`projection_angles` in `src/menu_native_camera_math.py` exposes both angle
conventions for explicit viewport, selector and ratio-mode inputs. Four new
synthetic tests cover horizontal/vertical edge geometry, the exact mask,
ratio selection boundaries and invalid viewport dimensions. Four existing
native-camera math tests also pass. No new source data or image tuning is used.
Ignored evidence: `reports/projection-initialization-20261025/`.

Next useful discriminant: Camera02's motion block 30000CF1 and its application
before the menu pose copy, or a live capture of the active view/projection.
The static stored pose may differ from the pose at the original screenshot.
