# Global-camera field 0x410: writers and candidate inputs

Static investigation, October 23, 2026, following
[camera state selection](2026-10-23-camera-state-transition.md).
Executable SHA-256:
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
CameraAndGlobal SHA-256:
`68c1323218f0c5479c5064a53ac3c60a329e45cba6c11c7f08affbb649484582`.
All addresses refer to this executable; no runtime capture was performed.

## Confirmed setter

`005A9770(camera, candidate)` writes its second argument to camera field `0x410`
at instruction `005A97B5`. The destination field-storage base is obtained from
`camera + 0x18 -> +0x04 -> +0x44`. Interpreter context is temporarily switched
to that camera and restored afterward.

The helper then calls `005A95E0(camera, candidate)`, which records a non-null
resolved candidate in ten slots at `0x60C..0x630`. It fills the first empty slot;
when all are occupied it shifts entries left and writes the last slot. This is
observed list maintenance, not proof of a user-facing history feature.

The global definition `B60024E1` declares field offset 1040 (`0x410`) with
identifier `0C132FA9`, count 1 and tag `00090028`. The base tag `0x28` and native
object dereferences support an object-reference field. Its live identity is
not established by that declaration.

## Two inspected callers

| Call site | Function | Candidate source and gate |
| --- | --- | --- |
| `005C0891` | `005C07A0` | Second argument; requires a non-null third argument and either a successful helper result or a nonzero fourth argument |
| `005C0BAD` | `005C0900` | Selected local candidate; requires its resolved object field `0x88` to be nonzero, after preceding checks |

`005C07A0` calls `0054A020` for its conditional check, then invokes the setter,
updates field `0x740`, informs the manager through `004B0700`, and selects
behavior `B60025BD` for slot 2. It is not an unconditional assignment on entry.

`005C0900` saves the former `0x410` reference in `0x470` before its setter call.
It obtains candidates through `005A9920` or `005AA130`, with other validation
and cleanup steps. In this path its calls to `005AA220` pass zero as the third
argument, so the conditional clearing branch described below is not taken.

## Upstream manager and candidate list

`004B0900` and `004B1460` call `005C07A0` using:

- camera object from manager field `0x4F8`;
- candidate from manager field `0x34 + 4 * [0x14]`.

`004B0900` passes that same candidate as the third argument and forces the fourth
argument to 1 when its own conditions permit the call. `004B1460` uses a previous
selected value as the third argument and passes 0 as the fourth.
The contents and runtime index of the manager list remain unresolved.

For the other path, `005A9920` scans eight entries at camera fields
`0x4EC..0x508`, with filtering and an optional earlier override via `005A9340`.
Its ordinary selection retains the candidate with the greatest inspected
integer value, obtained by `005498A0` from candidate field `0xFC`, starting
with threshold -1. `005AA130` instead returns the first candidate in that list
whose field `0xFC` exceeds its supplied threshold. No descriptive name is
assigned to that score until its initialization is traced.

## Confirmed clear paths

| Instruction | Function | Condition/context |
| --- | --- | --- |
| `005AA2B5` | `005AA220` | Third argument nonzero and supplied object equals current `0x410` after special-reference resolution |
| `005E3363` | `005E3240` | Clears `0x410` in its reset sequence |
| `004B1DD5` | `004B1A40` | Clears `0x410` in the branch whose inspected discriminator equals 5 |

The native table binds `005E3240` to `3200043E` and `004B1A40` to `B60024E0`;
both are typed OFC links in the global camera's behavior list `B60024E2`.
This corroborates their camera context. It does not establish when those
branches execute in the main menu.

## Rejected offset-only matches and limits

The initial bounded byte search found other stores at displacement `0x410`.
`004E8120` stores a time-derived float there, and `005D9EB0` manipulates bit
flags there. They are not evidence for this camera pointer merely because
the numeric offset matches. Remaining raw candidates are not claimed as
camera writes without context. The search is not exhaustive for aliases,
indirect stores, bulk initialization or interpreter writes.

The setter and three clear-store byte sequences were checked independently
against the hash-verified executable. The field descriptor and two reset
bindings/typed links were checked against the selected decoded container.
Local ignored evidence: `reports/camera-source-writers-20261023/` contains four
Ghidra batches, `validation.json` and its validation script. Native exports
were produced with the existing `OpenJadeFog.java`, in read-only mode.

Next: identify writes to the manager list at `0x34` and camera candidate list
at `0x4EC`, then map those references to named menu objects. Camera02 is still
not verified as the selected object. Preview defaults and game assets are
unchanged; no new runtime implementation or synthetic regression test is claimed.
