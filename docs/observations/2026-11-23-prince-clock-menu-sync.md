# Prince playback clock and menu synchronization (2026-11-23)

This follows [blend and activation measurements](2026-11-23-prince-blend-activation.md).
Evidence is from original GOG resources and native captures; historical engine
sources were not consulted. No runtime controller was changed in this step.

## Playback time without phase fitting

The test evaluates 101 consecutive captured poses, with 34 primary local bone
rotations per pose. Selection events identify the start of each clip; the rate
is checked against the captured primary playback field at +0x08. Clip time is
computed as rate multiplied by the sum of captured update durations after the
selection frame through the draw frame. No pose search, fitted time offset or
screenshot alignment is used.

| Selection frame | Incoming action | Source clip | Captured rate |
| --- | --- | --- | --- |
| 4721 | 1 | 2D000AD4 | 10 |
| 4750 | 1 | 2D000AD4 | 10 |
| 4780 | 1 | 2D000AD4 | 10 |
| 4810 | 24 | 330010E9 | 5 |

The three blend accumulators are also recalculated from captured update durations,
with integer truncation to 1/15360-second units and the observed 11/60-second
termination threshold. Their active flags and counters match the native samples.
Predicted coefficients, rather than captured coefficients, drive pose evaluation.
The maximum rotation-matrix RMS error is 5.844e-5, below the existing 2e-4 threshold.

This validates the sampled update ordering, clips, rates and observed linear blend
mode. It does not establish bit-exact x87 behavior, every possible transition mode,
or long-session clock drift. The prior translation checks remain separately
reported; the 101-pose test concerns rotations.

## Synchronized menu and camera capture

A lighter probe records menu messages, idle-gate setter calls and 3,002 view
matrix samples on the same frame counter. The user selected New Game and left
input idle afterwards. Registry matches identify senders by original resource
key, rather than by process-specific addresses.

| Frame | Native event | Observed effect |
| --- | --- | --- |
| 1 | Menu_Start_Demo (0B0044CA), class 2 / event EA / value 0 | Idle gate disabled |
| 460 | Menu receives class 32 / value 999 after New Game selection | Existing UI-to-camera branch executes |
| 460 | Menu_Start_Demo, class 2 / event EA / value 1 | Idle gate enabled |
| 461 | Camera02 (30000CF0), class 7 / value 2 / parameter 0 | Camera-entry handler disables idle gate |
| 462 | First view sample differing from the initial view | Camera motion visible in captured matrix |
| 1746 | Camera02, class 7 / value 3 / parameter 0 | Exit/reset handler calls the enable setter |
| 1746 | First terminal view sample | View remains stable through frame 3001 |

Event fields are hexadecimal where named EA/32; frame identifiers and values
999/2/3 are decimal. The view comparisons use a maximum component tolerance of
1e-5. These frame numbers are capture identifiers, never runtime delays.

The camera message sender is recovered at message offset zero. Class is at +0x30,
value at +0x28 and parameter at +0x2C. The entry/exit messages reach `005EFCF0`:
value 2 enters its suspension path; value 3 follows its nesting/reset path.
The traced setter call sites are `005EFFCA` and `005EFE12`. At exit the gate is
already one before the setter call, so this capture must not be described as
proving a unique writer or a continuously sampled gate value throughout motion.

The sum of presentation update durations between camera messages is approximately
9.029 seconds. The source camera track lasts 9 seconds. These are different
measurements; exact equality between the presentation clock and the camera's
internal clock is not claimed.

## Independent integration contract

The observed menu sequence supports an event-driven controller: suspend idle at
menu initialization, process New Game activation, suspend it during Camera02's
entry, and process the exit/reset when Camera02 completes. Preserve the native
reset conditions, clip-end decisions and untracked-channel state documented in
the preceding studies. Do not trigger the Prince sequence using a fixed delay
measured from scene load or copied capture frame numbers.

This closes the previously pending no-phase-fit rotation check and identifies
the menu/camera activation boundaries for this observed route. Implementing the
controller in Rust, connecting camera lifecycle events, and validating resulting
Vulkan poses, sheath continuity and frame times remain the next integration step.

## Artifacts and checks

Private results are stored under `reports/prince-clock-menu-20261123/`:
`prince-clock-validation.json`, `prince-menu-sync-validation.json` and measurement
scripts. Their hashes identify the original local evidence. The clock test covers
101 poses; the synchronization test checks the four sender-resolved messages,
menu action and stable initial/final view intervals. Raw game data is not published.

The temporary capture proxy was restored to SHA-256
`e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`.
No Vulkan performance result is claimed for this research-only change.
