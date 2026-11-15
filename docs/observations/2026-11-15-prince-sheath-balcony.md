# Prince sheath controller, animated lighting and balcony integration

Date: 2026-11-15. Validation platform: Windows, AMD Radeon RX 9070 XT.

This extends the [source-skeleton diagnostic](2026-11-14-prince-skeletal-animation.md).
The prepared prototype now renders eleven components / 2,933 triangles, including
the dagger, both in isolation and in the menu environment. It is not a playable
character or a claim of full native animation/rendering parity.

## Evidence and provenance

Original resources remain read-only. The three character bundles retain the hashes
listed in the [resource assembly observation](2026-11-13-prince-resource-preview.md).  
Menu bundle `FF000CB9` SHA-256 is `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.  
The GOG research executable SHA-256 is `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.


The private `prince-sheath-state` probe records input/output state around native
`006E1020`, reached through type-22 modifier update `006E1B30`. The source modifier
belongs to bone `130035EE`; source snap `130046A1` and the previously measured local
half-turn place the dagger relative to that bone. The proxy was restored after the
capture (SHA-256 `e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`).

## Source-backed sheath dynamics

The selected 415-byte GAO contains modifier type 22 at offset 271, payload version
1 at 279, flags 2 at 283, two coefficients of 0.5 at 287/291, acceleration
`(0,0,-30)` at 295, and two constraint records after the count at 307. The final
wind multiplier is 2 at 407. No additional wind contribution is needed to reproduce
the sampled updates; arbitrary wind activation is not established.

The local rest translation gives length `0.297787696`. Each constraint holds four
vectors; the file order is hard A, hard B, soft A, soft B. The runtime comparison
uses hard A, hard B, soft B, soft A. These records are not animation-key tracks.

The independent calculation applies parent-relative inertial and acceleration
terms, constrains velocity against angular boundaries, advances the endpoint and
restores its length. Orientation is derived from that endpoint and the reference
basis. `src/prince_sheath.py` specifies the measured case; the Rust evaluator uses
the same source parameters, with its own data representation.

Across 125 captured updates:

| Comparison | Maximum absolute error |
| --- | --- |
| Local endpoint | 1.3381e-6 |
| Local velocity | 9.7802e-5 |
| Output matrix, using measured endpoint | 1.2257e-5 |

These are **one-step comparisons on captured inputs**, not an autonomous native
trajectory comparison. The native startup includes a large relocation from the
template position. The viewer instead starts from rest at its displayed placement,
uses bounded 125 Hz diagnostic steps, and resets with the four-second diagnostic
clip. This deliberate startup/loop policy is not recovered original behavior.

## Animated lighting

The viewer now skins original normals and recalculates vertex RGB each frame using
the independently checked [actor lighting equation](2026-11-13-ambient-cache-shaders.md).
Ambient, two directional and two point-light parameter sets are retained from the
native diagnostic capture and transformed into actor coordinates. Their provenance
remains explicit: this is **not a general source-loaded scene-light system**.

The 165 expanded vertices of the dagger's texture-factor pass retain their constant
material color. They do not incorrectly receive the computed diffuse term. The
sword reflection path and full native material fidelity remain unresolved.

Seven Python/Rust poses agree within 7.75e-7 for positions and 1.014e-6 for RGB.
The formula comparison establishes evaluator consistency, not measured GPU pixel
parity. Lighting parameters do not yet respond to camera movement or game state.

## Balcony placement and scene preservation

The original `Menu3D_TEC_Checkpoint.gao` (`0F0053D9`) supplies the placement:
translation `(-103.2630768,-4.7990041,1.3564005)` and its stored horizontal rotation.
Thirteen native samples match its XY and orientation within 1e-6. Native Z is about
0.014345 lower. The source height is retained; no guessed ground adjustment is made.
The cause of that vertical difference has not been established.

`assemble_prince_balcony.py` appends the actor, offsets only its vertex/texture
ranges, and preserves existing scenery vertices, draws, texture pixels, UV rates,
palm records and effect sidecars. Actor passes use the existing native-range vertex
fog path. The `.placement` sidecar transforms the animated positions at upload;
lighting remains in actor coordinates. This does not implement collision or actor
activation scripts.

## Validation and reproduction

Private outputs: `reports/prince-sheath-animation-20261114` (isolated diagnostic)
and `reports/menu-prince-20261115` (assembled menu). Reports/assets are not committed.

Fixed-time Vulkan captures of the isolated Prince, main-menu viewpoint and decoded
Camera02 endpoint have identical repeated frames and no validation errors. The
native-menu smoke test completes 80 frames with resizing and zero validation errors.
The endpoint capture demonstrates visibility on the balcony, not original-game
pixel parity. The existing postprocessing and lighting limitations still apply.

From the repository root, with previously decoded character bundles in `$sources`:

```powershell
$env:PYTHONPATH = 'src'
python src/export_prince_animation.py $nativeDrawCapture $newActorOutput --sources $sources
python tests/integration_prince_sheath.py $nativeSheathUpdates $validationOutput --sources $sources
python tests/integration_prince_animation.py $nativePaletteCapture $newActorOutput $poseReport --sources $sources
python tests/integration_prince_lighting.py $newActorOutput --sources $sources
python src/assemble_prince_balcony.py $preparedMenu $preparedActor $decodedMenuBundle $newMenuOutput
```

The standalone shader/mesh capture, native palette capture and sheath update file
are different inputs. See the scripts' argument help and the earlier observations.
From `engine/`, the prepared local assembled preview is:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-prince-20261115/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
$env:OPENJADE_ACTOR_FIXTURE = (Resolve-Path ../reports/prince-sheath-animation-20261114/prince.actor).Path
cargo test -p jade-assets actor::tests::source_pose_parity -- --ignored --nocapture
cargo test -p jade-assets actor::tests::source_lighting_parity -- --ignored --nocapture
```

Other incomplete work: facial controllers, remaining secondary animation, native
action selection and timing, general runtime lighting, sword reflection, ground
placement, interactions and gameplay. Linux/macOS were not revalidated for this update.
