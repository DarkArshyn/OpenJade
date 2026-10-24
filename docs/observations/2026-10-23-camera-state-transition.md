# Global camera state transition

Static analysis, October 23, 2026. This follows
[the manager/global-camera link](2026-10-23-camera-behavior-object-links.md).

Source executable SHA-256:
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
CameraAndGlobal SHA-256:
`68c1323218f0c5479c5064a53ac3c60a329e45cba6c11c7f08affbb649484582`.
Ghidra ran read-only. No live game state was observed.

## Request and dispatch

`005C02E0(object, requested)` temporarily establishes the object's interpreter
context, writes `requested` at field-storage offset `0x84`, calls
`005A8980(object, 2)`, then restores the previous context. Field storage is
reached through `object + 0x18 -> +0x04 -> +0x44`.

The previously examined manager helper `004B1010` calls it with the resolved
global `Camera.gao` and requested value 1 in its corresponding conditional
branch. This does not itself copy a pose or attach a new renderer camera.

`005A8980` compares requested field `0x84` with applied field `0x248` and returns
without switching if they are equal. Otherwise its recognized branches are:

| Request | Behavior resource selected | Native binding |
| --- | --- | --- |
| 1, null field `0x410` or referenced object's `0x1B4` differs from 4 | `B6002512` | `00500C00` |
| 1, referenced object's `0x1B4` equals 4 | `55000018` | `006291F0` |
| 2 | `B6002511` | `00605740` |
| 3 | `08002787` | `005481C0` |
| 4 | `32000451` | `00548930` |
| 0 | Calls `0049E090` for slot 3 and the requested slot | No new behavior selected here |

All recognized branches write the applied field. Several also update flags or
call other helpers. This table describes selection, not every side effect or
the meanings of the numeric modes. Unknown mode values are not interpreted.

`00549050` reads field `0x1B4` from the object supplied by camera field `0x410`.
The referenced object has behavior fields; its identity and role are not yet
established. Calling it Camera02 or a verified pose source would be premature.

## Behavior-slot write

`0049DF70(slot, behavior)` is the selected behavior installer. It writes the
behavior pointer at context `+0x18 + slot*4`, and its first word (the node
pointer) at context `+4 + slot*4`, when the behavior differs from the existing
one. If that node pointer is zero, native mode is enabled and behavior `+0x10`
contains a native implementation, it writes `0xFFFFFFFF` to the execution
slot. This corroborates scheduling a native-backed behavior; it does not
directly call that implementation in this helper.

For the path through `005C02E0`, the slot argument is 2. Consequently the
selected behavior pointer is written at context `+0x20` and its execution
value at `+0x0C`. These offsets are context fields, not object transform fields.

## Connection to pose and FOV work

Both request-1 alternatives contain downstream FOV handling. `00500C00` also
ends a pose-update path with `00477540` on the current object and then calls
the same state dispatcher again. `006291F0` contains a direct FOV setter call
and a branch using `005BF780`. Their complete geometry/interpolation logic is
not decoded in this investigation. These observations do not determine the
menu's final position, orientation or FOV.

The immediate unresolved input is the object pointer at global-camera field
`0x410`. Its writes and object association should be traced before choosing
either branch for the offline menu renderer. The fact that the main menu is
visually stationary does not identify which branch is executing.

## Validation and evidence

Five native key/pointer pairs were independently checked against the executable
table. All five behavior keys are present as typed `.ofc` links in the global
camera's `B60024E2` list, and each selected body exists uniquely in the decoded
container. Input hashes were checked. This is real-data static verification,
not a runtime test or a new math implementation.

Ignored evidence: `reports/camera-state-transition-20261023/`, containing
`validation.json`, its check script and four bounded Ghidra export batches.
To repeat the native inspection, use the existing read-only setup and
`OpenJadeFog.java` with `005C02E0`, `005A8980`, `0049DF70`, `00549050`,
`00500C00` and `006291F0` into a new output directory.

No source game files, preview camera defaults or runtime code changed.
