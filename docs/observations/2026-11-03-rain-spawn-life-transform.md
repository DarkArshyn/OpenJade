# Rain creation, timer transitions and emitter matrices (2026-11-03)

Follow-up to [native parameter loading](2026-11-03-rain-native-parameters.md).
The same hash-verified PC GOG executable and frozen menu container are used.
Original game files remain read only. Executable code runs only in isolated x86
emulation for these checks; this is not a live observation of the menu.

## Random creation

Native CRT `0072955B` advances a 32-bit state by `state*214013+2531011` and returns
`(state>>16)&32767`. The rain creation branch consumes draws for the initial timer,
two sizes, two rectangle coordinates and speed. Zero speed still consumes a draw.
A zero initial timer takes an additional main-phase sampling branch. Seed values
1, 42 and 12345 were supplied to the original seeding function; they are test
inputs, not recovered game seeds. A private CRT thread-state stub isolates the
random stream. The generator and creation arithmetic execute natively.

Independent `initial_sample` comparisons pass for timer, flags, sizes and position
(tolerances 1e-7, exact flags, 1e-6 and 2e-6 respectively). Random stream sharing
with other game systems and the actual initial seed remain unverified.
The 0.02 float input alone produces no creation: its extended-precision product
with 50 is just below one. At 0.03 the tested emitter creates one particle.
Do not round the rate product to float32 before truncating without validation.

## Timer boundary checks

Six cases execute `004307F0` with one live particle and one quantized step:

| Initial state | Timer | Result |
| --- | --- | --- |
| Initial phase (flag 1) | 0 | Main phase; timer approximately 0.983333 |
| Initial phase (flag 1) | Exactly h | Same phase, timer becomes zero |
| Main phase (flag 0) | 0 | Enters end phase, then removal for the short seeded duration |
| Main phase (flag 0) | Exactly h | Same phase, timer becomes zero |
| End phase (flag 2) | 0 | Removed |
| End phase (flag 2) | Exactly h | Same phase, timer becomes zero |

The seed-42 end duration is about 0.00320444, shorter than one update. This proves
that more than one phase transition/removal can occur in an update. Equality does
not expire a phase. No fade/opacity behavior is inferred from these timer checks.

## Matrix selection and axes

`0042B9D0` initializes the first emitter context with selector +0x40 equal to zero.
`0042EE80` copies the effective GAO matrix pointer at object +0x0C when this
selector is zero; otherwise it uses the context matrix. A nonzero context link
at +0x94 can also cause a composed matrix update before emission. These branches
must be preserved rather than always using the stored matrix.

Mode 1 uses matrix row 0 and row 2, i.e. local X and Z, not X and Y.
A controlled rotation/translation test and an explicit context override test pass.
Both real stored rain matrices also pass when supplied through the GAO fallback.
They have X=(1,0,0), Y=(0,0,-1), Z=(0,1,0), so their local XZ rectangles are
horizontal in world XY. Their stored centers are:

- Rain01: (-91.851890564, 2.011213064, 9.291855812).
- Rain02: (-100.629737854, -3.591801882, 9.291855812).

These are verified stored centers, not a claim that no behavior changes them.
**Still unresolved:** capture the effective object matrix, context selector and
optional link during the live menu. Controlled emulation establishes the math
and branch behavior but cannot establish the live branch or hierarchy state.

## Evidence and reproduction

Local reports under `reports/menu-effects-20261103/`:
`native-spawn-check.json`, `native-phase-check.json`, `native-transform-check.json`
and `rain_spawn_check.py`. Run the harness from the research workspace where
`.native-oracle-deps` contains Unicorn. Allocation/resource lookup is stubbed;
these tests do not validate resource loading, renderer state or full population.
Ghidra follow-ups are in `reports/rain-emitter-context-20261103`,
`rain-emitter-setup-20261103` and `rain-rng-20261103`.

```powershell
python -m unittest discover -s tests -p test_menu_rain_parameters.py
```

Six synthetic/reference regression tests pass. No rain is added to Vulkan yet.
Next: observe live emitter state and the actual particle draw, then connect the
validated native parameters and behavior to the runtime.

Follow-up: [live menu state](2026-11-03-rain-live-state.md) now confirms the
GAO-matrix fallback and both stored matrices during three captured menu frames.
