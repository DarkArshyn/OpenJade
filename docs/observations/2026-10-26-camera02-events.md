# Camera02 event track and message 999

Analysis date: 2026-10-26. Sources are the same executable and
Menu3D hashes as [the preceding study](2026-10-25-camera02-tracks.md).
Native evidence is local under `reports/camera02-events-20261026/`.

## Third track: instructions rather than another transform curve

The stripped-PC layout at payload 496 contains flags 0014, target FFFF,
allocation 104 bytes, object key zero and two keys. The optional 16-byte
name is absent in this resource variant: `0079D690` / `004245B0` condition
its consumption on the resource-loading mode. This bounded decoder does not
claim support for the named/unstripped variant.

| Key offset | Duration ticks | Start time | Event flags | Instruction count |
| --- | --- | --- | --- | --- |
| 512 | 540 | 0 seconds | 0041 | 6 |
| 568 | 0 | 9 seconds | 0041 | 6 |

`0079D210` selects `00647640` for event class 0040. That loader reads a
32-bit count and eight-byte nodes via `00424AB0`. Each payload occupies
52 bytes (4 + 6*8), accounting for the full 104-byte allocation.
`00645EA0` dispatches the event to `00647750`, which establishes the object
context and calls the interpreter `00462ED0`. Flag 0001 gates repeated
evaluation using the controller's processed state; no frame-perfect live
execution was observed.

Both keys contain exactly the same sequence:

| First node offset | Operand | Tag | Interpretation |
| --- | --- | --- | --- |
| 520 | 0 | 01000028 | Object-context operand; numeric value retained |
| 528 | 0 | 02000806 | Context selection operation |
| 536 | 0 | 01000021 | Integer camera entry index 0 |
| 544 | 3FA6661B | 01000022 | Float32 approximately 1.299991 radian |
| 552 | 0 | 030030D9 | Previously corroborated FOV operation |
| 560 | 0 | 1F000000 | Terminal node retained numerically |

The 30D9 association with native setter `00483CD0` was established in
[the behavior/object study](2026-10-23-camera-behavior-object-links.md).
That setter writes camera entry +94 and projection context +D8, then
rebuilds projection if the angle changed. This track supplies the same
angle at both keys, not a progressive FOV curve. It supports interpreting
the zoom as camera movement, while leaving any other runtime writers open.
The exact float differs slightly from the 1.3 startup constant; retain its
original bits rather than replacing it with a rounded constant.

## Message 999: interface action construction found

In `0059F140`, the message structure receives type 0032 and value 999.
`00673850` creates an action; `00699B80` copies all 13 message words into it.
`00568550` wraps the action and attaches it via `00468070` to the element
stored in the menu state at +6D0 (piVar1[1B4]). Earlier in the same function,
that element is obtained by `00528E00` using the menu resource/index pair
at +6C4/+6C8 with an index increment of 3.

On receipt, `0061A600` handles type 0032/value 999 and sends 006E to the
Balcony CAM_Insert reference at +6CC, among other recipients. This closes
the action-construction-to-receiver association. The element's resolved
resource name and visible label have not yet been established here:
identifying it conclusively as New Game remains pending. No runtime click
was captured. The native action invocation callback also remains to trace.

## Reproducible scope

`src/decode_camera02_events.py` decodes this exact layout, preserves all
instruction operands/tags, and never executes them. Its CLI hash-checks the
source and refuses to overwrite an existing JSON output:

```powershell
python .\src\decode_camera02_events.py <decoded.bin> <new-report.json>
python .\tests\test_camera02_events.py
```

Four synthetic tests cover boundaries/timing, preservation of unknown nodes,
truncation and unsupported header/count rejection. The real frozen resource
consumes exactly [496,624) and confirms identical instruction sequences.
The older decoder intentionally still preserves this span raw; this separate
decoder supplements it. Next: resolve the UI element and action invocation,
then sample quaternion orientation for a controlled visualizer transition.
