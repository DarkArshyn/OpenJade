# Prince return blend and menu event sender (2026-11-23)

This extends [terminal-loop validation](2026-11-23-prince-idle-terminal.md).
Evidence uses original GOG resources and captured native palettes/state. No
historical engine sources were consulted. The Rust controller is unchanged.

## Return from action 24 to action 1

The captured secondary playback record has duration byte 10. Its native duration
is `(10 + 1) / 60`, or 11/60 second. The elapsed counter is stored in units of
1/15360 second. The sampled elapsed values are 0, 1536 and 2595; the corresponding
linear coefficients are 0, 0.545454545 and 0.921519886. The blend flag clears on
the following sampled frame. These are observed states, not a frame-count schedule.

A source-derived quaternion interpolation from the terminal pose of `330010E9`
to `2D000AD4` agrees with 34 primary local bone rotations. Across twelve samples,
the maximum rotation-matrix RMS error is 5.844e-5, below the existing 2e-4
comparison threshold. The pelvis translation's maximum component error is
3.000e-5 source units, below the selected 5e-5 check threshold.

**Limit:** incoming clip phases were fitted to the observed rotations. This does
not independently validate the playback clock. Probe overhead enlarged frame
durations, leaving only three active blend samples including coefficient zero.
Neither high-refresh timing nor every blend edge has been validated by this test.

## Untracked channels retain state

The alternative clip also contains a translation channel for bone 1,
`B_Pr_Bip Spine.gao`; the normal clip does not. During all 89 captured frames
from 4721 through 4809, across the return and subsequent action-1 restarts,
this local translation remains at the alternative clip's terminal value.
Maximum component difference is 5.406e-8. Its difference from the stored initial
transform reaches 8.817e-4 source units.

Consequently, resetting every missing channel to its resource-local transform
at an action change would not reproduce these observations. A future multi-clip
evaluator must preserve this state. This observation does not by itself define
the policy for every channel, actor or transition. The current single-clip
runtime has not been modified speculatively.

## Menu event sender

Two captured `0xEA` messages contain values 0 and 1 at offset `+0x2C`. Their
sender pointer at offset zero resolves through the loaded resource registry to
`0B0044CA`, `Menu_Start_Demo.gao`. The existing
[menu startup investigation](2026-10-24-camera02-menu-startup.md) independently
links that resource to the startup behavior. Small integers elsewhere in the
message also match unrelated registry entries; they are not treated as pointers.

In this capture, the gate is disabled at frame 1 and enabled at frame 237 through
`005F2748`. A separate behavior path disables it at frame 238 through `005EFFCA`;
its reset/exit path enables it at frame 1014 through `005EFE12`. These frame
numbers identify evidence only. They must not become runtime delays. The full
relationship between these transitions, UI activation and camera insertion still
requires a synchronized trace before enabling the complete Vulkan controller.

## Reproduction and integration boundary

Private working artifacts are `prince-idle-blend/`, `prince-idle-event/`,
`measure_prince_blend.py`, `measure_prince_blend_translation.py` and
`validate_prince_blend_activation.py`. The validator checks the fitted rotations,
pelvis translation, retained spine translation and two registry-resolved event
messages. `prince-blend-activation-validation.json` records measured errors,
limitations and capture hashes. Captured palettes and game data remain private.

The research proxy was restored to SHA-256
`e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`.

Next: validate incoming clip time without phase fitting and synchronize the gate
with the menu/camera events, then implement the independent stateful controller.
Vulkan integration, visual comparison and performance validation remain pending;
this research result is not a claim of a new runtime feature.
