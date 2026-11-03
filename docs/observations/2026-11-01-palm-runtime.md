# Menu palm deformation in the native viewer

OpenJade, 2026-11-01. Inputs are the frozen menu and executable identified
in the [component layout](2026-10-30-palm-component-layout.md).

## Native calculation

006AB5A0 advances the component phase by rate times 30 times effective frame
seconds. The two constants at 007A8E74 and 007A8FFC are 30 and float32 tau.
0041AA60 converts ticks using 007A531C (approximately 1e-6), enforces a minimum
of 1000 ticks and applies a runtime cap (initial value 0.1 seconds), time scaling
and optional overrides. The viewer uses a unit time scale and clamps the interval
between presented frame preparations to 0.001 through 0.1 seconds. Its first pose
starts at phase zero. Exact original scheduling and the startup phase still
require a timed game capture.

0079BF40 initializes the angular index scale to float32 bits 4322F983. Its
rounding bias is 3 times 2 to the power 51. The rounded index wraps over 1024
entries. 0079CEC0 multiplies an integer index by the float32 angular step at
007A8FE0 (0.006135923322290182) and passes a double to 007294B4. That routine
uses x87 FSIN. Each result is stored as float32. The portable viewer builds the
table once with double-precision sine and uses nearest-even lookup. A test covers
all entries against an independently computed table fingerprint. This comparison
uses the recovered construction rule. A live x87 table dump remains unavailable.

## Runtime geometry

The exporter checks the frozen source hash, resolves the seven supported objects
and matches each expanded corner to the original local mesh through the existing
world transform. Flags 7 use X to offset local Y and Z with a quarter-table shift.
Flags 15 combine lookups from Y and Z to displace local X. The exporter rotates
the displacement axes into world space. The renderer evaluates each corner from
its rest position and writes XYZ into the coherent vertex buffer after the
previous frame fence. Rebuilding the swapchain preserves the phase.

The local OJSCN005 package extends the v4 payload with ordered sparse records
(44 bytes each) and a trailing count. Each record identifies the expanded vertex,
quarter shift, two spatial angles, signed rate factor and two world displacement
vectors. Seven instances each contribute 648 corners. With normal effective time,
the magnitude of the angular velocity is 1.5 radians per second. Palm8 runs in
reverse. The menu UI, fog and Camera02 share the same scene package.

## Evidence

The generated package and per-object counts are under
`reports/palm-runtime-20261101/`. Native inspection outputs are under
`reports/palm-clock-20261101/` and `reports/palm-trig-20261101/`. The developer
guide documents the export and launch commands. Regression checks cover legacy
scenes, v5 extent and index rejection, reverse phase, quarter shift and the sine
table. The AMD Vulkan smoke run exercises 80 frames including resizing and
Camera02. Comparison with original-game motion remains pending.
