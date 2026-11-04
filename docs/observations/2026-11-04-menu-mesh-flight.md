# Mesh bird turns and wing deformation (2026-11-04)

The optional menu.flight package connects three 22-triangle instances to the Rust viewer. Its data comes from the verified local Menu3D container. Native captures are independent checks; the runtime does not read recorded transforms or vertex animation.

## Waypoint controller

Each mesh GAO references model 010000A6 through its eight-byte binding. Its parameter record supplies the path key, speed and turn factor at offsets 84, 88 and 92. The initial path record supplies the first waypoint. Following each waypoint's outgoing link visits three nodes and closes the cycle. Two birds share one cycle and start at 30000F30; the other starts at 30000F3B. The node records supply a center and an axis-aligned arrival box (each axis spans -1 to +1 in local coordinates).

The independent controller starts at the first node facing the next. At each update it advances the target when the bird is inside its box, moves using the previous unit heading and the stored speed, and rotates toward the target direction measured from the previous center. The angle traversed equals the remaining angle times the stored turn factor and the frame interval. The basis has negative local Y along the resulting heading and horizontal local X. This is a behavioral reconstruction from effective transforms, without running the original behavior model.

The compiled Rust controller was replayed with the measured GOG frame intervals and compared to the effective draw matrices of each instance. Each row covers 7,136 consecutive frames in the first 50 engine seconds of the fixed menu. Scale identifies each instance independently of draw order. Maximum errors are cumulative from the original node, without resetting the simulation to the observations.

| GAO | Speed | Target changes | Maximum center error (world units) | Maximum heading error |
| --- | ---: | ---: | ---: | ---: |
| 30000F2D | 5 | 18 | 0.004495 | 0.069 degrees |
| 30000F38 | 4 | 14 | 0.030645 | 0.642 degrees |
| 30000F44 | 3 | 13 | 0.004262 | 0.049 degrees |

## Local wings

The 40-byte GAO suffix identifies modifier type 1, version 25, flags 28. The original update at 006AB5A0 advances phase by rate * 30 * engine delta. For these birds rate is 0.07, so the phase advances about 2.1 radians per engine second. The expanded corners retain the original primary mesh X/Y, UV and source vertex index. Local Z receives the sum of two 1024-entry sine lookups, using phase plus local X or Y times the stored spatial factor. Both terms are weighted by amplitude times the mesh vertex's alpha byte divided by 256. The color byte here controls deformation, not the draw's opacity. The renderer applies the moving object's basis and scale after the wing calculation.

In a separate capture the first 2,000 draws of each instance supplied 396,000 submitted corners in total. X/Y and UV compared exactly. The maximum absolute local Z error against Rust was 1.20e-7 units. Native source color, 32x32 texture, MODULATE2X, opaque depth-tested draw and the viewer's normal menu fog are used.

## Run and compare

From `engine/`:

```powershell
cargo run -p jade-viewer -- --scene ../reports/menu-flight-20261104/menu.ojscene --menu ../reports/engine-ui-scale-20261029/menu.ojui --color-pipeline legacy-unorm --validation
```

Add `--no-flight` to isolate the three mesh birds while retaining the two particle emitters. The exporter writes menu.flight alongside other sidecars when given `--palm-source`. Existing scenes without the sidecar still load. The new package submits 66 additional mesh triangles. At 800x600 the measured image difference with/without mesh birds was 380 pixels at time 0 and 255 pixels at 4 seconds. At 8 and 12 seconds both images matched. The measured windows are specific to the fixed view; visibility during Camera02 has not been compared to synchronized GOG footage.

Rust workspace tests and Clippy pass. The native menu and resize smoke test presented 80 frames with zero Vulkan validation errors on the Windows AMD setup. Raw data and probe sources remain in `reports/menu-mesh-flight-evidence-20261104/flight-captures.zip`. Extract the archive locally, set OPENJADE_FLIGHT_CAPTURES to the resulting directory and OPENJADE_FLIGHT_SCENE to the prepared menu.ojscene. From `engine/`, run `cargo test -p jade-assets flight::tests -- --ignored --nocapture`. For the independent GPU test run python `tests/integration_rain_vulkan.py reports/menu-flight-20261104/menu.ojscene reports/menu-flight-gpu-check --effect` flight from the repository root.

The captured intervals establish the behavior over several turns and laps. Frame cadence changes can move a box crossing to a neighboring frame. The controller targets the menu's two three-node routes, and long-running lockstep with the original is unverified.
