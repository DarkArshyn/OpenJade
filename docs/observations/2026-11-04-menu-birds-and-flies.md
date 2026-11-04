# Menu birds and flies in Vulkan (2026-11-04)

The GOG menu draws two bird particle emitters, three separate moving bird meshes and two fly meshes. OpenJade now renders the two particle emitters and both fly meshes. Follow-up: [mesh flight and wing deformation](2026-11-04-menu-mesh-flight.md) are now implemented and validated separately.

## Bird particle emitters

The frozen GAOs 87005402 and 87005404 bind descriptors 87005403 and 87005405. They share material 870025AC and texture 870025AD. Their capacities are 5 and 10, respectively. Spawn uses a rectangle in the emitter's local XZ plane and velocity along negative local Y. The first emitter samples two sizes. The second uses its sampled width on both axes. Acceleration, size, life ranges and effective initial transforms are exported from the native records.

The 32x32 texture contains four columns and two rows. The native update at 004309BF compares a per-particle counter to the descriptor delay (10 or 2). It either advances the cell and resets the counter, or adds engine delta times 120 and truncates the result. At the ends, tiles reverse through 0,1,...,7,6,...,0. Stepping with the recorded frame intervals reproduces the next observed tile, direction and counter in all 76 tested intervals for the first particle in each emitter. The viewer schedules simulation on its existing 60 Hz research clock, so original frame timing and random phase remain unsynchronized.

A GOG draw capture covers 78 sampled draws and 543 initial-phase particle observations. The independent Rust quad path matches all 3,258 captured UVs and vertex colors; maximum world-coordinate component error is 4.77e-7. These samples cover the first several seconds, not the complete lifetime. Both emitters use camera-oriented quads, source-over RGB blending, depth testing without writes, texture-times-diffuse-times-two and enabled fog.

## Fly meshes

Menu3D_GFX_Mouches and Menu3D_GFX_Mouches2 use mesh 30000F50 (54 triangles each), material 2E005242 and texture 2E005240 (64x64). Both scaled object origins agree with the indexed GOG draws in the fixed view. Native draws use texture factor FFE5E5E5, source-over blending, opaque diffuse alpha and fog. The active vertex shader transforms the UVs with constants c12 and c13. Its horizontal scale is 1.390625 and its vertical scale is 1. The decoded UV rates are +1.390625 and -0.0098876953125 cycles per engine second. Against timestamps for the two meshes, all ten sampled pairs of captured UV transforms agree within 0.00001 modulo one.

At fixed Vulkan times 0, 1 and 2 seconds, freezing only the two fly UV rates changes 0, 102 and 105 pixels. Maximum RGB differences are 0, 73 and 72 byte levels. This isolates the swarms' texture motion from rain, birds and other animation. For the two particle emitters, a separate enabled/disabled check changes 0, 5,442 and 5,157 pixels at those times.

## The three other birds

The native draws for the three 22-triangle mesh instances change both their transforms and local vertices. The frozen path GAOs contain next-node links, including a cycle through 30000F2F, 30000F30 and 30000F31. In the fixed capture two birds start at path node 30000F30, the third at 30000F3B. Recovering their world centers from the camera basis and the draw matrices gives speeds near 3, 4 and 5 units per second, matching the three stored values. The observed paths curve near nodes. Turning, mesh deformation and loop timing require further verification before connecting this family to the viewer.

## Run and verify

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-fauna-20261104/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

Use `--no-birds` to isolate the two particle emitters. Prepared scenes without menu.birds retain their existing behavior. The new export contains 50 scene objects before particle draws. On Windows/AMD the combined native UI and scene presented 80 smoke-test frames with zero Vulkan validation errors.

Local GOG captures are archived in `reports/menu-fauna-evidence-20261104/native-captures.zip`. Extract them to a local directory and run python `tests/integration_menu_fauna.py`. For the Rust comparison, set OPENJADE_BIRD_CAPTURES to its birds-track subdirectory and OPENJADE_BIRD_SCENE to the prepared menu.ojscene, then run `cargo test -p jade-assets native_bird_corners -- --ignored --nocapture` from `engine/`. GPU comparisons are under `reports/menu-birds-gpu-20261104` and `reports/menu-fauna-gpu-20261104`.
