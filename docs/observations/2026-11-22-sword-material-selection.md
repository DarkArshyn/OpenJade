# Sword material-pack selection

Date: 2026-11-22

## Verified behavior

The original sword component `057CC7FF` links mesh `33001050` to material pack
`13006BC3`. The pack contains two ordered entries: `13006BBB` and `13006BBC`.
The original mesh groups request indices 0, 2 and 4.

Read-only examination of the GOG executable identifies selection at `00441830`.
For a nonempty type-4 pack and nonnegative requested index, an index above the last
available entry selects that final entry. This behavior was checked against a fresh
native capture immediately before material rendering at the `00441885` call site.

| Triangles | Original requested index | Selected pack index | Captured resource identity |
| --- | --- | --- | --- |
| 61 | 0 | 0 | 13006BBB |
| 8 | 2 | 1 | 13006BBC |
| 24 | 4 | 1 | 13006BBC |

A separate capture of the active material field at graphics context +0x88 and
same-process registry bindings agrees with all three selections. The rule is an
upper bound on the index, not modulo arithmetic or a sword-specific lookup.

## Implementation and scope

The original-resource exporter now resolves the index against the decoded pack.
The hardcoded sword material key and its unresolved-remapping warning are removed.
Export evidence retains both requested and resolved indices.

This supports the existing nonempty type-4/type-5 material inputs and nonnegative
indices. Empty packs, missing resources and negative indices remain rejected;
the native default-material fallback is not implemented by this change.
The correction does not establish compatibility with other Jade versions.

## Validation

    python tests/test_prince_material_slots.py
    python tests/integration_sword_material_slots.py CAPTURE_DIRECTORY SOURCE_MANIFEST

Three synthetic tests pass: the measured sword case, index boundaries with unrelated
resource IDs, and rejection of unsupported inputs. The integration test checks all
three captured group counts, requested indices and selected original resource keys.

Native selection log SHA-256:
`792f80b6b492076386db4865f3a271010aee37382db497eac16ca732c0ea400b`.

The new actor export was compared byte for byte with the preceding native-mipmap
package. All seven files are identical: `.ojscene`, `.actor`, `.actorlight`, `.actororigins`,
`.reflection`, `.sheath` and `.swordmips`. Only report provenance changes. No Rust/Vulkan
runtime code changed, so no new GPU performance or visual-parity result is claimed.

Private evidence:
`reports/prince-material-slots-20261122/material-selection-validation.json`.
The existing `menu-prince-mips-20261122` bundle remains valid and needs no replacement.

## Remaining work

This resolves the material-index uncertainty recorded in
[reflection integration](2026-11-17-sword-vulkan.md) and
[native mipmaps](2026-11-22-sword-mips.md).
Whole-frame GOG fidelity, other actor texture mipmaps, native startup/controller
timing and gameplay remain separate investigations.
