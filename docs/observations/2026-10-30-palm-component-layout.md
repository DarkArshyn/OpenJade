# Compact palm deformation component

Date: 2026-10-30. Follow-up to the [initial audit](2026-10-30-palm-animation-audit.md).
Same frozen scene and executable hashes apply. Original inputs were read only.

## Cursor and corrected identification

For the seven uncached compact palm layouts, start at the end of the validated
instance-color array. The observed post-color sequence consumes 24 bytes:
color marker 1, FFFFFFFF, 30000CE4, 30000CE9, zero and cache sentinel FFFFFFFF.
The compact extra-object fields then consume 18 bytes (4+4+4+2+4). The component
starts 42 bytes after the color array, not at the earlier candidate word 25.

0067D8C0 and 0067DF50 provide these cursor branches; 00681BB0 reads the component
type and header flags, then invokes its reader. Type 1 resolves through
00680C80's table slot 00AF5ABC to 006ACCD0. That reader consumes 28 bytes:
version 25 followed by flags, phase, amplitude, spatial factor, phase-rate factor
and group selector. The final FFFFFFFF terminates the component chain.
Total component extent is 8+28+4 = 40 bytes.

The previous tentative type-25/constraint path was an eight-byte alignment error
and is not the palm component. Seven instances are supported: palm1, 2, 3, 4, 5,
8 and 10. The decoder rejects other flags, cache layouts, extents and nonfinite
parameters; palm6, 7 and 9 remain explicitly excluded.

## Native update

The type-1 update is 006AB5A0. It copies original positions into a working buffer
when needed, advances a phase using the stored rate factor, a native constant
and a runtime time value, and applies spatially varying lookup-table offsets.
For observed flags 7 it offsets Y and Z from X-dependent phases (with a
quarter-table offset between them). For flags 15 it adds two Y/Z-dependent
offsets to X. These branches do not require the separate wind.gao object.
The group selector is FFFFFFFF, leaving the full vertex range selected.

Stored phase is zero. Amplitude is approximately 0.1 (palm8: 0.15); spatial
factor is 1 (palm4: approximately 1.089); rate factor is approximately 0.05
(palm8: -0.05). These names describe their arithmetic roles, not verified physical
units. The native phase constant, lookup-table construction/rounding, scheduler
eligibility and relation to rendered instance transforms still need validation.
No animated runtime rendering or original-game movement parity is claimed.

## Evidence and reproduction

Read-only native evidence is under ignored `reports/palm-layout-20261030/`
and `reports/palm-component1-20261030/`. No decompiled game code is versioned.

```powershell
python src/inspect_menu_palms.py reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin reports/palm-layout-20261030/palms.json
python -m unittest discover -s tests -p test_menu_palms.py
```

Four synthetic tests cover cursor/type/version, offsets, signed rates, malformed
extent, unknown type, nonfinite input and source rejection. The real report keeps
both the historical raw-suffix observation and the anchored component decode.
Next: verify the phase constants and lookup table, then validate a sampled local
deformation before transferring it into the renderer.
