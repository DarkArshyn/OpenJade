# Balcony camera candidate renders

Date: 2026-10-24. Offline comparison against the user's original
800x600 main-menu screenshot. No runtime camera state was captured.

## Method

Reused assemble_menu_scene.py with its existing mesh, texture, vertex-color
and three-panel fog diagnostics. A local driver overrides only the raster
camera position and basis with the two poses from the orientation report.
Existing preview defaults and production source files are unchanged. Both
candidates were rendered at vertical FOV 50 and 75 degrees, fog time zero,
with no yaw/pitch fitting. These FOV values are explicit hypotheses.

Each run accepted 42 objects, 14,960 triangles and 35 materials. The driver
replaces the assembler's Camera02 metadata with the actual candidate pose.
Reports preserve exclusions and rendering limitations. Original screenshots,
textures, OBJ exports and rendered images remain in local ignored reports.

## Visual result

At 50 degrees both candidates frame the balcony and doorway much more closely
than the stationary main-menu reference. At 75 degrees they reveal more of
the surrounding building, but the doorway remains much lower in the frame;
the foreground tree arrangement and occlusions also differ from the reference.
Neither tested combination reproduces the stationary main-menu framing.
Widening FOV alone in this tested range does not resolve the mismatch.

This is a visual comparison, not an image-registration score. It does not
exclude other FOVs, runtime transforms, hierarchy effects or transition states.
The close balcony views are consistent with the user's description of the
post-New-Game sequence, but that role has not been demonstrated at runtime.
Do not label either candidate the confirmed main-menu camera.

Lighting and fog still differ substantially from the reference. The geometry
comparison should precede attempts to tune those effects to compensate for
an incorrect camera. Missing scene elements and material limitations remain
those recorded by the existing assembler.

## Artifacts and validation

Local directory: reports/balcony-camera-comparison-20261024.

- fov50/comparison.png and fov75/comparison.png: original reference at left,
  CAM_Balcony at center, CAMALT_Balcony at right.
- Each candidate directory: fixed-camera.png, diagnostic baselines, scene.json,
  scene.obj, scene.mtl and textures.
- Driver scripts and the input pose JSON provide the reproduction inputs.

Both sheets were visually inspected. All four renders completed; scene counts
matched. This is a render experiment, not validation of original engine output.
The scripts currently assume the recorded local paths and should be adjusted
before reuse outside this workstation.

## Next priority

Return to the stationary-menu activation path and Camera02 or another proven
startup camera source. Capture or establish the active camera object, transform
and FOV before changing scene placement. Keep the balcony candidates for later
New Game transition checks. A diagnostic 3D scene is already renderable; the
faithful stationary background and its integration behind the menu remain open.
Audio is deferred and is not required for these framing checks.
