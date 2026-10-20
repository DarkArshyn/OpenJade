# Located dynamic functions 5b82 and 5b83 — 2026-10-19

## Result

Both function definitions are present in the already decoded **Menu3D** resource,
not in the previously examined CameraAndGlobal behavior blocks. The descriptor
pair model `263c` / file `005d` is associated with the definitions by matching
function identifiers and their shared behavior-resource links. This is not a
verified arithmetic conversion from model/file numbers to archive keys.

Source: Menu3D decoded WOW, SHA-256
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
Body record `B60024E5` begins at container offset 1474133 and has 13072 payload
bytes. All function offsets below are relative to its payload.

| Function | Definition start | End marker | Tokens through end marker |
| --- | ---: | ---: | ---: |
| `5b82` | 5352 | 5432 | 11 |
| `5b83` | 5808 | 6912 | 139 |

Both starts use category 1c and the expected identifier; both finish with a 1d
marker before the next definition. These are resource-language bodies, not newly
recovered original source code. Token dumps remain in ignored local reports.

## Descriptor and object linkage

The populated `08000338` table is at container offset 1489142, with 49 records.
It agrees with the CameraAndGlobal table on model/file pair and signatures:
5b82 has no parameters and returns type 25; 5b83 takes and returns type 25.
Stored indices differ (666/676 here versus 614/624 previously), reinforcing that
these indices must not be treated as stable resource/function identifiers.

Two additional occurrences of key 08000338, at 1506676 and 1524001, contain empty
four-byte tables. The tool retains these occurrences and selects the unique
populated table containing both requested IDs. It does not silently overwrite
duplicate keys or infer runtime precedence among occurrences.

Behavior list `B60024E9` explicitly links `B60024E5` as OFC and `08000338` as TTT,
as well as definition-variable record `B60024E8` as OVA. Two reference chains lead
from named objects to this list:

| Object record | Observed name | Payload reference offset | Eight-byte pair |
| --- | --- | ---: | --- |
| `30000D63` | Menu3D_FarahRoom_CAM_Balcony.gao | 177 | `30000D62` -> B60024E9 / 30000D61 |
| `3C00144D` | Menu3D_FarahRoom_CAMALT_Balcony.gao | 180 | `3C00144C` -> B60024E9 / 3C00144B |

These names and links establish the shared balcony-camera behavior context.
They do not prove which object is current when the caller executes, or whether
the ordinary or alternate camera is active in the captured menu.

## What the bodies establish

5b82 copies current-object field offset **0**, type 25, into local offset 0,
then transfers that local to the return stack and exits. This uses the previously
corroborated 0960, 0836 and 0834 handlers. Its result is therefore a stored field
value in this path, not an independently demonstrated computed world position.
The field's name, coordinate space and initialization remain unverified.

5b83 receives its vector argument through the return/argument stack into local 0,
copies it to local 12, performs conditional component-oriented operations, then
copies local 12 to local 24 and returns it. The body references fields including
172, 276, 396, 436, 464 and 512. Component selectors and several arithmetic helpers
are not fully interpreted here: no clamp, rotation or transform name is assigned.

This resolves the missing-body lead from [the previous investigation](2026-10-18-vector-consumers.md).
It does not yet establish a complete view matrix or reproduce the original framing.

## Search scope and verification

A targeted exact-definition search covered the four already decoded containers:
CameraAndGlobal, Menu3D, MenuBoot and MenuCredits. Only Menu3D contained matching
aligned definitions in a bounded token area. No archive-wide extraction was run.
A native cross-reference query for descriptor lookup 00462fd0 found only the two
calls from loader 00460040 in the current Ghidra project; it did not establish a
model/file-to-key conversion. That evidence is local under
`reports/native-model-file-20261019/`.

The reusable reader freezes the Menu3D hash, checks unique selected body/link
records, retains duplicate table occurrences, requires a unique matching table,
checks the two signatures' model/file values and verifies both GAO reference
chains. Two synthetic tests cover function boundaries, missing ends and ambiguity.
The real-data run resolves both definitions and both object chains.

```powershell
python .\src\resolve_camera_function_bodies.py .\reports\menu3d-focused-4d627a9470c84b73bfc16ae467514310\FF000CB9-decoded\decoded.bin .\reports\camera-function-bodies-new
python .\tests\test_camera_function_bodies.py
```

Recorded output: `reports/camera-function-bodies-20261019/functions.json`.
Game and extracted inputs remain read-only. No game execution occurred.
Next: decode the bounded 5b83 arithmetic and map the relevant variable fields in
B60024E8 and the balcony instances, without assuming an active camera.
