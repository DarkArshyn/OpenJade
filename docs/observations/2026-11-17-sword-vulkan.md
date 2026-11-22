# Sword reflection during Camera02 and Vulkan integration

Date: 2026-11-17

## Native evidence

Extends [resource and UV identification](2026-11-17-sword-reflection.md).
The existing GOG Camera02 capture contains 275 pairs of sword draws. In every
first, visible draw, the reflection constant rows exactly equal -0.5 times
object-to-view X/Y, with a 0.5 bias. The largest coefficient span across the
sample is 0.904055566: these coordinates are not a frozen material offset.
The following offscreen draw retains these constants while changing its position
matrix and must be excluded from this relationship.

Captured view reconstruction shows native X agreeing with renderer camera.right,
and native Y opposing renderer camera.up (initial dot products approximately
1.00000055 and -1.00000048). Therefore the independently implemented rule uses:

    U = 0.5 - 0.5 * dot(world_normal, camera.right)
    V = 0.5 + 0.5 * dot(world_normal, camera.up)

Normals retain their original magnitude. Their source attachment transformation,
evaluated skeleton and rigid actor placement precede projection. Position and UV
evaluation use the same frame time. This is normal-projected environment texture
mapping, not a new screen-space reflection or a reflection of scene geometry.

| Sword group | Captured main-target treatment |
| --- | --- |
| 61 triangles | Base 13006B64 plus reflection 2E011834; measured two-texture equation |
| 8 triangles | Same base texture object; texture times diffuse times two; no pixel shader or stage-1 texture |
| 24 triangles | Same base texture object; texture times diffuse times two; no pixel shader or stage-1 texture |

All three observed draws enable depth testing/writing and disable alpha blending.
The two nonreflective groups already used this treatment; no additional reflective
pass is attached to them. Source slot values 2 and 4 still do not directly index
the two-entry material pack. Their native slot-remapping mechanism remains
unresolved; matching the observed draw behavior does not resolve that mechanism.

Reflection tint is read from material `13006BBB`'s packed color and agrees with
native pixel constant (64,71,74)/255. Texture `2E011834` comes from the original
resource, whose first level exactly matched the native readback. Sampling is
linear/clamped at level zero. Its original 32x32 dimensions are preserved.

## Implementation

Optional `OJREFL01` sidecars bind one complete opaque actor draw, a reflection texture
layer and tint. Readers reject malformed extents, invalid texture layers, partial
draws, nonfinite tint and missing actor normals. Old packages without this sidecar
retain their previous material path. Scene assembly remaps draw/texture indices.

The renderer uploads 183 projected UV pairs per frame in a separate channel,
samples the additional texture and applies the measured RGB/alpha equation before
the existing fog treatment. UI shaders provide the matching interface.

## Validation

Commands (private capture and source paths must exist locally):

    python tests/integration_sword_reflection.py CAPTURE SOURCE_MANIFEST --camera CAMERA_CAPTURE
    cargo test --manifest-path engine/Cargo.toml --workspace
    cargo clippy --manifest-path engine/Cargo.toml --workspace --all-targets -- -D warnings

- 77 ordinary Rust tests pass; 15 local-data tests remain ignored by default.
- New tests cover normal magnitude/Y convention and malformed reflection bindings.
- Native validation covers 275 Camera02 poses, the two additional triangle groups,
  original reflection texture pixels and material tint.
- Three endpoint-camera poses at actor times 0, 2 and 3.983333 seconds produce
  identical repeated frames, with zero Vulkan validation errors.
- Reflection on/off changes respectively 158, 194 and 126 final pixels at 800x600,
  with maximum 8-bit channel differences 40, 68 and 37.
- Additional initial/intermediate Camera02 captures and native-menu loading pass
  Vulkan validation. This does not establish GOG final-pixel parity.

Four sequential 1,800-frame FIFO runs on Windows / Radeon RX 9070 XT, excluding
30 warm-up frames:

| Run | Reflection | Frame median / p95 ms | Simulation median / p95 ms | GPU median / p95 ms |
| --- | --- | --- | --- | --- |
| 1 | Off | 5.612 / 11.342 | 0.718 / 0.877 | 0.329 / 0.347 |
| 2 | On | 5.622 / 11.325 | 0.762 / 0.935 | 0.330 / 0.349 |
| 3 | On | 5.609 / 11.353 | 0.758 / 0.913 | 0.330 / 0.350 |
| 4 | Off | 5.618 / 11.515 | 0.966 / 1.387 | 0.326 / 0.346 |

Zero validation errors over these 7,200 frames. The last baseline is noisier;
these observations do not demonstrate statistical performance equivalence.
The later clock-sharing adjustment does not change fixed-time captures.

Private generated bundle: `reports/menu-prince-reflection-20261117/menu.ojscene`.
The UI bundle remains `reports/menu-fixtures-20261110/ui/menu.ojui`.

Follow-up: [native sword mipmaps verified and integrated](2026-11-22-sword-mips.md).

Later follow-up: [sword material-index selection resolved](2026-11-22-sword-material-selection.md).

## Remaining limits

Whole-image GOG parity, native material slot remapping and exact source base-texture
mip-chain equivalence remain unverified. The exporter still transports the base
level of actor diffuse textures; general scene filtering behavior is unchanged.
This integration does not complete the Prince's runtime controller or gameplay.
