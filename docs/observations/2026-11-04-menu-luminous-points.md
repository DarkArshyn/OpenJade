# Luminous points in the fixed menu (2026-11-04)

The GOG menu has separate fly meshes and an additive pollen emitter. Readbacks immediately before and after each draw isolate changes in the same frame and render target at 800x600. The instrumented runs used the local research copy of the hash-verified POP.EXE. They sampled frames 20, 70 and 120. Each row below gives changed RGB pixels in that order.

| Object | GAO | Changed pixels | Binding |
| --- | --- | --- | --- |
| Menu3D_GFX_Mouches | 30000F4F | 3, 0, 2 | 54 indexed triangles, measured view origin |
| Menu3D_GFX_Mouches2 | 30000F52 | 18, 16, 18 | 54 indexed triangles, measured view origin |
| Menu3D_pollen1 | 30000D39 | 2305, 2657, 2577 | World origin (-95.225960, -1.261524, -2.198490), SRC_ALPHA/ONE |

In the second run the emitter at the pollen GAO's stored origin submitted 14, 20 and 20 quads. Its descriptor is 30000D3B, material 30000D3C and texture 2E00522D. At (386,263) in frame 20 the measured RGB changed from (52,78,95) to (182,231,255). The two other draws matching the same capacity and flags correspond to Fog3D and Fog3D2 by their distinct world origins. Both use source-over blending. Filtering only on the particle flags would misattribute fog pixels to pollen.

The supplied OBS recording was sampled near 28-31 seconds in the main menu and reduced to 800x600. Small bright variations are visible outside the measured fly patches, including the left side of the scene. The runs are unsynchronized and the video is compressed. The native draw identifies a source of the bright points; an individual OBS particle has not been matched across runs. The observations do not identify every light in the scene.

The current Vulkan export includes the two fly meshes. The [subsequent pollen capture and integration](2026-11-04-vulkan-pollen.md) connects this emitter to the native viewer. GOG evidence and the enlarged before/after crop are local under `reports/menu-fireflies-20261104`.

## Targeted vegetation inventory

All four following GAOs have geometry in the current prepared scene. Each ends in a type 1/version 25 modifier record. Plante3 (30000CBB) has flags 15, plante1 (30000CC6) has flags 7, plante2 (30000CCF) has flags 12 and liane (30000CCE) has flags 2. These records identify animation candidates. Deformed vertices and the identity of the hanging silhouette at upper right still need live validation.
