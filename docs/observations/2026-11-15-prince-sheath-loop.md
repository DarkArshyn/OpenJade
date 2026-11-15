# Native sheath state across body loops (2026-11-15)

## Original-game evidence

An extended private probe records 2,000 updates of the sheath controller around
`006E1020` plus sampled body shader palettes. The capture spans about 30.103 seconds
of the recorded native clock. The resource parameters and executable identity are
the same as the earlier [sheath observation](2026-11-15-prince-sheath-balcony.md).
The research-copy proxy was restored, SHA-256
`e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`.
The original installation was not modified. No historical engine source was used.

Update capture SHA-256:
`9a8d69d917b969a6345177da99e2691a7d4d44c7f487e7ba7841aa56d37e788b`.
Private evidence is retained in `reports/prince-sheath-loop-20261115`.

As in the earlier pose study, the source clip phase is fitted from 34 primary
local bone rotations, using a 0.01-tick grid. Three sampled pairs identify wraps
with rotation RMS below 0.0002 on both sides:

| Frames bracketing wrap | Fitted ticks | Native clock seconds |
| --- | --- | --- |
| 252 / 264 | 19.66 / 0.26 | 3.933 / 4.126 |
| 504 / 516 | 19.31 / 0.17 | 7.893 / 8.081 |
| 756 / 768 | 19.09 / 0.00 | 11.850 / 12.038 |

These bracket the boundary, not its exact instruction or frame. At later times,
matching the selected clip deteriorates (maximum RMS about 0.118); these samples
do not validate more repetitions or identify the next action.

For all 1,999 consecutive pairs of selected controller calls, previous-position,
endpoint and velocity fields (nine floats at data +0x20 through +0x40) entering
the next call equal the preceding output exactly. In particular, there is no
rest reset between calls bracketing the three accepted body loops. One-step
dynamics across all 2,000 updates reproduce endpoints within 1.3381e-6,
velocities within 9.7802e-5, and output matrices within 1.2885e-5.

## Runtime correction

Only the body clip phase now wraps. The controller advances on an absolute
125 Hz diagnostic timeline and preserves its endpoint/velocity across wraps.
The first-cycle cache remains; one additional checkpoint holds the latest full
step. Forward playback evaluates only new steps, keeping memory bounded by the
first-cycle cache plus one state. Fractional queries never modify that checkpoint.
Backwards seeks replay from the first-cycle cache if needed; long fresh seeks
cost work proportional to elapsed time. Accepted diagnostic time is 0..86400 s;
invalid clocks query the initial pose. Reloading the controller clears history.

This fixes the artificial four-second reset, without smoothing, changing source
constraints or importing captured animation poses. Rest startup and the 125 Hz
step remain diagnostic policies: the original has variable timestep and template
relocation at startup. General action selection and other reset conditions remain
unimplemented. This is not full native trajectory parity.

The maximum vertex displacement over 3.999990 -> 4 seconds falls from
0.325568408 to 0.000000517 scene units. Across the final 1/60-second interval,
it falls from 0.325070918 to 0.000717615. Regression checks cover the native fixture
boundary, cache/replay equality, repeated timestamps, backwards queries and reload.
Python reference pose and light-color fixtures are regenerated for the new timeline.

## Post-change runtime verification

At the same fixed Camera02 endpoint, a live 1,800-frame 800x600 FIFO run completes
with zero Vulkan validation errors. Simulation median/p95: 0.674/0.802 ms;
GPU command median/p95: 0.312/0.321 ms; frame interval median/p95: 5.670/11.087 ms.
The previous 600-frame reference was respectively 0.663/0.809, 0.311/0.331 and
5.607/11.294 ms. These runs do not indicate a material performance regression;
they are local measurements with different sample counts, not a statistical proof.
All eleven actor tests (including three private fixture checks) pass, as does
workspace Clippy with warnings denied. The research-copy DLL restoration is verified.
