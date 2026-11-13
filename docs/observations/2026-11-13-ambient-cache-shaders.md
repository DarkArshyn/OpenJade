# Initial actor ambient cache and material shader combination

Date: 2026-11-13

## Result and scope

The previously unresolved ambient-source link is now captured: the ambient resolution for the Prince-related components selects `Menu3D_FarahRoom_Balcony.gao`, whose runtime ambient pointer leads to `Menu3D_LUM_Ambiant.gao` and its color descriptor. This is a pointer/resource binding, not merely a matching RGB value.

Captured vertex and pixel programs also establish how normals, ambient/dynamic lighting and material textures combine. The independent arithmetic replay covers the eleven components and distinguishes an exceptional constant-color dagger pass and the sword's two-texture shader. No actor lighting or geometry is added to Vulkan in this step.

Evidence: local research capture `ambient-shader2`, original scene SHA-256 `96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`, and GOG executable SHA-256 `6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`. Native code, captured bytecode and original assets remain private and are not added to Git.

## Initial cache construction

The probe is installed when the research copy creates its graphics device. It records the two known calls to `00444410`, the four calls to ambient resolver `00443730`, and the native load registry. All identified pointer-to-resource matches are checked in the same process.

The first three private-cache construction events are:

| Event | Owner | Owner key | Private cache before | Color after |
| --- | --- | --- | --- | --- |
| 1 | Prince.gao | `CC000431` | null | `FF3B2E25` |
| 2 | Prince_Holder_WAY.gao | `3F000E2F` | null | `FF3B2E25` |
| 3 | Prince_Head_LowRes.gao | `330005EC` | null | `FF3B2E25` |

For each event, the resolver returns `003B2E25`. Its selected owner is Prince.gao and its fallback object resolves through a `0067DF50` load binding to `Menu3D_FarahRoom_Balcony.gao` (`30000CD9`). The fallback's model `+0x28` points to `Menu3D_LUM_Ambiant.gao` (`30000CE4`). That object's descriptor resolves through a `0043F120` binding to `30000CE8`, with packed color `003B2E25` at `+0x0C`.

This matches the inspected resolver path: select the fallback object's ambient source, read its descriptor color, update the ambient state and return the packed result. Private-cache construction forces the high byte to FF. The constructor also contains an inheritance path copying the private structure from the selected parent; the holder and head select the Prince as their owner. The capture establishes their initial cache colors and owner selection without claiming a separate instruction-by-instruction trace of that copy branch.

The owner's direct ambient field `+0x74` remains null. This is therefore not evidence of missing ambient lighting: the source is reached through the balcony fallback. The first Prince private-cache event already has a populated owner-level ambient value; this capture establishes private-cache allocation and source resolution, not every earlier write to every ambient field.

Together with the [previous transfer measurement](2026-11-12-actor-light-terms.md), the chain is now:

```text
Balcony fallback -> Menu3D_LUM_Ambiant -> descriptor 30000CE8
-> resolved RGB 37,46,59 -> private lighting cache +0x44
-> render context +0x850 -> vertex constant c25
```

## Vertex lighting and normals

Forty-six captured draws use five distinct vertex programs. Twenty-four draws target the 800x600 color surface and produce a diffuse color; another 22 target a 256x256 surface and do not write diffuse output. The latter are not evaluated as illuminated color passes.

Of the 24 lit draws, seven use unskinned position/normal inputs and seventeen use three-weight skeletal transforms. For the skeletal variants, three palette matrices selected by the blend indices are combined using the supplied weights; position and normal are transformed by that combination. The normal then passes through the normal transform at c8-c10 and is explicitly normalized. The unskinned variants also transform and normalize the normal.

There is no vertex COLOR input in these captured declarations. Their lit diffuse output is computed from normals and light constants; it is not multiplied by a baked per-vertex RGB field.

Let P and N denote the shader-space position and normalized normal. The RGB arithmetic is:

```text
D = ambient
  + max(dot(N, moon_direction), 0) * moon_color
  + clamp(dot(N, room_direction_to_vertex), 0, 1) * room_attenuation * room_color
  + clamp(dot(N, brasero_direction_to_vertex), 0, 1) * brasero_attenuation * brasero_color
  + max(dot(N, generated_direction), 0) * generated_color

direction_to_vertex = normalize(light_position - P)
distance = length(light_position - P)
attenuation = clamp((outer_range - distance) * inverse_range_width, 0, 1)
```

Here `direction_to_vertex` names the vector used for the vertex calculation; its actual sign is explicitly `light_position - P` (from vertex toward light). It is not an inverse-square attenuation. Room and brasero use c30/c34 for positions, c33/c37 for attenuation, and c32/c36 for color. Directional terms use c27/c28 and c39/c40; ambient is c25. No specular term or explicit final RGB clamp appears in these vertex programs. Rasterizer/output clamping is not inferred from this arithmetic replay.

## Material paths

The final color cannot be inferred from the vertex lighting alone:

| Main color draws | Observed material path |
| --- | --- |
| 22 | Fixed-function texture stage: `MODULATE2X`, texture RGB times current diffuse RGB, then doubled |
| 1 | Dagger pass: `MODULATE2X` uses texture RGB times texture-factor RGB instead of diffuse |
| 1 | Sword pass: a pixel shader mixes two texture branches using the first texture's alpha |

The dagger exception is draw 007, 55 triangles, with texture factor `F84E5257` (ARGB). Its RGB is `(78,82,87)/255`; its factor alpha is `248/255`. A lit vertex program is bound for this draw, but its computed diffuse RGB is not selected by the texture-stage color operation. This explains why receiver selection alone is insufficient to establish each pass's visible response.

For the sword pixel shader, before final pipeline clamping/composition:

```text
a = clamp(texture0.alpha, 0, 1)
RGB = 2 * ((1-a) * texture0.RGB * diffuse.RGB
           + a * texture1.RGB * K)
alpha = (1-a) * a + a * texture1.alpha
K = (64,71,74)/255
```

The vertex program generates the second texture's coordinates from the input normal and c17/c18. This distinguishes the second branch from another ordinary diffuse texture. Identifying its texture resource and checking sampled/interpolated pixels remains a separate task.

Alpha is also material-dependent on fixed-function draws: some multiply texture alpha by current diffuse alpha, others by texture-factor alpha. The measured stage states are retained in the evidence; one universal alpha rule is not assumed. Fixed-function lighting is disabled (`D3DRS_LIGHTING = 0`) for the main draws because illumination is computed in the vertex programs.

## Validation and limits

`src/replay_actor_vertex_shader.py` is independent arithmetic tooling for the small instruction subset used by the captured programs. It disassembles local captured bytecode through the Windows Direct3D compiler and executes the arithmetic without storing original shader code in the repository. It also evaluates a separately expressed lighting formula.

`tests/integration_ambient_shader.py` checks:

- Three null-to-populated private-cache transitions and the named fallback/source/descriptor bindings.
- The original scene's names and ambient descriptor color.
- Twenty-four lit draws across eleven receivers, with 2,434 referenced vertex instances (unique within each draw).
- Agreement of shader-instruction replay and the separate formula: maximum absolute RGB difference `1.444e-15` using host double precision.
- All material-path counts, the dagger factor exception, and sixteen synthetic texture/color cases for the sword pixel arithmetic.

This tiny error compares **two CPU calculations on captured inputs**, not CPU against measured GPU output. Native GPU instruction precision, vertex-output clamping, interpolation, texture sampling, fog, blending and final displayed pixels are not validated by it. The previously measured per-light pixel ablations remain separate evidence. No new whole-scene fidelity claim is made.

The probe completed and the saved research proxy was restored, with SHA-256 `e53ee384d005e9189e62b2cb4619a1e4b69c9fe0dfeb2554e2eef492fb8ab5a6`. The first capture established cache creation and shader variants; the second added the fallback-source pointer, target formats and pixel constants. Only the complete `ambient-shader2` capture is used by the integration check.

## Reproduction and next step

On Windows with Python, NumPy and `d3dcompiler_47` available:

```powershell
python tests/integration_ambient_shader.py <ambient-shader2> <Menu3D-decoded.bin>
```

Private evidence is retained under `ambient-shader2/`: events, native registry, per-draw declarations, streams/indices, shader bytecode, constants, states, and `verified-initial-cache-shader.json`.

The next bounded target is a rendered actor-component comparison using these verified equations and exact material selection, including the sword's second texture. Preserve baked scenery colors; these findings apply to the captured Prince components, not to global illumination of the menu.

## Rendered follow-up

The [frozen head preview](2026-11-13-actor-head-preview.md) applies these equations to one component and compares its Vulkan pixels with an isolated native draw. Runtime actor animation and lighting remain separate work.
