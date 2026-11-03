# Native rain parameter loading and update (2026-11-03)

## Evidence chain

Verified PC GOG executable SHA-256:
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
The frozen menu source hash is documented in the [effect inventory](2026-11-03-menu-effects-inventory.md).
Ghidra runs use the existing project with `-readOnly -noanalysis`; game files are
read only. Decompiled game code remains in ignored local reports, not source control.

- `0043F120` loads a resource and invokes its selected reader.
- `00435840` consumes the type/version words and selects a 44-byte table entry.
- `00431F40` installs reader `0042D6D0` at `00A6EA24` for type 11.
- `0042D6D0` reads version 23 into a 0x164-byte runtime descriptor.
- `00431D30` invokes update `004307F0`, then emission `0042EE80`, using
  `0080CBFC` as the time input. A frame marker prevents repeated normal updates.
  Flags and global state gate these calls; active emission is not implied solely
  by a resource being present.

## File values and operational meanings

Offsets include the eight-byte resource type/version header.
Both rain descriptors `2E00E1B3` and `2E00E1B4` contain identical values.

| File offset | Runtime offset | Value | Verified use |
| --- | --- | --- | --- |
| 0x08 | 0x08 | 150 | Stored count field; do not equate it to the live population |
| 0x0C | 0x14 | 0x08020241 | Behavior flags |
| 0x14 / 0x15 | 0x1C / 0x1D | 1 / 0 | Rectangular spawn branch / axial velocity branch |
| 0x1A / 0x1E | 0x44 / 0x48 | 4 / 6 | Local rectangle half extents |
| 0x26 | 0xDC | 50 | Emission accumulator multiplier |
| 0x2A / 0x2E | 0x50 / 0x54 | 0 / 0 | Initial speed range |
| 0x4A / 0x4E | 0x70 / 0x74 | 1 / 1 | Main phase duration range |
| 0x52 / 0x56 | 0x78 / 0x7C | 0 / 0.600000024 | End phase duration range |
| 0x5A / 0x5E | 0x80 / 0x84 | 0 / 0.100000001 | Initial phase duration range |
| 0x62..0x6A | 0x8C..0x94 | (0,0,-70) | Acceleration vector |

Emission adds the time input to an emitter remainder, truncates its product with
50 to an integer request, and subtracts requested/50 from the remainder before
clamping the request to available capacity. Forced emission and quota flags have
separate branches. These are engine-time units; wall-clock synchronization and
any runtime overrides have not been measured here.

Spawn mode 1 draws two independent CRT random values divided by 32767 and maps
them to [-4,4] and [-6,6] along the emitter basis axes. Velocity mode 0 samples
its speed range along the negative third axis; the stored rain range is zero.
The descriptor's offset displacement is also zero. Final world placement still
requires the effective emitter matrix, not just its stored GAO matrix.

Lifetime is a three-phase state machine, not a single constant. Flag bit 1 marks
the initial phase; expiry samples the main duration and clears that bit. Main
expiry enters bit-2 end phase, then expiry removes the particle by replacing it
with the last active slot. Expiry uses a strict less-than comparison with the
quantized update interval. The next phase starts with a fresh sampled timer;
this is not equivalent to subtracting elapsed time once from total lifetime.
Phase labels here describe timer states, not independently verified fade curves.

## Native movement timing

For each emitter, update combines the supplied interval and a separate simulation
remainder. It truncates `combined * 60`, then advances that many steps using the
actual float constants `h=0.016666999086737633` and
`k=0.008333000354468822`. The remainder is `combined - steps*h`.
Do not replace these constants by exact 1/60 and 1/120: the rate and step product
are not exactly reciprocal. For the rain branch, each step performs, with native
float stores, `dv=a*h`, `p=(p+dv*k)+v*h`, then `v=v+dv`.
Optional collision and damping branches exist but their flags are clear for the
stored rain descriptor. This does not establish every runtime-modified state.

## Validation and remaining work

`menu_rain_parameters.py` decodes all 274 bytes into 74 mapped fields. An isolated
Unicorn x86 run executes the original reader for both rain blocks: 73 fields
compare exactly; runtime +0x10 is intentionally excluded because the reader forces
it to 1 after reading the stored value. Cursor consumption is exactly 274 bytes.
The harness replaces allocation and resource registration; it does not validate
resource resolution. Type initialization and numeric readers execute natively.

Four isolated live main-phase particle updates (dt=1/120, 1/60, 1/30 and 0.1)
match the independent float calculation exactly for position and velocity.
For dt=0.1, six steps give z=-0.350010484457016 and vz=-7.0001397132873535.
This test stubs unrelated resource lookup and does not exercise random spawning,
phase transitions, a full emitter population, rendering or scene visibility.
Evidence: `reports/menu-effects-20261103/native-reader-check.json` and
`native-motion-check.json`; instruction exports in `reports/rain-native-instructions3-20261103`.

Three new synthetic decoder tests cover complete cursor mapping, invalid extent/
version and nonfinite floats. The effect inventory now includes the decoded fields.
Next validate native spawn samples and phase boundaries, recover the effective
emitter transform and draw state, then integrate this verified behavior into Vulkan.
No guessed rain animation or original game code has been added to the runtime.
