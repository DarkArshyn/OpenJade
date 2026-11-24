# Prince idle initialization and return (2026-11-23)

This extends [idle selection](2026-11-22-prince-idle-selection.md) using only
original GOG resources, native executable analysis and new runtime captures.
Historical engine sources were not consulted. No actor scheduler was added to Vulkan.

## Initial state and table provenance

The pre-initialization capture matches the following original `BB000032` payload
ranges byte for byte. These are bounded matches, not a complete variable-format
specification or proof that every field uses one linear mapping.

| Native variable offset | Resource payload offset | Bytes | Observed initial value |
| --- | --- | --- | --- |
| `0x290` | `0x1D20` | 8 | Repetition counter 0, sequence row 1 |
| `0x3E0` | `0x1E70` | 4 | Stage 0 |
| `0x700` | `0x2190` | 8 | Auxiliary sequence flag 0, idle gate 1 |
| `0x9B4` | `0x2444` | 668 | Dimensions 11 by 15, zero-filled entries |
| `0xE54` | `0x28E4` | 668 | Dimensions 11 by 15, zero-filled entries |

The populated sequence values are therefore **not stored in those resource
entries**. Call site `0059E549` invokes `004F0F80`, which fills the tables during
native initialization. A before/after capture at that call confirms the row used
by the menu:

| Stage | Action | Repetitions | Observed playback rate |
| --- | --- | --- | --- |
| 0 | 1 (`2D000AD4`) | 1 | Not re-established here for initial activation |
| 1 | 24 (`330010E9`) | 2 | 10 units/second |
| 2 | 1 (`2D000AD4`) | 3 | 10 units/second |
| 3 | 24 (`330010E9`) | 3 | 5 units/second at entry |
| 4 | Sentinel -1 | Not an action | Not applicable |

The same initializer writes 3 to the row's restart-stage entry at native offset
`0x87C`. The selector reads this when it encounters the sentinel; the eventual
long-run wrap was not captured in this test. These observations specify behavior;
no decompiled routine is copied or translated into engine source.

## Conditions and resets

`0050BE80` writes the idle gate and calls reset routine `004EAD60` when enabling
it. `004E72B0` accepts sequence rows 1 through 10, then clears stage, repetition
count and the auxiliary sequence flag. A row argument of 0 leaves the current
row unchanged; the menu capture actually records such a no-op request from
`00508D00`, with row 1 retained.

The gate starts at 1 but does not stay enabled throughout startup. A separate
capture observes calls from `005F2748` disabling it at frame 1 and enabling it
at frame 196; `005EFFCA` disables it at frame 197. `005EFE12` subsequently enables
it at frame 961. These frame numbers describe that execution only.
The latter path in `005EFCF0` clears stage, repetition count and the auxiliary flag,
sets the delay field to 10, and enables the controller after its behavior exit
conditions are met. These are behavior-driven conditions, not one elapsed-time
schedule. All possible UI/input interactions and the complete initial variable
loader remain outside this validation.

## Return observed in the game

The long capture records the following requests from the same idle controller:

| Frame | Previous action | Requested action | Rate applied afterward |
| --- | --- | --- | --- |
| 5162 | 1 | 24 | 10 |
| 5821 | 24 | 24 | 10 |
| 6480 | 24 | 1 | 10 |
| 6661 | 1 | 1 | 10 |
| 6841 | 1 | 1 | 10 |
| 7013 | 1 | 24 | 5 |

The two completed action-24 intervals measured 7.286 and 7.359 seconds in the
accumulated frame clock, consistent with the 73-unit clip at rate 10 within
capture/update granularity. The next two measurable waiting intervals were
2.006 and 2.007 seconds. No timestamp is assigned to frame 7013: that event log
extends beyond the copied clock's 6,975 samples. Files were copied while the game
was still advancing, so their common extent must be respected.

The action-24 return is thus verified as selection of action 1, with three
consecutive action-1 requests before selecting action 24 again. Requests carry
the force-restart bit. This is not a fixed timed chain inferred from a video.
The earlier direct-restart result remains specific to the measured 1-to-24 edge;
this test does not claim general transition or blending compatibility.

## Reproduction and limits

Private scripts and reports: `validate_prince_idle_init_return.py`,
`prince-idle-init-return-validation.json`, `prince-idle-fill-proof/`,
`prince-idle-init-proof/` and `prince-idle-return/`. The validator checks source
ranges, initial state, zero-filled tables, populated row, repetition counts,
restart stage, return requests, rates and bounded clock intervals. Checks passed;
source offsets and capture SHA-256 hashes are recorded in its JSON report.
The research proxy DLL was restored to its original SHA-256
`e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`.

Remaining work: validate activation against the intended menu state, the terminal
wrap and a source-backed independent runtime controller. Retain the distinction
between asset defaults, behavior initialized from the executable and experimentally
observed values. No rendering changes or new frame-time claims are made here.

## Terminal-loop follow-up

[Terminal-loop and activation validation](2026-11-23-prince-idle-terminal.md) now verifies the stage-3 wrap and records blend activation on the action-1 return and restarts. The limits above describe the earlier capture.
