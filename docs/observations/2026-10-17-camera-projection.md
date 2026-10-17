# Camera projection hypotheses — 2026-10-17

## Source evidence

The focused decoded resource has SHA-256
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
Camera02 GAO `30000CF0` contains the key `30000CEF` at payload offset 159.
Its target record starts at file offset 1248089 and has a 24-byte payload:
`0600000000000000010000000000000000007a4491a49b3f`.
Interpreted as four uint32 and two float32 values this is
`6, 0, 1, 0, 1000.0, 1.2159596681594849`.
These values are observed; their semantics remain unconfirmed.
Only one 24-byte record beginning with uint32 6 was found in this resource.

The Balcony and Alternate GAOs reference eight-byte blocks `30000D62` and
`3C00144C`; those contain keys `30000D61` and `3C00144B`, respectively.
The latter blocks contain candidate references to the named objects and their
associated targets. They are controller candidates, not decoded behavior.
Names alone do not establish that all three GAOs represent complete cameras.
The JSON retains byte offsets for candidate key matches; a match does not by
itself establish a typed reference.

## Projection experiment

`src/preview_menu3d_camera.py` reads the frozen input, reconstructs the four
landmarks and reuses local texture previews from the previous experiment.
It renders four explicit hypotheses at 800x600 with unchanged texture V:

- Previous baseline: 60-degree vertical angle.
- Stored float as vertical radians: 69.669 degrees.
- Stored float as horizontal radians: 55.123-degree vertical angle at 4:3.
- Vertical-radian interpretation with transposed camera basis.

Conversion uses `v = 2 atan(tan(h / 2) / aspect)`.
The first three keep the balcony visible but do not establish agreement with
 the user's original main-menu screenshot. The transposed-basis view shows only
 a narrow piece of distant geometry. This disfavors that isolated change under
 the other current assumptions; it does not prove the full coordinate system.
No camera pose was fitted to the screenshot. Active-camera selection, controller
behavior, transform hierarchy and the meaning of the stored float remain unknown.
The renderer still omits lighting and fog, and uses diagnostic material settings.

## Artifacts and checks

Local output: `reports/menu3d-camera-20261017/` (excluded from Git).
`projection-comparison.png` places baseline and vertical radians on the top row,
then horizontal radians and transposed basis on the bottom row.
`camera-projection.json` records the exact bytes, offsets and test parameters.

```powershell
python .\src\preview_menu3d_camera.py <decoded.bin> <landmark-texture-directory> <new-output-directory>
python .\tests\test_camera_projection.py
```

Three tests pass: known vertical-angle conversion, horizontal/vertical
conversion and invalid parameter rejection. Source access is read-only.
This is a sample-specific investigation, not a general camera parser.
Next: determine the role and evaluation of the controller candidates before
choosing a camera pose or claiming screenshot fidelity.
