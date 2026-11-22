# Generated directional light during Camera02

Date: 2026-11-17

## Result

The generated directional contribution is not fixed during the menu-to-balcony
transition. Its RGB stays at `(64,64,64)/255`; its world direction changes with
the owner's position relative to the render-context camera reference. The three
selected named lights remain moon, room and brasero throughout this capture.

This verifies the native calculation and GPU constants. The Vulkan actor still
uses its captured generated direction: no runtime change is included here.

## Experiment and provenance

The local GOG research copy was launched with a bounded observation proxy. New
Game was activated through the original menu; the balcony view and movement hint
were observed. No original installation resource was modified. Executable SHA-256:
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.

The completed `light-camera02b` capture contains 3,025 receiver samples over 275
sampled frames, eleven components and 12,626 draws. Samples are taken every 30
presented frames, not at an assumed fixed frame rate. The captured native delta
clock provides sample times. The initial `light-camera02` attempt did not produce
a completed transition capture and is excluded.

The probe records the input/output of `00444270`, owner translation, context
reference at `+0x184`, local/GPU transforms, shader constants, selected lights and
same-session load bindings. Original code and private binary captures are not
published. The research proxy was restored, verified SHA-256:
`e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`.

## Verified calculation

The input is `normalize(owner_position - context_reference)`. Applying the
[previously measured positive-polar-angle formula](2026-11-12-actor-light-terms.md)
with the captured float32 pi azimuth offset and 0.3-radian polar angle reproduces
the native direction. Only the input's horizontal heading affects the result.
The direction is then transformed to receiver-local coordinates, transformed to
shader coordinates and normalized; c39 contains the result and c40 its color.

| Check | Maximum absolute component error |
| --- | --- |
| Owner/reference difference and normalization vs native input | 1.140e-7 |
| Independent angle formula vs native output | 1.757e-7 |
| World-to-local transfer | 2.980e-8 |
| Local-to-shader transfer vs c39 | 1.326e-7 |
| Constant RGB/W vs c40 | 1.485e-8 |

The render-context reference moves from approximately
`(-83.58902, 1.38866, -2.66195)` to `(-92.80204, -0.96494, 3.93218)`.
These endpoints agree with the independently decoded Camera02 endpoints to less
than 4e-5 per component. One tracked receiver has 36 intermediate samples from
native elapsed time 36.541 through 45.310 seconds; the first endpoint sample is
45.554 seconds. These times include the wait in the main menu, not animation
timestamps measured from a captured activation event.

For that same receiver, world directions are:

| Pose | X | Y | Z |
| --- | --- | --- | --- |
| Fixed menu | 0.28190631 | 0.08866202 | 0.95533651 |
| Balcony endpoint | 0.27747089 | 0.10169583 | 0.95533651 |

Their angular separation is approximately **0.788845 degrees**. A frozen initial
direction can therefore differ from the native result. For a unit normal, the
isolated diffuse RGB-channel error is bounded by
`(64/255) * length(direction_end - direction_start) = 0.00345546`.
This is a mathematical upper bound before material multiplication, clamping,
fog and composition, not a measured final-pixel difference or average brightness.

Same-process registry resolution verifies the selected GAOs `30000CE2`,
`30000CF4`, `30000D57` for all 3,025 samples. Selection alone does not prove their
final-pixel contribution; the earlier fixed-menu pixel ablation remains separate.

## Limits and next integration

- The reference used in the verified formula is captured directly. Reconstructing
  a camera origin by inverting the captured transform product differs by up to
  0.007932 scene unit. That discrepancy has not been resolved; it is not hidden
  in the direction-error measurement.
- Final samples return to the initial reference. The cause of this return was
  not traced; the measured outward transition and stable endpoint precede it.
- There is no Camera02 final-pixel ablation, arbitrary-camera validation, or
  proof of a rule for other polar angles or degenerate horizontal directions.
- This task changes tests/documentation only. No new Vulkan timing benchmark is
  claimed because the runtime and its prepared packages are unchanged.

Next, supply the current camera reference and actor position to the runtime
generated-light calculation, preserving the source-derived named lights. Validate
the coordinate convention and compare the resulting directions against this
capture before measuring rendering performance again.

## Reproduction

```powershell
python tests/integration_camera02_generated_light.py <light-camera02b> <output.json>
```

The test checks the numeric comparisons, eleven receivers, complete sample/draw
counts, unchanged named-light selection and a nonzero transition. The output
includes binary evidence hashes and per-sample values. Private evidence is kept
under `reports/camera02-generated-light-20261117/light-camera02b/`.

## Runtime follow-up

The [runtime integration](2026-11-17-camera02-runtime-light.md) now recalculates the direction from the active camera and validates its effect on final Vulkan pixels. Individual receiver origins and GOG final-pixel parity remain open.
