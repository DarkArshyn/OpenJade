# Prince source skeleton and diagnostic runtime animation

Validated on 2026-11-14 using original PC resources and local native palette captures.
This extends the [frozen assembly](2026-11-13-prince-resource-preview.md).
It is an isolated diagnostic, not a playable Prince or complete native actor system.

## Independent evidence

The source bundle hashes are recorded in the preceding observation and each export
manifest. `130035F0` lists 62 bone GAO keys. Local transforms, parent links, inverse
bind matrices and packed weights are read from the original resources. Row-vector
hierarchy evaluation composes `local * parent_world`; skin matrices compose
`inverse_bind * bone_world`. Weights retain their packed float values.

`2D000AD4` contains 37 bounded transform tracks occupying the complete 4,838-byte
payload: 34 bone rotation channels, pelvis translation and two actor-root channels.
Quaternions use signed 16-bit components divided by 32768. Translation keys contain
three floats. Per-key durations establish sampling times; they are not assumed to
be uniformly spaced. The selected controller spans 20 track units. The standalone
preview evaluates 35 body channels and excludes the separate actor-root channels.
Untracked joints retain their resource-local transforms.

Native validation reconstructs bone world matrices from captured palettes and
source inverse binds, then removes parent transforms to compare local rotations.
Across eleven sampled frames, the 34 primary bone rotations match this clip with
fitted-phase RMS below 0.0000874 in matrix components. Shared bone world matrices
across costume components differ by at most 5.61e-8. Fitted phase progresses at
approximately five track units per second over the 1.69-second observation.
This is a fitted comparison, not proof of the active action descriptor or looping.
The earlier camera-track timebase must not be applied blindly to actor playback.

The facial component's resource-local transform followed by the head bone matches
the first native attachment matrix within 1.5e-6. Its separate facial skeleton is
kept neutral from resource transforms; gaze and expression controllers are absent.
Shoulder plates follow their named parent bones. The sword attachment is independently validated below; the support joints are validated below. The dagger remains omitted pending its secondary sheath controller.

## Implementation and scope

`src/prince_animation.py` decodes the selected encoding and evaluates the hierarchy.
`src/export_prince_animation.py` prepares an `OJACT001` sidecar containing local
bones, decoded keys and inverse-bind-space vertex influences. This is OpenJade's
private interchange design, not a claim about the original runtime's structures.
The original skin weights are not renormalized. The Rust reader checks bounds,
finite values, parent cycles, unique channels, ordered key times and vertex bindings.

`engine/crates/jade-assets/src/actor.rs` evaluates keys and skinning on the CPU at
absolute elapsed time. The Vulkan upload uses the existing frame fence before
writing positions. It does not replay captured pose matrices or baked frame arrays.
The diagnostic repeats the selected clip every four seconds; native action selection,
blending and loop semantics remain unverified. No new architecture or dependency
on historical engine source was introduced.

The initial package rendered eight components and 2,634 triangles; the sword update
rendered nine components and 2,727 triangles. The support update renders ten components and 2,769 triangles. The older eleven-part
frozen package remains available for reference. This is intentionally not represented
as a complete replacement of every captured subsystem:

- Secondary clothing controllers are missing; their resource-local transforms are used.
- Facial expression and eye motion are missing.
- Dagger is excluded; sword reflection and material-slot remapping remain unresolved.
- RGB lighting and draw states still derive from the frozen native diagnostic capture.
  Animated normals are not yet used to recompute lighting.
- Scene integration, collision, gameplay and native action selection remain absent.

## Source sword attachment

The original `3F000E3C` (`b_Holder_Snap_to.gao`) local matrix, composed with
`130035BE` (`B_Pr_Bip Spine2.gao`) world space, reproduces the sword object matrix
in all eleven palette samples. Maximum matrix-component error: 2.5938e-6.
The holder object root also matches Spine2 (maximum error 2.9807e-6), and its internal joint transforms are established separately below. These are observed composition
relationships, not a claim that the source GAO parent field directly names Spine2.

The exporter applies the source snap matrix to original sword geometry and binds
each vertex rigidly to Spine2. No fitted attachment offsets or captured pose matrices
are exported. The existing Rust skeletal evaluator needs no special weapon code.
This is the sheathed state seen in the measured sequence, not draw/sheath gameplay.

## Support joints and dagger orientation

The original holder list `3F000E2C` contains six bones. Its action bank points to
four short clips. Evaluating `3F000E32` at its initial time reproduces all four
visible skin matrices across eleven native samples, with maximum component error
4.3518e-6. The other three candidate clips do not match this observed pose.
`src/prince_attachments.py` evaluates this hierarchy from original resources;
the exporter skins the support locally and attaches it to Spine2. This validates
the observed sheathed pose, not general holder action selection.

The dagger requires a proper half-turn around `(1, -1, 0)` before the original
snap transform `130046A1`. In row-vector notation its rotation rows are
`(0,-1,0)`, `(-1,0,0)`, `(0,0,-1)`. This is an observed initialization operation,
not a rotation stored in the dagger GAO and not a reflection.

A write watch on the research executable records the attachment-basis write at
`0x00474DA5`, reached from `0x004F2AA3`. Combining this independently measured
basis with the source snap matrix and the captured sheath bone `130035EE`
reproduces eleven dagger object matrices within 1.52e-5. The parent bone still
receives secondary deformation not reproduced by the current source evaluator.
Therefore the helper is tested but the dagger is deliberately not exported yet.

Private evidence is retained in the local `prince-dagger-local-writes` probe
outputs and `reports/prince-holder-animation-20261114/attachments.json`.
No historical Jaded or Rayman 4 implementation was used for this reconstruction.


`tests/integration_prince_attachments.py` reproduces the eleven-pose matrix check:

```powershell
python tests/integration_prince_attachments.py $nativeCapture reports/prince-holder-animation-20261114/attachments.json --sources $sources
```

The prepared local package is `reports/prince-holder-animation-20261114/prince.ojscene`.
It passes the seven-time Rust/Python position comparison (maximum error 4.7684e-7).
Vulkan captures at 0 and 2 seconds are stable at each fixed time and have no validation
errors. Sword reflection remains absent; this is not final material or pixel parity.

## Reproduction and tests

From the repository root, with the same decoded sources and capture metadata as the
frozen preview (set `$sources` to those three decoded bundle paths):

```powershell
$env:PYTHONPATH = 'src'
python src/export_prince_animation.py $capture reports/prince-animation-20261114 --sources $sources
python tests/test_prince_animation.py
python tests/integration_prince_animation.py $nativeCapture reports/prince-animation-20261114 reports/prince-animation-20261114/native-comparison.json --sources $sources
python tests/integration_prince_vulkan.py reports/prince-animation-20261114/prince.ojscene reports/prince-animation-20261114/check-2 --seconds 2
```

The native capture argument expects the named `*-bindings.txt`, `*-draws.bin` and
`*-clock.bin` files from the local palette probe. These captures and all game assets
remain outside Git. The integration test also writes `prince.poses` for a seven-time
Python/Rust comparison; it is validation evidence, not an animation input.

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/prince-animation-20261114/prince.ojscene --color-pipeline legacy-unorm --validation
cargo test -p jade-assets -p jade-render-vulkan
$env:OPENJADE_ACTOR_FIXTURE = (Resolve-Path ../reports/prince-animation-20261114/prince.actor).Path
cargo test -p jade-assets actor::tests::source_pose_parity -- --ignored --nocapture
```

Results: four Python unit tests; 65 ordinary Rust tests passed, 11 private-fixture
tests ignored by default; the actor's explicit private-fixture parity test passed.
Its maximum position difference from the Python evaluator is 4.7684e-7 across
0, 0.5, 1, 1.7, 2, 3 and 4 seconds. Four Vulkan captures at 0, 1, 2 and 3 seconds
show different poses, stable repeated frames at each fixed time and no validation
errors. These checks establish evaluator consistency, not original-game pixel parity.
