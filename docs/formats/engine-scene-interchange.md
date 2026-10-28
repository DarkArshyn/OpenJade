# Local engine scene interchange

This is an OpenJade research bridge, not an original Jade file format. The Python
converter consumes an existing common-space `scene.obj`, `scene.json`, material
PNGs and the initial pose from a transition `poses.json`. It reads these inputs
without changing them. No native executable or proprietary code is required at runtime.

## Version 1 (initial import)

All integers and floats are little-endian. No padding:

| Offset | Field |
| --- | --- |
| 0 | Eight bytes `OJSCN001` |
| 8 | Four u32: expanded vertex count, texture width, height, array layers |
| 24 | Thirteen f32: eye XYZ, right XYZ, up XYZ, forward XYZ, vertical FOV degrees |
| 76 | Vertex count records of nine f32: world XYZ, native UV, diagnostic RGB, texture layer |
| after vertices | Width * height * layers * 4 bytes of RGBA8, layer-major |

Triangles are expanded in groups of three vertices. A triangle must reference one
integer texture layer. The reader requires an exact byte extent, finite numbers,
an approximately orthonormal camera basis, valid FOV and bounded sizes (256 MiB,
one million vertices, 2048 per texture dimension, 128 layers). The backend also
checks the device's image dimension and layer limits.

The converter reverses the existing export's `1-v` OBJ convention. World vertices
and diagnostic colors remain unchanged. Camera axes are `-basis[0]`, `basis[2]`,
`-basis[1]`, matching the research raster's horizontal correction. Vulkan projection
negates view Y, uses positive forward depth and maps the chosen near/far planes
(0.1/1000, research settings) into [0,1]. The vertical FOV stays constant on resize;
horizontal coverage changes with the viewport aspect ratio.

Textures are resampled to 512x512 array layers, nearest sampling, repeat UV, no
mipmaps. sRGB texture sampling and the sRGB swapchain perform the color conversions.
The current shader multiplies sampled linear RGB by the exported diagnostic colors
and discards alpha below 0.5. This does not establish the original lighting model.
Depth testing/writing use LESS; raster culling is disabled. A shared depth image is
safe only with the current single-frame-in-flight fence discipline. Resources are
rebuilt on resize for now, including static uploads; caching is future work.

The converter excludes whole objects with fog, multi-stage materials or omitted
groups, and records the reasons and source hashes in `manifest.json`. The tested
local package contains 40 objects, 14,994 triangles and 31 texture layers. Three fog
panels, both hangfire objects and lampions are excluded. The captured scene is not
the finished main menu: no UI overlay, animated camera, particles, audio or gameplay.

Run `python -m unittest discover -s tests -p test_export_engine_scene.py` from the
repository root and `cargo test --workspace` from `engine/`. The bridge tests check
XYZ/color retention, UV/camera convention, source mismatch and overwrite rejection;
the Rust tests check malformed packages and the depth projection endpoints.

## Version 2: material passes

`OJSCN002` preserves the version-1 header/vertices/pixels, then adds a u32 draw
count and 48-byte records: first vertex, count, blend mode, depth-write flag (four
u32), followed by eight f32 (UV scale XY, UV offset XY, alpha, RGB gain, cutoff,
sampler). Modes 0/1/6 mean opaque/source-over/SRCALPHA additive. Only opaque draws
write depth. Equal depth is allowed so overlay passes survive their base pass.
Samplers 0/1/2 select nearest repeat, linear repeat or linear wrap-U/clamp-V.
The reader validates exact sequential coverage, bounds and supported state pairs.

`export_engine_materials.py` includes all 46 objects, 15,674 geometric triangles,
16,226 submitted triangles, 88 passes and 38 textures. Fog is sorted by object
center and drawn last. A fixed `--time` sample selects decoded UV offsets; no
continuous fog/fixture animation is currently replayed. The first version's
exclusions above are historical. Whole-scene lighting fidelity remains unresolved.

## Menu bundle and runtime playback

`OJUI0001` is a local UI/camera bundle produced by `export_engine_ui.py`. Its five
pages have bounded button rectangles/action IDs, one normal plus hovered image
per button, and 76 512x512 RGBA tiles. Four tiles reconstruct each 800x600 frame
without rescaling the source layout. A final table contains 541 camera poses of
13 f32 each at 60 Hz, generated from the hash-checked native-derived sampler.
The parser checks dimensions, bounds, finite camera values and agreement with the
scene's initial pose before appending UI textures/vertices in memory.

The native menu draws its overlay last with depth disabled and source-over alpha.
Rendering and pointer coordinates share a centered 4:3 viewport. Start New Game
hides the overlay, advances the baked pose index over nine seconds and holds the
last pose. Escape restores the initial camera/menu. The detailed settings/profile
simulation is not part of this native UI yet. This is not a general UI layout engine
or native track interpreter. Neither .ojscene nor .ojui contains code from the game;
both contain game-derived data and must remain local and excluded from Git.
