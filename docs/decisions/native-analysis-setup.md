# Native camera analysis setup

The optional native-analysis workflow uses portable **Ghidra 12.1.4** and a
64-bit **Eclipse Temurin JDK 21.0.12.1+1**. This setup was selected for static
analysis of the PC GOG x86 executable. It does not launch the game.

## Local installation

Tools are installed under `reports/native-tools/`, excluded from Git. No system
PATH or persistent JAVA_HOME setting is required. Ghidra may also create its
normal per-user preferences, symbol exports and caches in AppData.

Official archives used:

- [Ghidra 12.1.4](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build)
  (`ghidra_12.1.4_PUBLIC_20260921.zip`), SHA-256
  `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`.
- [Temurin 21.0.12.1+1](https://github.com/adoptium/temurin21-binaries/releases/tag/jdk-21.0.12.1%2B1)
  (`OpenJDK21U-jdk_x64_windows_hotspot_21.0.12.1_1.zip`), SHA-256
  `f9d6e191ab098c0d416e7d588a24420a8621cd2f4720dab2459b8b7b2d2d8b4e`.

Both archive hashes were checked against the official release metadata/checksum
before extraction. A fresh clone does not include these downloads: obtain the
archives from the official links, verify their hashes and extract them locally.
Ghidra's application metadata requires Java 21 or newer for this distribution.

REA was not installed. Its reviewed Windows documentation distinguishes main-branch
x86 support from release support; using Ghidra directly avoids that intermediary
for this task. See [REA review](../../references/rea.md).

## Run from the repository root

```powershell
.\tools\Invoke-NativeCameraAnalysis.ps1 -Path .\game\TSoT-GOG\POP.EXE -GhidraDirectory .\reports\native-tools\ghidra_12.1.4_PUBLIC -JavaHome '.\reports\native-tools\jdk-21.0.12.1+1' -OutputDirectory .\reports\native-camera-new
```

The output directory must be new and outside `game`. The wrapper verifies the
reference executable hash, copies it to the report, starts headless analysis
with a two-CPU limit and 2 GiB heap, and checks the original and copied hashes.
The Ghidra script verifies the program hash and preferred image base as well.
The automatic analysis stage has a 300-second budget; inspect logs for timeouts
and analyzer errors. A produced evidence file is not proof that every analyzer
completed. Function decompilation is separately bounded to 60 seconds per function.

The script exports references to the three diagnostic strings, enclosing
function addresses, and bounded assembly/decompiler evidence. Decompiled output
is an analysis aid, not verified source or code to copy into the independent
runtime. The listing is capped at 2,000 instructions per function.

## Output handling

Keep the executable copy, Ghidra database, logs, assembly and decompiler files
inside `reports/`. They are local research artifacts and must not be committed.
Only the independently written orchestration/export scripts and factual
observation notes belong in source control. The original game is never executed
by this workflow; OS libraries may be inspected by Ghidra while resolving imports.
