# Splash emitters and their named resource link (2026-11-04)

The eight splash GAOs listed in the [menu inventory](2026-11-03-menu-effects-inventory.md) share descriptor 2E00E1B2. The frozen menu and executable hashes are those in the [rain reader analysis](2026-11-03-rain-native-parameters.md).

The original version-23 reader consumed all 274 bytes in isolated x86 execution. It registered key B60024ED for descriptor field +0x20 through 00420BF0. The frozen container has a matching 164-byte GAO payload at record offset 1316735 named Cam_Manager.gao. At 0042EEB6 the emitter reads the resolved field and passes it to 0067D7F0. The isolated harness stubs resource registration and lookup. Its zero pointer is a harness result. The camera manager's live contribution remains open.

Stored capacity is 20, emission rate 10 per engine-time unit, spawn mode 4 and velocity mode 2. Acceleration is (0, 0, -2). Using each stored emitter matrix separately, seed 42 and dt 0.11, the original emission routine created one initial-phase particle in all eight cases. With the unresolved link the particle started at the emitter translation plus (0, 0, 0.2), with zero velocity. No falling-drop or collision input was supplied. These results establish that the isolated emitter can create a particle independently. They do not establish when the game invokes it or which transforms and velocities are used with the link resolved.

To reproduce the lookup, inspect runtime field 020 in the splash descriptor using src/probe_menu_effects.py, resolve the stored key against probe_menu3d.records, then check the registration arguments during 0042D6D0 and the argument read at 0042EEB6. The next measurement is the resolved object and its effective transform during an active splash draw.

## Live GOG birth capture

In an instrumented research copy of the verified executable, the reader registered B60024ED at field address 137D58B0. The emission probe selected this exact descriptor field. Its value at birth was 133F6680 in this run. The native calls at 0042EEBE and 0042EEC4 each returned zero in all 32 births. Thus the registered resource link was populated, while the secondary transform branch was skipped.

The probe recorded the live count directly before and after 0042EE80 and read only newly appended 48-byte slots on return. All eight emitters matched uniquely by their measured world origins. For GFX_Rain_Splash01.gao on probe frame 1, count increased from 0 to 1. World position was (-86.1698914, 0.672529459, -3.25414371) and initial velocity was (-0.587189496, -0.189040750, 0.966172814). This is one random sample. Local raw traces, the probe source and all 32 labelled vectors are in reports/splash-birth-20261104. Addresses are specific to this process.

## Reconstructing the birth vectors

A second GOG capture paired 32 newly emitted slots with the six CRT draws at the position and velocity call sites. Each draw returns an integer divided by 32767. Mode 4 samples azimuth from 0 to 2*pi, elevation from -pi/2 to pi/2, and radius from 0 to the stored 1.1. For the observed emitter basis, the center is the emitter translation plus 0.2 on world Z. The world offset is radius times (cos(azimuth)*cos(elevation), sin(elevation), -sin(azimuth)*cos(elevation)).

Mode 2 samples horizontal angle A from -0.9 to +0.9 radians, angle B from -0.9 to +0.8, and speed from the stored 1.121636987 to 1.168210983. World velocity is speed times (sin(A)*cos(B), sin(B), cos(A)*cos(B)). The comparison uses the 1024-entry sampled sine and quarter-period cosine. Maximum absolute component errors over the 32 paired births were 0.00000356 for position and 0.000000041 for velocity using the decimal trace. Local reproduction: run compare.py in reports/splash-birth-rng-20261104.

The earlier 32 births did not record their CRT draws. Their radii around the offset centers ranged from 0.003927 to 1.073749 and their speeds from 1.129930 to 1.162608, inside the decoded ranges. The paired comparison covers creation in the fixed menu. Subsequent phase appearance and draw state still require capture.

## Splash vertices and D3D9 state

The GOG draw probe captured nine frames (20-22, 120-122 and 240-242), eight splash draws per frame. The descriptor flags were 0x20149 throughout. Each 36-byte vertex contained position at byte 0, D3DCOLOR at 24 and UV at 28. The particle records and stream were sampled in the same draw callback.

| Phase | Particle observations | Example vertex ARGB |
| --- | ---: | --- |
| Initial | 107 | 0x06C4C4C4 |
| Main | 352 | 0x43808080 |
| End | 262 | 0x41565656 |

Across 4,326 submitted vertices, every quad used UVs (0,1), (0,0), (1,0), (1,0), (1,1), (0,1). The two measured half-edge lengths and the diagonal midpoint agreed with the particle sizes and center within 5.6e-7 world units. All six vertices carried the same color. The descriptor's four packed entries were 0x00E8E8E8, 0x47878787, 0x41565656 and 0x00000000. Main phase uses packed interpolation alone. Initial and end phases also apply the native five-term packed alpha scale to the interpolated alpha, preserving interpolated RGB. The reconstructed color matched every submitted vertex.

All 72 draws enabled blending with ADD, SRC_ALPHA and INV_SRC_ALPHA. Only RGB writes were enabled. Depth testing used LESSEQUAL with depth writes off. Alpha testing was off. The fog enable flag was set. Texture stage zero used MODULATE2X for RGB and MODULATE for alpha. These are captured draw settings; fog intensity per fragment was not measured.

Local raw data, per-phase example coordinates and the probe are in `reports/splash-draw-20261104`. From the repository root run python `tests/integration_splash_appearance.py reports/splash-draw-20261104` to repeat the checks.

## Vulkan integration

The exporter writes eight native matrices, descriptor controls and the 64x64 decoded texture to menu.splash. A private fixed-step simulation generates three-phase particles and builds camera-facing rectangles. The viewer uses source-over RGB blending, depth testing with writes disabled, and the existing scene fog approximation. Both the original random sequence and splash fog intensity remain unverified.

From `engine/` run:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-splash-20261104/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

Use `--no-splashes` to isolate this effect while retaining the same rain and scenery. At fixed times 0, 1 and 2 seconds the enabled/disabled images differ in 0, 48,061 and 50,566 pixels. The maximum RGB differences are 0, 39 and 39 levels. The local Rust native_splash_corners check uses OPENJADE_SPLASH_CAPTURES and OPENJADE_SPLASH_SCENE. It matches all 4,326 captured corner UVs and colors, with maximum XYZ component error 4.77e-7 in the fixed view. The GPU regression uses tests/integration_rain_vulkan.py with --effect splashes.

## Splash fog in the fixed menu

Two independent GOG runs used ForceVSFog=1 and InvertFogRange=0 or 1 in the research copy. At 72 splash draws per setting, the measured fog RGB was (52,78,95), table and range fog were off, and the vertex shader supplied the visibility factor. Both variants used camera-space vertex depth z, start 8, end 35 and strength 0.6. With InvertFogRange=0 the fraction of fog color is F=0.6*clamp((z-8)/27,0,1). With InvertFogRange=1 it is 1-F. These are fractions of source RGB before alpha blending.

| InvertFogRange | Submitted corners | Measured corner fog fraction | Largest native fog-on/off RGB difference |
| --- | ---: | ---: | ---: |
| 0 | 4,446 | 0 to 23.70% | 2/255 |
| 1 | 4,410 | 77.54 to 100% | 51/255 |

For the pixel check, eight splash draws at frame 120 were replayed individually on a black scratch target with the same depth buffer, geometry, alpha and blending. Native fog versus disabled fog changed 400 pixel/draw pairs for setting 0 and 17,785 for setting 1. Black/white fog-color controls reached differences of 6 and 81 RGB levels respectively. Random populations differ between runs. These are isolated contributions before scene post-processing, not final-screen pixel differences.

The current Vulkan splash shader already implements setting 0 with the measured color and depth curve. No adjustment was needed for the fixed view. Camera02 and per-pixel equivalence with a synchronized Vulkan frame remain unverified. Local data and measurement script are in `reports/splash-fog-20261104`. Extract both capture archives there and run `measure_splash_fog.py` from that directory to reproduce summary.json.
