# Text DAT / INI

Scope: Windows-1252 text files such as `pop4pclocal.dat`. A `.dat` extension
does not imply text: this tool is not a decoder for `gamepads.dat` or other
binary data.

Implementation: `src/OpenJade.TextDat.psm1`. Commands:
`tools/Convert-DatToIni.ps1` and `tools/Convert-IniToDat.ps1`.
Validation: `tests/Test-TextDat.ps1`; real inputs are optional.

The operation is a byte-preserving copy with a reversible Windows-1252 check.
It does not parse sections, edit properties, normalize whitespace, change line
endings or add a final newline. Empty files are supported. Output files must
not exist and their parent directories must already exist.

NUL bytes and UTF-8/UTF-16 BOM signatures are rejected as outside the supported
input contract. These checks do not prove that a file is text or valid INI.
UTF-8 without a BOM may also decode as Windows-1252: automatic detection is not
claimed. Save edited INI files explicitly as Windows-1252 without a BOM.

For an unedited DAT -> INI -> DAT round trip, all three SHA-256 hashes must
match. Editing text intentionally changes the resulting bytes. Game behavior
after edited data is reintroduced has not been verified; no repacking tool is
provided.
