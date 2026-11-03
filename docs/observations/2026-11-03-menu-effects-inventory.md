# Focused menu effects inventory (2026-11-03)

## Verified resource links

Source: the frozen decoded Menu3D container, SHA-256
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.
Local evidence: `reports/menu-effects-20261103/inventory-resolved.json`, including absolute
record/name offsets, stored matrices, raw descriptor bytes and hashes.

| Family | Objects | Linked data |
| --- | --- | --- |
| Rain | `2E00E1AD`, `2E00E1AF` | Descriptors `2E00E1B3/B4`; material `2E005783`; texture key `2E005781` |
| Rain splashes | `2E00E1B1`, `2E00E1B5` through `2E00E1BB` | Shared descriptor `2E00E1B2`; material `2E004F14`; texture key `2E00581E` |
| Mesh birds | `30000F2D`, `30000F38`, `30000F44` | Shared mesh `30000F2E`; material `30000D90`; texture key `30000C67` |
| Named bird particles | `87005402`, `87005404` | Descriptors `87005403/405`; material `870025AC`; texture key `870025AD` |
| Flies | `30000F4F`, `30000F52` | Shared mesh `30000F50`; material pack `2E005250` |

The five effect descriptors have exactly 274 bytes and header words 11/23.
The two rain descriptors are byte-identical, not merely similar. Their word at
+8 is 150; the splash descriptor has 20, and bird descriptors have 5 and 10.
These values are deliberately not labelled particle counts, rates or lifetimes:
the native reader/update path has not been verified. Header 1/7 on mesh birds
and flies distinguishes their stored geometry from these effect descriptors.
Six separately named bird-path objects and `GFX_Flys2.gao` are also inventoried;
name and key presence alone do not prove runtime activation or path semantics.

## Limits and next step

Texture keys occur twice: a short record and a larger pixel-bearing record.
The inventory preserves both offsets and tests each with the existing bounded
texture decoder, rather than silently selecting the first matching key.
Exactly one candidate decodes for each referenced texture: rain 32x32, splashes
64x64, mesh birds 32x32 and named bird particles 32x32.
Stored matrices are preserved without assuming they are final world transforms.
No Vulkan animation is added by this inventory. Emission timing, lifetime,
velocity, random generation, visibility, blending and fog interaction require
native verification. Next trace the reader and update of the shared 274-byte layout.
Use the same native capture method as the fog-particle audit to identify actual
rain draws before implementing a deterministic runtime reproduction.

## Reproduction

```powershell
python src/probe_menu_effects.py <decoded-menu-file> <new-report.json>
python -m unittest discover -s tests -p test_menu_effects.py
```

Three synthetic tests cover unsupported source rejection, descriptor extent/header
validation and lossless preservation of unknown bytes. The real frozen resource
produces 24 selected objects and five unique effect descriptors. Inputs are read
only; output creation refuses to replace an existing report. This is a bounded
menu investigation, not a scan of all game resources.

Follow-up: the [native rain reader and update](2026-11-03-rain-native-parameters.md)
resolve the version-23 mapping and isolated movement. The unverified temporal
fields described above reflect the earlier inventory stage.
