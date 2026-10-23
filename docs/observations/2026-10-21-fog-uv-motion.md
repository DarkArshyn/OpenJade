# Deterministic fog UV motion

The three fake-fog panels now accept an explicit effective engine time through
`assemble_menu_scene.py --fog-time`. They share the same decoded material rate,
without advancing time once per object. This is an offline time sample, not an
interactive animation player.

## Native evidence

The executable and decoded payload hashes are unchanged from
[the native fog study](2026-10-21-native-fog-state.md). Ghidra was run with
`-readOnly -noanalysis`. Local evidence is stored under
`reports/native-fog-uv-20261021/` and is excluded from source control.

- `0043F9C0` masks each packed UV word with `0xFFFE0000` to obtain a float scale.
  It shifts the original word left 16 bits and reinterprets the bits as a float,
  then multiplies by scale. This is a bit reinterpretation, not integer-to-float
  conversion. Assembly was checked because decompiler casts are misleading here.
- Fog leaf `30000CAB` stores U=`0x3F803DA2`, V=`0x3F800000` at offsets 32/36.
  Scale is (1,1); U rate is exactly 0.0791015625 and V rate is zero.
- `0043F300` advances the shared stage accumulator by rate times `0080CBFC`.
  It uses a frame-counter nibble to avoid advancing the same stage repeatedly.
  `0068C650` can reverse direction for states 3/4/5. Only forward samples are
  implemented here.
- `0041AA60` converts the timer delta with float `0x358637BD` (approximately
  0.000001), then applies caps and time multipliers. Thus the sample parameter
  represents accumulated effective engine seconds, not guaranteed wall time.
- `0043F7C0` selects static rotation index zero for these packed words; the
  corresponding sine/cosine table values are 0/1. No rotating UVs are implied.
- `004412B0` applies the resulting affine UV transform by adding its translation.

The preview uses `u(t) = u + (0.0791015625*t mod 1)` and unchanged V, with phase
zero chosen for the diagnostic. This gives a repeat period of approximately
12.642 seconds of effective forward time. Native per-frame float rounding,
initial scene phase, rewind and timing overrides are not replayed. Modulo-one
sampling is appropriate for the verified wrapping U axis.

## Reproduction

```powershell
python -B src/assemble_menu_scene.py <decoded.bin> reports/fog-t0 --fog-time 0
python -B src/assemble_menu_scene.py <decoded.bin> reports/fog-t4 --fog-time 4
python -B src/assemble_menu_scene.py <decoded.bin> reports/fog-t8 --fog-time 8
python -B tests/test_menu_fog_motion.py
```

Each output directory must be new. The timestamp and decoded motion parameters
are recorded in `scene.json`; OBJ UVs reflect that timestamp. Camera, geometry
and all non-fog resources remain identical between samples. Local validation
outputs are under `reports/menu-fog-motion-20261021/t0`, `t4`, and `t8`.

Three new tests cover packed-field decoding and rejection, time sampling without
input mutation, invalid times, repeat period and a visible synthetic texture
shift. The existing twelve geometry/material/raster checks remain applicable.
The work does not resolve general scene lighting, exact camera framing, texture
mip selection or integration with the menu simulation.
