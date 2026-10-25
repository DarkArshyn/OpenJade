# Horizontal projection sign correction

Date: 2026-10-25.

The mirror hypothesis is confirmed for the diagnostic rasterizers.
The existing local components were (dot(delta,B0), dot(delta,B1), dot(delta,B2)).
The rasterizers used screen-right +B0, screen-up +B2 and forward -B1.
The traced native conversion instead supplies camera-block axes -B0,-B2,-B1.
Its negative projection Y coefficient cancels the -B2 sign before viewport Y
inversion. Projection X is positive in both studied branches, leaving -B0
as the horizontal view axis. Thus X was reversed, while Y and depth need no
corresponding sign change in the current diagnostic convention.

Corrected `menu_colored_raster.py` and `preview_menu3d_landmarks.py` at the
world-to-view conversion, before projection and rasterization. No image flip,
UV inversion, scene-object movement or camera-position negation is applied.
This does not establish all runtime matrix-helper, hierarchy or projection
branch behavior. It corrects the mismatch with the already reconstructed
native matrix chain.

## Validation

New `test_menu_projection_signs.py` projects three landmarks under a translated,
rotated camera through the native view/projection matrices and compares their
pixel positions to actual triangle centroids from both rasterizers. It uses
vertical FOV 60 degrees, ratio 0.75 and the corresponding native axis branch.
The old colored rasterizer fails the two off-center landmarks by about 208
pixels horizontally, while vertical coordinates agree. Corrected colored and
legacy rasterizers pass all three landmarks. Four existing native-camera-math
tests also pass. This is mathematical/raster validation, not live game capture.

## Visual comparison

Two Camera02 renders were regenerated without yaw/pitch adjustment, preserving
the stored camera position, 42 objects, 14,960 triangles and 35 materials.
The angle 1.3 radians is still tested as vertical and horizontal alternatives.
The large foreground trunk now appears on the same side as in the original
capture. Landmark size, exact framing, lighting and fog still differ.
No claim is made that every remaining error is camera-related.

Local ignored evidence: `reports/camera-projection-sign-20261025/renders`,
including comparison.png and per-view scene.json. Older renders and camera
fits were generated under the previous sign convention and must not be used
as current visual validation. Their manual yaw/pitch fits should be revisited,
not copied into corrected renders.

Next: resolve the native projection branch/aspect ratio and Camera02 motion
state, comparing several landmarks at once. There is no evidence here requiring
negation of Camera02's stored world position or movement of scene geometry.

Sources: [native matrices](2026-10-22-native-camera-matrices.md) and
[Camera02 menu copy path](2026-10-24-camera02-menu-startup.md).
