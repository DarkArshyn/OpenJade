# Prince idle action selection (2026-11-22)

## Scope and evidence

This investigation uses original GOG resources and executable observations only. It identifies the observed selection of body clip `330010E9`; it doesn't implement a general actor scheduler in Vulkan.
Private captures and native analysis remain outside public source files.

## Resource and controller chain

`Prince.gao` (`CC000431`) references action table `2D000ACC`. Its zero-based entry
24 references `330010D9`, whose clip key is `330010E9`. Native registry resolution
confirms the same chain. The original descriptor stores rate 5.

The observed request originates at `004EE6AA`, inside the Prince idle controller
`004EE490`. It calls action API `0047F180` with `0x80000018`; selector `006BD270`
removes the high bit and treats it as a forced restart request for action 24.
The instance's current action changes from 1 to 24 and its descriptor pointer
changes to the registry-resolved `330010D9` allocation.

The controller uses an activation gate, an end-of-action condition, a repetition
counter and a sequence table. In the measured case, its native variable block has:

| Offset | Observed meaning and value |
| --- | --- |
| `+0x704` | Idle-controller gate enabled: 1 |
| `+0xC4` | State value 1, bypassing the elapsed-time early return in this call |
| `+0x294` | Sequence row: 1 |
| `+0x3E0` | Sequence stage at selection: 1 |
| `+0x290` | Repetition counter after advancing the stage: 0 |
| `+0x9B4` | Sequence table; observed row starts `1, 24, 1, 24, -1` |
| `+0xE54` | Repetition table; corresponding row starts `1, 2, 3, 3, 0` |

The table accessor uses the stored row width (15 here), with data after an
8-byte header. These are captured state values, not yet source-file defaults.
Their initialization and all activation paths remain to be traced.

## Observed transition and rate

Immediately before the request, the primary playback end flag is set. Immediately
afterward it is clear. The current action becomes 24, while the pending-action
and transition-action identifiers remain `0xFFFF`. The active-blend flag remains
clear. This specific 1-to-24 transition is a direct restart, not evidence for a
new timed crossfade. Stale upper bits in the transition word must not be mistaken
for an active transition.

Call site `004EE6F2` then applies rate **10** to channel 0 through `00481360`.
This independently confirms the earlier approximately 10-unit/second pose fit;
the descriptor's stored rate 5 is overridden by the controller for this stage.

Two independent captures selected action 24 at accumulated frame-clock times
71.688999 and 16.661000 seconds. These are capture-relative times, not delays to
encode in OpenJade. The activation histories were not established, so the cause
of that timing difference is not claimed.

## Validation and remaining work

A local validator checks the original table/descriptor links, rate, captured
current/pending action fields, playback end flag, absence of active blending,
sequence row, repetition row and rate call. Its checks passed. Private evidence:
`prince-idle-proof-validation.json`, `prince-idle-proof/` and
`prince-action-calls/`, with source offsets and SHA-256 hashes in the validation
report. The research proxy DLL was restored to SHA-256
`e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`.

Next: identify initialization of the idle gate, sequence row, repetition counts
and stage; resolve their provenance independently; capture the return from action
24. Do not substitute a fixed timer or publish a complete sequence implementation
until these conditions are verified. The previous unexplained 16-25 second pose
interval is not resolved by this capture alone.

No rendering code or runtime package changed. No new Vulkan performance claim is
made. See [body-loop evidence](2026-11-15-prince-sheath-loop.md) for prior scope.

## Follow-up (2026-11-23)

[Initialization and return](2026-11-23-prince-idle-init-return.md) resolves the bounded default ranges, native table filling and the observed return to action 1. The earlier remaining-work list records the state of this investigation on 2026-11-22.
