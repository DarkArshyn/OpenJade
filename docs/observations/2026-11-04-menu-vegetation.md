# Plants and the hanging vine (2026-11-04)

The four GAOs have local geometry already present in the menu scene. Their compact type 1, version 25 suffixes control a local vertex wave. The export now adds these controls to the existing OJSCN005 animation stream. Older packages remain usable. Re-export the full scene to obtain the additional controls.

| Object | Key | Flags | Local motion | Submitted corners compared | Max world component error |
| --- | --- | ---: | --- | ---: | ---: |
| Menu3D_Plante3 | 30000CBB | 15 | X from two spatial waves driven by Y and Z | 11,520 | 1.53e-5 |
| Menu3D_plante1 | 30000CC6 | 7 | Y and Z in quadrature, driven by X | 12,960 | 7.63e-6 |
| Menu3D_plante2 | 30000CCF | 12 | Z from a temporal wave modulated by the sum of X and Y spatial waves | 17,856 | 7.63e-6 |
| Menu3D_liane | 30000CCE | 2 | X and Z in quadrature, driven by Y | 5,394 | 7.63e-6 |

The branch arithmetic follows the original update at 006AB5A0. For flag 12 the displacement is twice the stored amplitude times sine(phase) times the sum of the two spatial sine lookups. The vine's native uniform scale is applied to its displacement as well as its base geometry. Captured local positions were transformed using the effective GOG draw matrices and compared to the prepared controls at the measured frame intervals. Corner UVs agree exactly in all compared draws. Repeated passes and frames count as separate observations.

Two before/after GOG readbacks identify the upper-right silhouette. The hanging foliage is the eight-triangle material 30000CAF, exported as material-15.png. Its final draw changed 22,305 pixels on probe frame 24, including 9,934 pixels at x>=500, y<200 in the 800x600 image. On frame 96 the corresponding counts were 22,552 and 10,126. The other 42 triangles of the vine use material 30000C95. These readbacks establish draw ownership in the fixed view.

In Vulkan, freezing only the four new phase rates gives identical images at time zero. Motion changes 179,651 and 192,740 pixels at one and two seconds respectively after scene composition. This checks animated output separately from the existing palms, particle effects and camera. It does not establish exact GOG pixel matching.

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-vegetation-20261104/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

The complete menu presented 80 smoke-test frames with zero Vulkan validation errors. Local evidence is in `reports/menu-vegetation-evidence-20261104` and `reports/menu-vegetation-gpu-20261104`. Extract vegetation-captures.zip locally and run `python tests/integration_menu_vegetation.py <prepared-menu.ojscene> <extracted-plant-motion-directory>` from the repo root. The comparison covers sampled frames in the fixed menu. Other foliage records and Camera02 remain outside this measurement.
