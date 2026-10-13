# LZO1X research and independent verification

Reviewed 2026-10-13.

- Willy Tarreau (2014-07-19), updated by Dave Rodgman (2018-10-30):
  [LZO stream format as understood by Linux's LZO decompressor](https://docs.kernel.org/staging/lzo.html).
  Describes the instruction families, literal state, distances, lengths and
  end marker. The authors explicitly describe this as implementation analysis,
  not an authoritative format specification. OpenJade's original C# decoder
  implements the classic grammar; Linux's later RLE extension is unsupported.
- Markus F. X. J. Oberhumer: [miniLZO 2.10](https://www.oberhumer.com/opensource/lzo/),
  released 2017-03-01. Used as an independent local compressor and safe decoder
  for differential testing, not as an OpenJade runtime dependency.
- [FulGerNet/pop-bf-lab](pop-bf-lab.md): source of the POP framing hypothesis;
  its decoder is not used as the verification oracle.

Official archive:
<https://www.oberhumer.com/opensource/lzo/download/minilzo-2.10.tar.gz>

Published SHA-1 checked: `c7432708d49017a3f0b4f44c99d336f8a1be84f5`.
Locally measured SHA-256:
`EB4CE543AAD19533C83550746E0E9D7BCF716B35A42429E3BA17D60FA0F3E47A`.
The local archive retains its original COPYING and copyright notices; the
official project distributes miniLZO under GPL-2.0-or-later. No miniLZO source
or DLL is included in OpenJade's publishable source tree.

## Optional reference build

Extract the verified archive into a local directory under `reports`.
`tests/reference/Build-LzoReference.ps1` verifies SHA-256 values for all four
upstream compilation files before compiling them unchanged. It requires an
existing x64 MSVC compiler supplied by path. No dependency is installed or
downloaded by this script.

```powershell
.\tests\reference\Build-LzoReference.ps1 -MiniLzoDirectory .\reports\lzo-reference\minilzo-2.10 -CompilerPath 'C:\path\to\Hostx64\x64\cl.exe' -OutputDirectory .\reports\lzo-oracle
.\tests\Test-POPLzo.ps1 -ReferenceDll .\reports\lzo-oracle\oracle.dll -GameArchive .\game\TSoT-GOG\prince.bf
```

The OpenJade test bridge and minimal headers support a freestanding x64 build
without the Windows SDK or C runtime. Its static compressor workspace requires
sequential calls. Only the tests load this reference DLL. `build.json` records
source, compiler and output hashes. Users of the decoding command need only
Windows PowerShell 5.1 and its C# compilation support.
