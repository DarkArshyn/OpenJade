# Camera02 CF1: native track decoding

Analysis date: 2026-10-25. Frozen executable SHA256:
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
Menu3D SHA256: `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.

## Resource and loader connection

Camera02 `30000CF0` references `30000CF1` at payload offset 227.
GAO loader `0067DF50` registers the linked resource with callback `0079D690`
and stores its controller at `[object+18]+20`. `0079D690` reads a uint16
track count and container flags, then 20-byte runtime track descriptors.
It calls `0079D210` for the keys and `006483E0` for transform payloads.
The CF1 header is count 3, flags 2. This establishes a controller-track
container, not an arbitrary array of floats.

## First two tracks

| Property | Rotation | Vector |
| --- | --- | --- |
| Payload span | [4,62) | [62,496) |
| Stored flags | BC04 | BA04 |
| Target word | FFFF | FFFF |
| Expanded payload allocation | 48 bytes | 512 bytes |
| Key count | 4 | 32 |
| Duration encoding | uint16 | uint8 |
| First duration offset | 16 | 74 |
| First value offset | 24 | 81 |
| Shared event flags | 0084 | 0080 |
| Initial expanded size / payload flags | 12 / 1010 | 16 / 0001 |
| Total duration ticks | 540 | 540 |
| Total duration | 9 seconds | 9 seconds |

The reader's compression flags omit repeated event, size and payload-type
fields after the first key. Rotation keys contain four signed int16 values;
vector keys contain three floats. `00648B60` uses rotation payloads and calls
quaternion interpolation `0079B0D0` followed by matrix conversion `0079B1F0`.
Exact quaternion conventions/composition are not implemented in this change.

`00645800`, `00645EA0` and `00648B60` divide key durations by constant 007A9018.
The frozen executable stores bytes `00 00 70 42` there: float32 **60.0**.
This establishes time units, not a claim that rendering runs at 60 FPS.
Rotation durations are 364, 130, 46, 0 ticks. The last zero-duration key is
preserved. The remaining [496,624) third track is retained byte-for-byte;
its events are not interpreted yet.

This corrects the old ordinal-only study: 48 and 512 are allocation sizes,
not durations. Its vector-value offsets were correct, but the first alleged
leading byte at 80 belongs to payload flags. The actual first duration is at
74; subsequent duration/value boundaries follow the native compressed reader.

## Start and transfer path

Camera02 behavior 3200026B maps to `005AE110`, which reacts to events including
6E/6F/68 through `0054AF90`; the latter conditionally selects 32000274 in slot 2.
That behavior maps to `005C1D70`. In its startup branch it copies the object's
position/direction/up into the global camera, then calls `0047C800`.
`0047C800` passes `[object+18]+20` to `006456B0(...,1)`: inactive tracks get
elapsed time zero, index zero, and active bit set. Subsequent controller reads
use the same object field. These are conditional static paths, not captured
menu startup timing. The separate Menu_Start_Demo pose-copy path is documented
in [the startup study](2026-10-24-camera02-menu-startup.md).

**Do not advance CF1 arbitrarily to fix the still menu.** It remains unknown
whether the screenshot is before activation or at another controller state.
The nine-second duration alone does not identify this as the New Game zoom.

## Tool and validation

`src/decode_camera02_tracks.py` implements only these verified layouts, preserves
all offsets and the raw third track, rejects unknown headers and nonfinite
vectors, and checks the Camera02 resource link. It deliberately does not output
a guessed world-space animated pose.

```powershell
python .\src\decode_camera02_tracks.py <decoded.bin> <new-output-directory>
python .\tests\test_camera02_tracks.py
```

Four synthetic tests cover offsets, compressed duration sizes, signed values,
truncation/unknown headers, nonfinite samples and preservation of the third
track. The frozen real file validates both extents and returns two 9-second
tracks. Ignored outputs and native evidence:
`reports/camera02-track-decoding-20261025/`.

Next: decode the third track's events and trace the relative/world matrix
composition in `00648DB0` and `00648B60`, then establish which event activates
Camera02. No renderer pose, original game file or default FOV was changed.
