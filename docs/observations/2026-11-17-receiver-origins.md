# Generated-light receiver origins

Date: 2026-11-17

## Native observation

The [Camera02 capture](2026-11-17-camera02-generated-light.md) identifies three
owners for eleven rendered components using same-process registry bindings:

| Receivers | Owner | Origin used for generated lighting |
| --- | --- | --- |
| Nine components, including sword and dagger | Prince.gao, CC000431 | Actor root |
| Prince_Holder_Body.gao, mesh 3F000E05 | Prince_Holder_WAY.gao, 3F000E2F | Spine2, source bone 130035BE |
| M_Pr_Face.gao, mesh 13008483 | Prince_Head_LowRes.gao, 330005EC | Head, source bone 130035C0 |

The sword and dagger must not use their attachment positions for this calculation:
their native lighting owner is the Prince root. Conversely, skinning influence
weights do not define the lighting owner of the support or face.

The original inverse-bind matrices and source binding keys recover the relevant
bone matrices from the captured shader palettes. Comparing their translations
after root placement to the separately captured owner positions gives:

| Relationship | Samples | Maximum absolute coordinate error |
| --- | --- | --- |
| Prince root | 2,475 | 3.734e-6 |
| Holder owner = Spine2 | 275 | 5.806e-6 |
| Head owner = Head | 275 | 5.958e-6 |

Shared palette reconstruction differs by at most 9.324e-8 between draws. Swapping
Head and Spine2 produces errors above 0.235 scene unit; the two relationships are
distinguishable. These are measured attachment relationships, not a claim that
the owners' GAO parent fields directly contain these links. Their standalone GAO
translations are template positions and are not substituted for runtime origins.

`tests/integration_receiver_origins.py` repeats this comparison using the original
resource bundles and private native capture. Its report records hashes and resource
offsets. Historical engine sources were not used.

## Runtime and packaging

The exporter writes an optional `.actororigins` sidecar. Bone indices come from
the original skeleton list: the current package uses index 3 (Spine2) for 126
expanded vertices and index 5 (Head) for 1,650; 7,023 retain the root owner.
The sidecar is copied to `menu.actororigins` during assembly.

The existing evaluated skeleton supplies the animated origins each frame. The
renderer computes one direction per distinct origin (three here), then selects
the corresponding term per vertex. Geometry, normals, material colors and the
other lights remain unchanged. Missing sidecars preserve previous root behavior.
Unplaced isolated actors retain captured light directions as before.

The bounded loader rejects wrong counts, truncated/trailing data and out-of-range
bones without replacing an already valid mapping. Synthetic tests cover animated
bone movement, unchanged geometry, source-list indices and root-owned weapons.

## Rendering and performance

At diagnostic animation time 2 seconds, 938 vertex RGB values change, with maximum
absolute channel difference **4.3988228e-5**. The runtime test confirms that root
receiver colors and all vertex positions remain identical.

The final 800x600 balcony images at animation times 0, 2 and 3.983333 seconds are
byte-identical with and without individual origins. Each fixed-time capture is
also repeatable. Thus the CPU correction is measured, but there is **no measurable
final-image change in these three samples**. Visibility, material response and
quantization are not separated by this test. This is not proof of zero effect in
all poses, nor GOG final-pixel parity. All captures report zero Vulkan errors.

Four 1,800-frame endpoint runs (800x600, FIFO, validation, no screenshot layer,
30 warmup frames excluded) compare identical scenes except the origin sidecar:

| Mode/run | Frame median / p95 ms | Simulation median / p95 ms | GPU median / p95 ms |
| --- | --- | --- | --- |
| Common root 1 | 5.591 / 11.413 | 0.718 / 0.884 | 0.313 / 0.335 |
| Individual 1 | 5.569 / 11.436 | 0.724 / 0.877 | 0.314 / 0.337 |
| Individual 2 | 5.594 / 11.412 | 0.724 / 0.887 | 0.310 / 0.334 |
| Common root 2 | 5.592 / 11.441 | 0.731 / 1.136 | 0.312 / 0.331 |

No material slowdown is apparent in these runs; they do not establish statistical
equivalence. All 7,200 frames completed without Vulkan validation errors.
The workspace passes 75 ordinary tests; 15 private tests are ignored by default.
The new private package test and two Python mapping tests pass; Clippy passes.

## Use and remaining scope

```powershell
cd engine
cargo run -p jade-viewer -- --scene ../reports/menu-prince-light-origins-20261117/menu.ojscene --menu ../reports/menu-fixtures-20261110/ui/menu.ojui --color-pipeline legacy-unorm --validation
```

This command requires the newly prepared local package. Older exports are not
rewritten automatically. Future actor exports include the optional mapping.

```powershell
python tests/test_prince_light_origins.py
python tests/integration_receiver_origins.py <light-camera02b> <actor-manifest.json> <output.json>
```

The validation establishes the origin relationships on native palettes, not
complete animation synchronization: runtime origins follow OpenJade's diagnostic
body clip. General action selection and final GOG composition remain unresolved.
The next independent visual target is the sword's reflection/material path, or a
controlled comparison of complete GOG and Vulkan final composition.
