# Menu pollen capture and Vulkan rendering (2026-11-04)

The isolated GOG menu emitter matches the GAO origin of Menu3D_pollen1 (30000D39), capacity 20 and flags 80001041. The probe records the active population immediately before and after the native emission routine at 0042EE80. Newly appended slots are the births. It also records the original CRT values consumed by that routine. The two fog emitters with the same flags have different origins and are excluded. Inputs are read only. Game-derived sidecars and captures remain local.

## Birth, movement and color

Across 2,609 emitter callbacks, 45 births were captured. The first particle started at (-94.829697, 1.340587, -2.020052) with world velocity (0.170698, 0.369567, 0.768928). Emission rate is 60 per engine second subject to capacity. The initial timer range is zero. Creation samples a main timer between 4 and 12, two half sizes between 1 and 2, two rectangle coordinates along local X/Z, two direction angles, speed, initial rotation and spin rate. The local Y displacement is -0.1. World speed at birth is sampled from 0.813210 to 1.0 and acceleration is zero. The particle moves on the native quantized movement clock. Its packed angle advances once per emitter update even when no motion step occurs.

The runtime uses the native packed color interpolation. Main phase goes from RGBA (146,172,191,255) toward (158,175,180,32). The end phase blends toward (149,166,191,0). No initial-phase particle was observed. End duration is sampled between 0 and 4 engine seconds. Particles draw six vertices covering the full 64x64 texture 2E00522D, in the plane facing the camera. The two sized axes rotate with the packed angle. The native cosine index uses modulo 1023. Texture color modulates vertex color at double gain, texture and vertex alpha multiply, and source-alpha/one blending adds RGB with depth testing, no depth writes and no applied vertex fog.

## Validation

The Rust optional tests replayed all 45 births using captured random inputs, 51,827 same-phase motion updates and 26 observed transitions to end phase. Maximum position component error was 7.63e-6 and velocity component error 1.20e-7. Across 106 draw calls, 1,741 main and 372 end-phase observations produced 12,678 corners. All captured UVs and RGBA bytes matched; maximum corner component error was 7.63e-6 world units.

Fixed-time Vulkan comparisons at 0, 1 and 2 seconds change 0, 12,461 and 9,705 pixels when pollen is disabled. Maximum RGB changes are 0, 95 and 72 levels after scene composition. These isolate its contribution, not an aligned original pixel comparison. The viewer uses a private random stream; ordinary presentation uses frame time for pollen and fixed-time captures use deterministic 60 Hz updates. The population is not synchronized to the original shared game RNG.

## Run and reproduce

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-pollen-20261104/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

Add --no-pollen to compare the same menu with the emitter disabled. The exporter reads the original 30000D3B descriptor and 30000D3C material and writes menu.pollen. Existing scenes without the sidecar still load. The interactive viewer does not need Python.

Extract `reports/menu-pollen-evidence-20261104/pollen-capture.zip` locally, set OPENJADE_POLLEN_CAPTURES to the extracted directory and OPENJADE_POLLEN_SCENE to the prepared scene, then run `cargo test -p jade-assets native_pollen -- --ignored --nocapture`. From the repository root run `python tests/integration_rain_vulkan.py reports/menu-pollen-20261104/menu.ojscene reports/pollen-gpu-check --effect pollen` for the GPU comparison.
