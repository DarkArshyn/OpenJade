# BF baseline verification — 2026-10-09

Source: local execution of `tests/Test-BF.ps1` under Windows PowerShell 5.1,
using the user's GOG `POPData.BF` as the sole external input.
No external BF format specification was used.

Result: **119 checks passed**. The run covered synthetic offset and binary
content checks, empty files, malformed headers/ranges, unsafe output paths,
name collisions, command wrappers and real archive extraction.

- Real archive entries: 80.
- Extracted entries: 80.
- Extracted files checked against their source archive byte ranges: 80.
- SHA-256 matches with source ranges: 80.
- Original BF SHA-256 unchanged before/after extraction:
  `73AC4AB25DE546DE84B4FAC14CE590E30177CDF023F9576CD00D8957CA21FFCE`.

The generated JSON verification record and CSV inventory are local reports,
not source assets. The procedure is documented in the root README.

This establishes extraction integrity for this one archive. It does not
establish the semantics of its contents, support for other BF variants, or
support for the much larger `prince.bf` archive. No game execution was tested.

Text DAT/INI conversion is documented separately with byte-preservation checks.
MGM integration remains a subsequent step.
