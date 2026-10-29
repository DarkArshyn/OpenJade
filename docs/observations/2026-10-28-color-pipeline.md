# Color modulation, sRGB and display gamma — 2026-10-28

Historical audit snapshot. The gamma helper and live bridge were subsequently
resolved in the [gamma follow-up](2026-10-28-gamma-bridge.md); unresolved statements
below describe the earlier investigation stage.

## Scope and provenance

Static analysis of the existing executable, SHA256
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
Ghidra used `-readOnly -noanalysis`; the game was not executed or modified.
`tools/ghidra/OpenJadeColorState.java` searches indirect state/gamma calls in
`00660000..00670000` and references to defined strings containing Gamma.
This is a bounded search, not proof of absence elsewhere or of live state.
Decompiler output remains local under `reports/native-colors-20261028*`.

## Modulation audit

The current 88-pass package contains 66 passes with color selector 0, 12 with
selector 2, and 10 with selector 3. All selector-2 vertices were checked against
their material constants: RGB is doubled once at export, with shader gain 1.
Fixture stage passes use shader gain 2. No second multiplication was found in
the constant-color path. These checks do not validate the unresolved lighting
inputs of selectors 0/3. No global brightness multiplier was added.

`006696B0` selects texture color operation 5 (MODULATE2X); alpha operation is
separate. See [previous upload evidence](2026-10-21-camera-fit-gpu-upload.md)
and [Microsoft D3DTEXTUREOP](https://learn.microsoft.com/en-us/windows/win32/direct3d9/d3dtextureop).
Saturation occurs after texture/color multiplication in the current shader.

## Two diagnostic color pipelines

| Mode | Texture read / filtering | Modulation and blending | Attachment write |
| --- | --- | --- | --- |
| `srgb` (unchanged default) | sRGB RGB decoding; alpha unchanged | Linear RGB with exported color coefficients | sRGB encoding |
| `legacy-unorm` | Normalized stored values; no sRGB decoding | Stored-value RGB arithmetic | UNORM, no sRGB encoding |

Both use an explicitly selected SRGB_NONLINEAR presentation color space. This
does not itself decode shader inputs. The viewer now refuses an incompatible
surface instead of silently falling back from an sRGB attachment to arbitrary
UNORM/HDR formats. The selected format is logged on each swapchain creation.

The comparison changes filtering, modulation, blending and mip generation space
together. Use the same `--texture-filter linear` in both runs to exclude generated
mipmap content as an additional variable. UI is also in the selected color
pipeline, but its dimensions and nearest filtering are unchanged. No display
gamma ramp is applied in either mode.

Neither mode is confirmed as the original live menu pipeline. The inspected
material-state routine does not establish enabling of sampler sRGB-read or
sRGB-write. That absence in a selected function is insufficient to prove defaults
remain active throughout the frame. A live capture or a more complete initialization
trace is still required. Microsoft documents these as separate, default-disabled
states: [Gamma, Direct3D 9](https://learn.microsoft.com/en-us/windows/win32/direct3d9/gamma).
Vulkan format semantics: [Khronos formats](https://docs.vulkan.org/spec/latest/chapters/formats.html).
Sources consulted 2026-10-28.

## Original Gamma option: newly traced

- `004115E0` handles the `GammaSlider` event and calls `00414380`.
- `00414380` divides the numeric setting by the constant 100 and forwards it to
  `006633E0`.
- `006633E0` checks the fullscreen-gamma capability flag, clamps its input to
  [0,1], and constructs three equal 256-entry 16-bit ramps. The disassembly shows
  an intermediate factor 0.5, helper `0072A190`, index multiplication, factor 255,
  and saturation at 65535 before conversion. The helper's mathematical identity
  and exact rounding have not been established here; no guessed power curve is
  implemented. The initial decompiler text omits essential x87 arithmetic, so
  `gamma-instructions.txt` is the evidence for these operations.
- The device call at `006634E9`, vtable offset `0x54`, passes swapchain 0, flags 0
  and the three ramps, matching IDirect3DDevice9::SetGammaRamp.
- `00415F70` loads the `FullscreenGamma` capability from Hardware.INI.

The option therefore concerns an output ramp, separate from material modulation
and texture sRGB conversion. Whether a reference screenshot includes that ramp
depends on its capture path and active settings; this is not known.
See [Microsoft SetGammaRamp](https://learn.microsoft.com/en-us/windows/win32/api/d3d9/nf-d3d9-idirect3ddevice9-setgammaramp)
(2022-08-19, consulted 2026-10-28). No desktop/display gamma setting was changed.

## Validation and remaining work

16 Rust tests passed, including rejection of silent transfer-function changes and
HDR surfaces. Formatting and Clippy passed. Three 80-frame resize/Camera02 smoke
runs passed with zero validation errors on AMD RX 9070 XT: sRGB/linear,
UNORM/linear and UNORM/trilinear. These validate execution, not original fidelity.
The 88-pass package audit is in local `modulation-audit.json`.

Next: identify `0072A190` and conversion rounding; trace device initialization or
capture active sRGB states; compare fixed-camera images at unchanged filtering.
Lighting selectors 0/3 and transparent ordering remain separate open questions.

The user's fullscreen UI observation is also recorded: the current logo and MFT
text are baked into 800x600 page images, split into 512x512 tiles and enlarged with
nearest filtering. Increasing viewport size cannot add glyph/logo detail. A future
UI renderer should draw assets and glyphs at the target viewport size; linear
filtering alone can soften blocks but cannot restore missing source detail.
