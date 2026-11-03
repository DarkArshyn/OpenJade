# Native rain geometry, UV and phase appearance (2026-11-03)

Follow-up to [live emitter state](2026-11-03-rain-live-state.md). Captures use the
same isolated GOG copy, verified executable and original menu. No installation
resource is modified. The observer reads GPU buffers during rain callbacks and
snapshots their particle/descriptor data. Captures are at marker-relative frames
20-22, 120-122 and 240-242, not video frame numbers or synchronized timestamps.

## Verified geometry

18 draws contain 767 particle observations: 42 initial-phase, 635 main-phase and
90 end-phase. These may include the same particle at successive frames. All
4,602 submitted corners match the independent reference exactly, as do UVs and
packed vertex colors. Source: ignored `reports/rain-appearance-20261103`.

Native `0042C000` uses basis helper `0042BA50`. For the observed rain flags,
geometry uses emitter X and Y axes, unlike spawning which uses X and Z.
The stored/live Y axis is (0,0,-1), making each rain quad vertical in world XZ.
There is no camera-facing billboard rotation in this verified branch.

For center P, half-width vector U and half-height vector V, corners are
P-U-V, P-U+V, P+U+V, P+U-V. The two submitted triangles are 0,1,2 and 2,3,0.
UVs are respectively (0,1), (0,0), (1,0), (1,1); no animated atlas is selected.
The GPU stride is 36 bytes: XYZ at 0, declared normal at 12, D3DCOLOR at 24,
UV at 28. The active vertex shader declares but does not consume the normal;
its uninterpreted buffer contents must not be used for lighting.

## Phase-dependent appearance

Let r=remaining_duration*inverse_phase_duration. Native descriptor colors are
packed RGBA bytes, later red/blue-swapped into D3DCOLOR. Captured endpoints are:

| Endpoint | RGBA bytes |
| --- | --- |
| Initial | (1,1,1,0) |
| Main start | (222,229,235,223) |
| Main end | (224,231,237,222) |
| End | (0,0,0,0) |

Initial phase interpolates initial -> main start with t=1-r and multiplies both
half-sizes by t. Main phase interpolates main end -> main start with t=r and keeps
size unchanged. End phase interpolates end -> main end with t=r and also keeps
size unchanged. Thus initial emergence grows the geometry and increases color/
alpha; disappearance fades color and alpha without shrinking this rain branch.

`00441D90` is not ordinary floating-point lerp. It selects packed shifted-byte
terms using float bits after adding 49152, with endpoint thresholds approximately
0.02 and 0.98. The seven-term approximation can darken intermediate values even
when endpoints are equal. `packed_lerp` preserves this behavior; comparisons to
original x86 interpolation and GPU bytes agree for all captured particles.

## Actual GPU combination

Follow-up state captures show stage 0 COLOROP=MODULATE2X, COLORARG1=TEXTURE,
COLORARG2=DIFFUSE; ALPHAOP=MODULATE with the same argument sources. Stage 1 is
disabled and no pixel shader is bound. The active vertex shader passes diffuse
color and UV through unchanged. It computes oFog, but fixed-function fog is
disabled in the observed draw state; the presence of oFog alone is not evidence
that fog is applied to these particles.

Therefore source RGB is clamped `2*texture.rgb*vertex.rgb`; source alpha is
`texture.a*vertex.a`. Blending is SRC_ALPHA/ONE with RGB-only writes and no depth
write. Alpha from the texture and phase both matter. This is not a claim of
pixel-exact Vulkan rendering: sampler/rasterization and final scene composition
will still need a rendered comparison.

## Reproduction and scope

```powershell
python -m unittest discover -s tests -p test_menu_rain_appearance.py
python tests/integration_rain_appearance.py reports/rain-appearance-20261103
```

Four synthetic tests cover packed interpolation, initial-size scaling, UVs and
unsupported flags. The integration comparison checks all captured corners and
requires coverage of all three phases. Original game data and shader binaries
remain local; source control contains only independent code and documentation.

The first capture completed but proxy restoration briefly failed because Windows
still held the DLL; the research process was stopped and the previous proxy was
restored with matching SHA-256. Later capture launchers retry restoration. The
original installation was untouched throughout.

Next: integrate the verified rain branch into Vulkan with deterministic research
seeds, then compare fixed-time captures. A deterministic seed is not proof of the
original shared RNG phase; exact cross-engine temporal synchronization remains open.
