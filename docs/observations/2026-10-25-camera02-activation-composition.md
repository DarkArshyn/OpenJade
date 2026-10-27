# Camera02 activation and relative pose

Analysis date: 2026-10-25. Sources: frozen POP.EXE and Menu3D,
with the SHA256 values recorded in [the track decoding study](2026-10-25-camera02-tracks.md).
This is static executable analysis and a numerical resource check, not a live trace.

## When the controller starts

Camera02 behavior 3200026B (`005AE110`) accepts activation events including
6E, 6F and 68. `0054AF90` checks its state and selects behavior 32000274
(`005C1D70`). Its startup branch requires field +2D8 to be zero and the
`0054BAE0` gate to succeed (+150 zero, +32C not 1, +0 nonzero).
It copies the object pose into the global camera and calls `0047C800`,
which invokes `006456B0(controller, 1)`. Inactive tracks receive elapsed time
zero, key index zero and active bit 1. Already active tracks are not reset.
The behavior then marks +2D8 as 1. Loading the CF1 alone is not this start call.

A menu route is visible in `0061A600`: message type 0x32 with value 999
sends event 6E to the object referenced at +6CC. The decoded reference is
30000D68, the Balcony CAM_Insert object. Its instance 30000D66 references
Camera02 at +48 and activation event 6E at +94. `005734D0` accepts that event
(subject to sender/state checks), and `005E2270` can call `0054AF90` on the
referenced camera after its insert/delay guards.

This establishes a conditional menu-event-to-controller route. The exact UI
action producing message 999, elapsed delay and frame ordering have not been
confirmed in a running game. Do not equate an event identifier with a button
solely from its number. The stored Camera02 +130 value is 1, so the separate
+130 == 3 self-activation branch does not establish automatic startup here.

## How values combine

`00646560` / `00645EA0` prepare relative tracks; event flag bit 0x4 on the
rotation track (0084) causes a current-pose capture via `00645E00` when needed.
The captured matrix is the activation-time object pose, not necessarily its
unchanged disk pose. Target FFFF resolves to the owning object in this path.

For this non-hierarchical Camera02 case, using row vectors:

```
P(t) = v(t) * R_capture + P_capture
R(t) = R_delta(t) * R_capture
```

`00648DB0` linearly interpolates the vector keys, finds the relative rotation
track for the same target, then calls `0079A990` to transform and translate
the vector through the captured matrix. For orientation, `00648B60` evaluates
the rotation; `0079A750` multiplies delta basis by captured basis, and
`00438110` copies the basis without replacing translation. Translation is
therefore not rotated by the newly evaluated delta orientation.

Zero displacement and identity delta preserve the captured pose. These are
relative values, not absolute world coordinates or per-frame increments.
The existing decoder gives both first tracks a nine-second key timeline.
The third track is still uninterpreted and may affect controller behavior.

## Independent endpoint check

Using the stored Camera02 pose as the captured pose and the final vector:

| Quantity | X | Y | Z |
| --- | --- | --- | --- |
| Camera02 start | -83.58901978 | 1.38866043 | -2.66194749 |
| Last local vector | 1.25201654 | -9.92837906 | 5.81041002 |
| Composed endpoint | -92.80203642 | -0.96490821 | 3.93215297 |
| Stored Balcony camera 30000D63 | -92.80204010 | -0.96491599 | 3.93215799 |

Euclidean position residual: **9.9685393e-6 scene units**. This independently
supports the relative-axis composition and strongly supports a menu-to-balcony
transition interpretation. It does not validate endpoint orientation, runtime
selection, or the complete New Game sequence. Do not advance the track to
compensate for a mismatch in the stationary menu framing.

## Implementation and validation

`src/compose_camera02_pose.py` implements only the above matrix composition.
It accepts an already decoded rotation matrix; it is not an animation player.
Four synthetic tests cover identity, rotated translation axes, noncommuting
rotation order, translation independence and invalid inputs:

```powershell
python .\tests\test_camera02_composition.py
python .\tests\test_camera02_tracks.py
```

Ignored local evidence: `reports/camera02-composition-20261025/`, including
the endpoint JSON and native decompilations. Original game files and the
renderer default camera are unchanged. Next: identify the sender of message
999, decode the remaining track and validate the orientation through time.
