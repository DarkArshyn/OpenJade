# MGM: observed structure (initial specification)

Status: research model, not a complete Jade Engine specification. Date:
2026-10-09. Evidence: `docs/observations/2026-10-09-mgm.md`, generated reports,
`src/OpenJade.MGM.psm1` and `tests/Test-MGM.ps1`.

## Bytes and tag candidates

The reader retains the complete input as `Document.Bytes`, including bytes
outside recognized nodes. It scans a one-byte-to-one-character Latin-1 mapping
for `<NAME>`, `</NAME>` and `<NAME/>`. Names follow
`[A-Za-z_][A-Za-z0-9_:\-.]*` and matching is case-sensitive. Attributes,
whitespace inside tags, entities and general XML syntax are not interpreted.
Other alphabetic angle-bracket candidates produce diagnostics; literal text
can also resemble such a candidate. This reader does not prove a file is XML.

Each token has its byte Offset, Length and exclusive EndOffset. Opening nodes
are linked by ParentIndex and Depth. Self-closing nodes are complete without
being pushed onto the open-node stack. They have an empty content range and
no separate closing tag (`ClosingOffset = -1`, `ClosingLength = 0`).

On a mismatched closing tag, the reader records a diagnostic and leaves the
stack unchanged. Remaining open nodes are reported at end-of-file. Following
parent relationships reflect that unrepaired stack, not a recovered hierarchy.
`Closed` means a matching pair or self-closing tag was recorded; it does not
validate all descendants or establish semantic correctness.

## Raw text and values

For a closed node, RawText is the complete observed byte range (tags included),
mapped reversibly as Latin-1. This is not a claim about the file's text encoding.
Length and EndOffset describe that range. For an unclosed node, Length is zero
and EndOffset equals Offset; RawText contains only the opening tag and
RawTextEndOffset identifies its separate, observed end. No end is guessed.

Leaf Value trims only NUL, tab, LF, CR and space from the content edges.
Container values are not flattened. Use RawText or Bytes for exact evidence.

## Materials

All uppercase MATERIAL nodes are inspected, regardless of their parent.

| Model | Classification rule | Additional properties |
| --- | --- | --- |
| MaterialDefinition | Direct NAME or STAGE child exists | StageCount, Files, Regions, BlendOps |
| MaterialReference | No child and a non-empty scalar value | None |
| MaterialUnclassified | Neither rule applies | None |

Each model preserves Name, Offset, EndOffset, Length, RawText,
RawTextEndOffset, Closed, NodeIndex, Parent and ParentIndex. Definition names
use the first direct NAME child. Stage fields come only from direct children
of that definition's direct STAGE nodes, joined with ` | ` for display. The
node table retains individual fields. Material names and texture paths are
observed strings; references are not resolved or validated against resources.

## Concrete observations

In the verified `pop4common.mgm`, offset 0 opens PACKAGE. Direct leaf nodes
include NAME at offset 12 (value `POP4Common`), VERSION at 38 (`4.1`) and
PAGESIZE at 63 (`640 480`). These are stored values, not confirmed runtime
semantics. A MATERIAL definition spans [108,260), with a FILE leaf at offset
174. The self-closing FONTSUBST spans [2964,2976). All offsets are decimal.
The source hash is recorded in the observation document.

## Reports and limitations

`Read-MGM.ps1` returns an in-memory document. With OutputDirectory it also
writes summary.json, diagnostics.json, tags.csv, nodes.csv, materials.csv and
structure.txt to a new directory. Empty tables retain column headers. CSV raw
text can contain newlines or control characters; structure.txt escapes scalar
values for readability. Tree indentation is capped at 40 levels, while actual
Depth and ParentIndex remain in the node table.

The reader does not render menus, decode textures/fonts, infer actions,
resolve material references, rewrite MGM or claim that all bytes are understood.
The separate resource-link tool provides explicit local name/path matching;
see `MGM-resource-links.md` for its evidence rules and limitations.
Large inputs are loaded into memory; raw strings for nested nodes duplicate
some data. Tests currently cover the three supplied menu MGM files and
synthetic edge cases, not every Jade Engine game or format variant.
