# MGM resource links

Date: 2026-10-09. Implementation: `src/OpenJade.MGMLinks.psm1`. Repeatable
validation: `tests/Test-MGMLinks.ps1`. Observed dataset and counts:
`docs/observations/2026-10-09-mgm-links.md`.

## Scope and matching rules

The resolver works within one MGM document and an explicit AssetRoot directory.
No other MGM file is searched, even if it exists in that directory. The output
records static evidence, not a proven game-engine loading or scope rule.

1. Scalar MATERIAL references match material definitions by exact name in the
   same document. Duplicate exact names are ambiguous. A case-only name match
   is a candidate and never selects a definition automatically.
2. FILE leaves directly under STAGE supply texture paths. The stage's parent
   is the owner used to connect a material definition to its file declarations.
   Each stage/file produces its own edge; paths are not joined and reparsed.
3. FONT leaves match NAME declarations under Pixmap nodes directly inside FONTS.
4. A font declaration is mapped to `fonts/<name>.mft` as a **filename candidate**.
   The MFT contents have not been decoded, so the font identity is not confirmed.

Texture paths normalize separators and interpret one leading slash as relative
to AssetRoot (for example `\Texture\POP.DDS` becomes `Texture/POP.DDS`). They are
not Windows absolute paths. Drive paths, network paths, traversal and unsafe
Windows filename components are refused. Matching uses the complete relative
path, never a basename search. Case-insensitive file matches are labeled, and
multiple case-colliding matches remain ambiguous. This matters for a future
port to a filesystem with different case behavior; no renaming is performed.

The inventory includes files under AssetRoot, skips reparse points and records
skipped paths. Reparse points in AssetRoot's ancestors are refused. File
existence does not validate DDS/MFT encoding, rendering, or resource contents.

If the MGM reader emits any structural diagnostic, resolution is withheld for
the document and links are marked UncertainStructure. No hierarchy repair is
attempted. All inputs are read-only.

## Results

| Status | Meaning |
| --- | --- |
| ResolvedName | One exact local declaration; target node and offset provided |
| MissingDefinition | No local name match |
| AmbiguousDefinition | Multiple exact names; no target chosen |
| CaseMismatchCandidate | Case-only names exist; no target chosen |
| FileFound | One exact normalized relative path exists |
| CaseInsensitiveFileMatch | One path exists with different case |
| FontFileCandidate | One expected MFT filename exists; content unverified |
| MissingFile | No file at the expected relative path |
| AmbiguousFile | Multiple case-insensitive paths; no target chosen |
| UnsafePath | Resource path is outside the accepted relative-path contract |
| UncertainStructure | Structural issues prevent reliable association |

Elements without a resolved reference remain UnresolvedReference. Resolved
definitions without a file edge remain NoFileDeclaration. AttentionCount
counts unresolved/unsafe/ambiguous links and NoFileDeclaration element chains.
Zero attention does not promote FontFileCandidate to a verified font.

The tool returns Document, Summary, Links, Elements, Assets and SkippedPaths.
Link rows carry the source node and byte offset, owner node/name, target node
and offset (if resolved), file path and explicit candidates/evidence. Element
rows join reference -> declaration -> resource. Multiple stages produce
multiple rows; element names alone are not unique identifiers.

## Reports

With OutputDirectory, the tool creates the standard structural reports plus:

- `links.csv`: all name and file edges with evidence and candidate details.
- `elements.csv`: element-to-resource chains for inspection.
- `assets.csv`: available files, relative paths and lengths.
- `links-summary.json`: counts, input hash and chosen root.
- `skipped-paths.json`: inventory exclusions.
- `references.txt`: readable chains and items requiring attention.

Reports stay local in the Git-ignored reports directory. Existing destinations
are refused. Omitting OutputDirectory does not generate reports.
