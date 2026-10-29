# Gamma ramp and Python-to-Vulkan bridge — 2026-10-28

## Native calculation

The hash-checked executable and Ghidra read-only workflow are the same as the
[color audit](2026-10-28-color-pipeline.md). `OpenJadeGamma.java` exports bounded
math instructions and constants; evidence stays in `reports/native-gamma-20261028*`.
No original executable code is included in the runtime implementation.

For the integer slider value `s` in 0..100:

1. `g = float32(s / 100)` and `x = float32(g * 0.5)`.
2. `gain = float32(exp(double(x)))`.
3. For each index `i` in 0..255, compute `float32(gain * i * 255)` with the
   intermediate extended arithmetic observed before the final float store.
4. Clamp to 65535, truncate toward zero, and store the same 16-bit result in R/G/B.

The exponent identification follows `0072A190 -> 007348F8`: its reduction constant
is `92.33248261689366 = 64/log(2)`, followed by split `log(2)/64` reduction,
a 64-entry power-of-two table and binary exponent reconstruction. This is an
exponential implementation, not a power applied separately to each pixel value.
`00726DF4` converts the bounded nonnegative result with truncation correction.
The x87 fallback dispatch is present; its full CRT implementation is not copied.
The independent implementation uses the standard-library exponential. Exhaustive
bit parity against both original CRT paths has not been executed.

At s=0, the ramp is `i*255`, so its final entry is 65025, not 65535. The engine
keeps that observed factor rather than replacing it with 257 to force identity.
At s=100, gain is approximately 1.64872122; index 128 yields 53814 and high values
saturate. Tests cover every slider value for monotonicity, black and saturation.
Zero is the screenshot/simulation baseline; the original factory-default path
has not been independently traced.

## Correct placement in the renderer

The scene and UI render to an intermediate attachment. A second subpass reads
the composed image and applies the 256-entry ramp, with linear interpolation
between entries. It runs after opaque, alpha, additive and UI blending.
For the sRGB path, RGB is encoded to stored/display values before ramp lookup,
then decoded before the final sRGB attachment write. UNORM uses stored values
directly. Alpha is unchanged. OS/monitor gamma is never modified.

This emulates the output ramp locally; actual hardware ramp interpolation,
driver calibration and screenshot capture behavior may differ. It is not a claim
of whole-scene color parity. Without --gamma or --settings the pass bypasses
the ramp, preserving the diagnostic default. The extra attachment is viewport-sized
and recreated on resize. The single-frame fence protects its reuse and uniform updates.

## Live bridge and transactions

`--settings PATH.ojsettings` connects Python and Rust using an OpenJade-owned
ASCII file, version `OJSET001`, then preview and committed integer values on
separate lines. Both values are strictly 0..100; input is bounded to 64 bytes.
Python atomically replaces the file only on changes. Rust polls every 100 ms,
keeps the last valid value on read/parse errors, and reports the failure.
The preview is the displayed value; the committed value survives Python restarts.

The existing Python Graphics Gamma slider now exposes 101 values (0.00..1.00).
Moving it previews immediately. On leaving:

- Yes commits the preview.
- No restores the committed value and updates Vulkan.
- Cancel keeps the pending preview and stays in the settings screen.
- Default Settings previews zero; it is committed only with Yes.
- Normal Python exit restores the committed value for the connected viewer.

Only gamma is connected. Other Python settings remain simulated. The native
Options page is not replaced by the Python controls; the two windows form a
research control/viewer workflow. Run Python first so a previous pending preview
is reset to the committed value before launching Rust. One Python writer per file.
The file is ignored by Git and rejected under the game directory.

## Validation

- 19 Rust tests, including strict parsing, the zero ramp, and all 101 monotonic ramps.
- Three Python synthetic tests cover invalid input, commit/discard/default/reload,
  and refusal to replace an unrelated file.
- Complete Python ten-screen smoke passed with the bridge enabled.
- End-to-end test called the actual Python UI handlers and observed Vulkan logging
  previews 100 -> 0 -> 42 -> 0, including Cancel, No, Yes and Defaults. The 80-frame
  resize/Camera02 test completed with zero validation errors.
- Explicit gamma=100 smoke passed in both sRGB and UNORM; bypass/checker passed.
- Formatting and Clippy passed. Game data and desktop gamma were not changed.

Local evidence: `reports/engine-gamma-20261028/integration.json` and `integration.log`.
Reproduce with `python -B tests/integration_gamma_bridge.py` after building jade-viewer
and preparing the documented local scene/UI reports. This integration test requires
Windows, Tk and a working Vulkan device; it is not a portable unit-test fixture.
