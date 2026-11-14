# Prince resource assembly and frozen Vulkan preview

Validated on 2026-11-13 against the local GOG resources and native draw probes.
This extends the [head fixture](2026-11-13-actor-head-preview.md) to the eleven
components observed in the initial native main-target frame. It is an isolated
frozen preview, not a controllable character or an independent animation runtime.

## Original-resource loading

`src/prince_resources.py` reads three decoded original `prince.bf` resources:

| Resource | Decoded SHA-256 | Role |
| --- | --- | --- |
| FF0C0226 | 6a2886cc69d194bbbd526184ca2a217c4575b43ffe7453fbeea2f0f151f1e7a5 | Prince, face, hair, shared skeleton and textures |
| FF030FA9 | 435657beb484850ac6c50c58dc3c78abd0e734f66ddff447bf0adbbe822d8941 | Costume geometry and materials |
| FF05C7FE | 20890d32a8715babc499a4799988d0ac7fa1537e452a0daa47867a8e39f41a9e | Weapons and accessories |

The reader preserves resource keys, offsets and payload hashes. Byte-identical
repeated records are deduplicated; conflicting payloads are rejected. Header-only
texture declarations are distinguished from full payloads. Skin records retain
inverse-bind matrices, named GAO bone bindings and packed vertex weights. The
native upload interprets the complete packed word as a float, including its low
16 vertex-index bits: clearing those bits or normalizing the weights changes the
native values. The real-data test confirms exact equality with native inputs.

Geometry contains separately indexed positions and UVs; corners are expanded only
for the local rendering package. A color-presence flag with zero color entries is
accepted for the sword instead of incorrectly consuming a vertex-sized array.
Indexed BGRA palettes, raw BGRA and the selected BC textures are decoded. Stored
small mip dimensions clamp to eight in each axis for these resources. Six base
textures are exported without resampling; native mip chains are decoded but are
not yet transported into this actor fixture.

## Observed coverage

The 24 captured main-target draws reconstruct 2,933 oriented triangles:

| Component | Geometry | Triangles rendered |
| --- | --- | ---: |
| Sword | 33001050 | 93 |
| Dagger | 057CC7F4 | 164 |
| Holder | 3F000E05 | 42 |
| Face | 13008483 | 550 |
| Body | 13008426 | 277 |
| Legs | 13008425 | 719 |
| Veil | 1300842C | 310 |
| Left/right shoulder plates | 13008427 / 13008428 | 51 each |
| Left/right sleeves and hands | 1300842A / 1300842B | 338 each |

The additional 48-triangle face group and separate 166-triangle hair mesh are
decoded and listed as unobserved in this capture. They are not forced on. Their
absence in one capture does not establish that they are unused in every state.

## Pose, lighting and material limits

`src/export_prince_preview.py` obtains positions, normals, UVs, skin weights,
indices and texture pixels exclusively from the original resources. Native
capture metadata and shader constants still supply the frozen bone palette,
object/view transforms and lighting. A common body coordinate frame assembles
all pieces without manual per-piece position corrections. The close-up camera
is diagnostic and is not the original menu camera.

The Vulkan backend adds source-over blending with depth writes (fixture blend 8),
observed on the actor's transparent overlays. These passes retain submission
order with opaque geometry; existing scene transparency modes are unchanged.
The dagger's constant-color path and captured alpha factors are retained.
The sword reflection shader is not reproduced: its original base texture and
diffuse lighting are displayed. Sword source slots 2 and 4 exceed the static
material pack; the shared base texture is independently confirmed by exact native
readback, but the original runtime slot remapping remains unresolved.

Palette and raw weapon texture readbacks match decoded pixels exactly. The BC
render-target-copy readbacks are incomplete and are not used as a pixel-parity
reference or as asset data. Full-character alpha-test state, reflection fidelity,
native mip selection, menu fog/occlusion and final pixel parity remain unverified.

## Reproduction

Use existing read-only extraction/decompression tools to prepare the three
resources locally. This command requires the private `prince-full` native pose
capture; the repository alone cannot manufacture that reference capture.

```powershell
python src/export_prince_preview.py <prince-full> reports/prince-preview-new --sources <FF0C0226-decoded.bin> <FF030FA9-decoded.bin> <FF05C7FE-decoded.bin>
```

From `engine/`, launch the prepared local sample:

```powershell
cargo run -p jade-viewer -- --scene ../reports/prince-preview-20261113/prince.ojscene --color-pipeline legacy-unorm --validation
```

An optional exporter `--yaw` changes only the diagnostic camera for another view.

## Validation

- Four synthetic tests cover packed-weight preservation, zero color entries,
  truncated geometry/texture data, invalid weighted indices and ambiguous palettes.
- `tests/integration_prince_resources.py` compares all 24 draws and 2,933 oriented
  triangles, including UVs, normals and weights: exact equality with native inputs.
  It also exports successfully after removing captured vertex/index/texture buffers,
  producing the same scene bytes.
- 60 Rust tests passed (50 assets, 10 Vulkan); ten existing private-data tests were
  skipped. New tests cover depth-writing actor passes and stable submission order.
- `tests/integration_prince_vulkan.py` checks a visible character, identical fixed-time
  frames and zero Vulkan validation errors. It does not claim original-game pixel parity.

```powershell
python tests/test_prince_resources.py
python tests/integration_prince_resources.py <prince-full> --sources <FF0C0226-decoded.bin> <FF030FA9-decoded.bin> <FF05C7FE-decoded.bin> --output <new-validation.json>
python tests/integration_prince_vulkan.py reports/prince-preview-20261113/prince.ojscene reports/prince-preview-20261113/new-validation
```

Original resources, captures, generated scene packages and images stay local and
unversioned. No original game files were modified. The next actor milestone is
original-resource pose/animation evaluation, replacing captured constants, before
integrating the Prince into the balcony scene with native lighting and fog.
