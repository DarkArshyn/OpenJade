# Palm animation: bounded first audit

Date: 2026-10-30. Source: frozen menu FF000CB9, SHA-256
`96244fe330c11acdf2a87a7c8a410225b224f5f1b9f264834425848cbf4d00eb`.

## Verified resource observations

`src/inspect_menu_palms.py` reads only the selected extracted scene and refuses
other hashes. Ten named palm objects resolve through the existing static-link
and primary-geometry readers. All ten geometry payloads report zero bones in the
currently supported metadata layout. This does not prove that the objects are
static: procedural deformation and external animation remain possible.

Seven instances (palm1, 2, 3, 4, 5, 8 and 10) have a repeated 40-byte suffix:
three words 1, 0, 25; a word 7 or 15; zero; three float candidates; two sentinel
words FFFFFFFF. These roles are deliberately not named amplitude/frequency/phase.
The candidates are approximately (0.1, 1, 0.05), except palm4 whose second value
is approximately 1.089 and palm8 with (0.15, 1, -0.05). Palm6, 7 and 9 have
other tails and are not accepted by this suffix recognizer.

All ten object payloads contain key-byte matches for 30000CE4 and 30000CE9.
Those records are named Menu3D_LUM_Ambiant.gao and Menu3D_LUM_Fog.gao;
their presence is not evidence of a wind-animation link. A separate wind.gao
exists at key 30000D35, payload size 213. No role is inferred from its name alone.
The JSON retains exact offsets, raw suffix words, mesh links and geometry counts.

## Native investigation and unresolved alignment

Read-only Ghidra examination used POP.EXE SHA-256
`6587d499f4ea6d0895179f74487045bc2c82a9d4e08a0a5046c1fb88ee3b6ec9`.
GAO loader 0067DF50 can call 00681BB0, which constructs a chained component
through 00681B50 and calls its reader at table slot +0x14. Initialization
00680C80 populates the table beginning at 00AF5A88.

Treating the raw suffix word 25 as a component type leads to reader 0069D780
and update 0069C6F0 -> 0069C280/0069C420. The latter manipulates multiple object
transforms and distance constraints. This has NOT established that the repeated
suffix is that component: the exact source cursor reaching 00681BB0 must first
be reconstructed, including compact/version-dependent layout branches.

The investigated type-27 path includes 006DA7B0 and 006DA670 -> 006E8960.
The last function computes a time-dependent vector using 006E9510/006E9440 and
an object transform. No proven connection to the ten palm instances is claimed.
No recovered native implementation is copied into the runtime or versioned code.
Local decompilation evidence remains under ignored reports/palm-*-20261030/.

## Reproduction and validation

```powershell
python src/inspect_menu_palms.py reports/menu3d-focused-4d627a9470c84b73bfc16ae467514310/FF000CB9-decoded/decoded.bin reports/palm-loader-20261030/palms.json
python -m unittest discover -s tests -p test_menu_palms.py
```

Use a new output filename: existing reports are not overwritten. Three synthetic
tests pass (offsets/signed candidate, truncation/unknown suffix, source hash).
Real-data result: ten palms, seven recognized suffixes, one wind.gao.

## Follow-up

The [compact component investigation](2026-10-30-palm-component-layout.md)
resolves the seven matching layouts as type 1, version 25. The tentative type-25
path above is superseded. Runtime palm animation remains pending.

## Next gate at the time of this initial audit

Reconstruct the exact post-color GAO cursor for palm4 and a second palm; then
identify the actual component reader and follow its update into geometry or
object matrices. Only after that should the runtime receive a deformation model.
A timed original-game recording is still needed to validate speed and amplitude.
The renderer is unchanged by this audit; palms are not animated yet.
