# Camera02 sampled transition preview

Analysis date: 2026-10-26. Frozen executable/Menu3D hashes are those in the
[track study](2026-10-25-camera02-tracks.md). Original resources remain read-only.

## Interface reference

`0061B1C0` calls `0045E130(0B0041D2,0,&pair)` and stores the resulting pair
at +6C4/+6C8. `0045E130` returns exactly (key,index) when resource lookup succeeds.
`0059F140` adds 3 to the index and calls `00528E00`; the result at +6D0
is attached to action type 0032/value 999. `00528E00` wraps `00528BE0` and
registers a togglable page item. Thus the exact resource pair is **0B0041D2:3**.

The extracted `pop4mainmenu.mgm` has `NewGame` / `Start New Game`, and the
French `pop4pclocal.dat` conversion has `P_MainMenu/NewGame=Nouvelle partie`.
The latter is the fourth entry in that section. These agree with the expected
button, but ordinal coincidence does not establish a binary resource mapping.
The key is absent from the inspected Menu3D, global-camera, MenuBoot,
MenuCredits and newly decoded Menu FF0E0165 containers. The exact binary
key-to-visible-label association remains unresolved; do not mark it proven.
The targeted Menu extraction is recorded locally, decoded SHA256
`81cccc10b4a5971545673e1626ced8108ee0cc1b80c4cac44734de08952c33cc`.

## Rotation and sampling

Native `00648120` multiplies each signed quaternion component by the float
at 007AE4AC: **0.000030517578125 = 1/32768**. Components are x,y,z,w,
as verified against `0079B1F0`. `00648B60` calls shortest-path interpolation
`0079B0D0` / `0079AF80`: negate the second quaternion for negative dot product,
clamp dot to 1, use the stored 007B1E38 epsilon (~1e-7), normalize the spherical
interpolation result. The zero-angle branch returns the first quaternion.
Terminal keys retain their decoded components. This is not bit-exact x87 replay.

`sample_camera02_animation.py` combines this orientation with the captured
pose using [the verified relative composition](2026-10-25-camera02-activation-composition.md).
The preview assumes the captured pose equals stored Camera02. Vector samples
use piecewise linear interpolation. Seven poses cover 0..9 seconds, with
no manual yaw/pitch adjustment and the event-track FOV ~1.299991 radians.

At 9 seconds, comparison with stored Balcony camera 30000D63 yields:

- Position distance: 9.9685393e-6 scene units.
- Maximum absolute difference across the 3x3 basis: 3.7112613e-5.

This supports both transform order and quaternion convention independently of
the screenshot appearance. It does not prove live event scheduling.

## Preview

```powershell
python .\src\preview_camera02_transition.py <decoded.bin> <new-output-folder>
python .\tests\test_camera02_animation.py
```

Open the generated `index.html` locally. Its slider selects seven prerendered
poses; Play samples advances every 1.5 seconds. This is a sampled visualizer,
not continuous engine playback. `contact-sheet.png` compares all poses;
`poses.json` preserves the numerical matrices. Local validated output:
`reports/camera02-transition-20261026/preview/`.

Lighting remains diagnostic; fog/fixture phases are held at zero, the Prince
is absent, and scene completeness is unchanged. No rendered frames or game
assets are intended for source control. Five synthetic tests cover row-vector
rotation, shortest-path sign, half-angle interpolation, segment boundaries,
terminal keys and invalid sample times.
