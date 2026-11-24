# Prince terminal idle loop and activation (2026-11-23)

This extends [initialization and return](2026-11-23-prince-idle-init-return.md).
Evidence comes from the original PC GOG executable and runtime state captures;
no historical engine sources were consulted. No Rust controller changed.

## Terminal loop verified

A clean capture without user input records these consecutive stages. Times are
relative to this capture, not scheduling constants for OpenJade.

| Frame | Seconds | Action | Stage | Repetition counter | Rate | Blend flag after selection |
| --- | --- | --- | --- | --- | --- | --- |
| 2010 | 15.758 | 24 | 1 | 0 | 10 | Clear |
| 3048 | 23.060 | 24 | 1 | 1 | 10 | Clear |
| 4087 | 30.362 | 1 | 2 | 0 | 10 | Set |
| 4369 | 32.368 | 1 | 2 | 1 | 10 | Set |
| 4650 | 34.370 | 1 | 2 | 2 | 10 | Set |
| 4932 | 36.370 | 24 | 3 | 0 | 5 | Clear |
| 7013 | 50.975 | 24 | 3 | 1 | 5 | Clear |
| 9093 | 65.577 | 24 | 3 | 2 | 5 | Clear |
| 11172 | 80.178 | 24 | 3 | 0 | 5 | Clear |

All nine requests occur with the primary playback end flag set and use forced
restart. Row 1, restart-stage entry 3 and the idle gate remain selected at these
calls. After three slow action-24 cycles, the counter resets to zero and stage
remains 3: the initial fast cycles and action-1 section are not replayed at this
terminal wrap. One full terminal wrap and the start of its next cycle were
observed; indefinite stability is not claimed.

The blend flag is set on the return to action 1 and on its two subsequent
restarts. This does not contradict the earlier direct 1-to-24 transition: the
edges differ. The blend curve, duration and resulting palettes still need
measurement before faithful runtime integration. The probe records the flag,
not a fully verified interpolation equation.

## Activation boundary

Native event dispatch `005F0AA0` branches on event ID `0xEA` to call site
`005F2748`, passing the message value at `+0x2C` to gate setter `0050BE80`.
The setter's observed calls carry 0 and 1. A separate behavior path disables the
gate through `005EFFCA`; its exit/reset path enables it through `005EFE12`.
The previously documented counters and stage resets apply at that boundary.
The idle path in `005302F0` tests the gate before invoking `004EE490`; this is
not simply elapsed time since the scene was loaded.

Earlier recordings contained movement/action interruptions while the user was
using input devices. They are retained as interrupted evidence, not used to
validate an uninterrupted idle sequence. A separate capture stopped before wrap
and is explicitly marked incomplete. This establishes the need to handle
interruption/reset independently from normal terminal looping. It does not
identify every original scene event sender or all UI activation conditions.

## Verification

`validate_prince_idle_wrap.py prince-idle-wrap-quiet` passed checks for action,
stage, counter, source-backed restart-stage setting, rates, playback-end flags,
blend flags, activation/deactivation call sites and clock coverage.
`prince-idle-wrap-validation.json` records the events and text capture hashes.
The capture helper stops the research game before copying files, avoiding the
unequal clock/log extents seen in the preceding investigation.
The research proxy DLL was restored to SHA-256
`e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`.

Next: measure the action-1 blend and identify the menu event sender/activation
mapping before integrating the independent controller. Terminal sequencing is
now observed; full actor activation and transition fidelity are not yet complete.
