# Local engine scene interchange (version 1)

This is an OpenJade research bridge, not an original Jade file format. The Python
converter consumes an existing common-space `scene.obj`, `scene.json`, material
PNGs and the initial pose from a transition `poses.json`. It reads these inputs
without changing them. No native executable or proprietary code is required at runtime.

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
