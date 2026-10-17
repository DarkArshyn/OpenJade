# OpenJade

## About the project

OpenJade is an independent research project aimed at reimplementing
*Prince of Persia: The Sands of Time* and the necessary Jade Engine functionality
from scratch, without Ubisoft's source code. The reference game is the **PC GOG edition**.

Native Windows, Linux and macOS support is a long-term objective.
Game data must come from your own local installation and is not included here.

> [!NOTE]
> Generative AI assists with research and implementation under human supervision.
> Findings and generated code are subject to testing and verification.

## Current status

**Research tools and an experimental menu simulation are available; the game is not playable in OpenJade.**

The Windows simulation displays ten screens in one window using extracted DDS
interface assets and MFT fonts. Navigation, settings and profiles are simulated;
profiles and settings are lost on exit. It does not execute the original game.

Separate offline 3D experiments investigate selected courtyard objects,
including the balcony, through diagnostic geometry and texture renders.
These experiments are not integrated into the menu; the original camera,
lighting, fog and complete scene behavior remain unverified.

The independent game runtime and native Linux/macOS validation remain future work.

## Prototype preview

The prototype currently provides an **800x600 menu simulation** with a neutral
background, screenshot-based layouts, controls, sliders and confirmation screens.
It is not a pixel-identical reproduction and no screenshot gallery is bundled yet.

See the [simulation description and limitations](docs/observations/2026-10-16-complete-menu-simulation.md)
and [local preview workflow](README-dev.md#menu-simulation).

## Implemented capabilities

| Area | Available today | Main limit |
| --- | --- | --- |
| Archives | Read and extract tested BF/BIG layouts; decode recognized POP-LZO envelopes | Not a universal archive decoder |
| Resources | Inspect MGM structure/materials, resolve menu links, preview DDS and MFT data | Selected formats and sample-specific interpretations |
| Menu simulation | Ten screens, navigation, session profiles, settings and confirmations | No gameplay, persistent profiles or actual hardware configuration |
| 3D research | Selected mesh/UV/material experiments and camera-linked field inspection | Offline diagnostics; original rendering and camera behavior unverified |
| Validation | Synthetic tests and recorded comparisons against local game data | Results do not establish complete format or engine coverage |

Detailed scope and evidence: [research status and validation](README-dev.md#research-status-and-validation).

## Roadmap

1. Verify the menu background's geometry, materials and camera behavior.
2. Improve menu fidelity, confirm defaults and add OpenJade-owned persistent profiles.
3. Establish a minimal independent scene runtime, then investigate animation,
   collision, audio and gameplay incrementally.
4. Implement and validate the first independent runtime on Windows.
5. Port and validate the runtime on Linux and macOS.

There is no completion date or reliable overall completion percentage.
See [milestones and validation criteria](README-dev.md#roadmap-and-milestones).

## Getting started

Use Windows, Windows PowerShell 5.1, and Python with Pillow, NumPy and tkinter.

You need your own [PC GOG game](https://www.gog.com/game/prince_of_persia_the_sands_of_time) data and a generated prototype report.
For a fresh checkout, follow the [local setup and asset preparation](README-dev.md#getting-started).

With an existing report containing `experiment.json` and `menus-assets/catalog.json`,
run from the repository root in Windows PowerShell:

```powershell
$pythonPath = (Get-Command python -ErrorAction Stop).Source
$reportDirectory = Read-Host 'Path to the generated menu prototype report'
.\tools\Show-MenuSimulation.ps1 -ReportDirectory $reportDirectory -PythonPath $pythonPath
```

Create a session profile, then navigate with the mouse or Tab/arrow keys and Enter.
Escape goes back. The original game's profiles and settings are not modified.

## Documentation

- [Developer guide](README-dev.md): setup, commands, tests, milestones and architecture.
- [Format notes](docs/formats): supported layouts and limitations.
- [Research observations](docs/observations): dated experiments and evidence.
- [Project decisions](docs/decisions) and [external research provenance](references).

## License & Legal Disclaimer

OpenJade is an independent research and reverse-engineering project.
It is not affiliated with, endorsed by, or associated with Ubisoft.
All trademarks and product names belong to their respective owners.
Prince of Persia and the Jade Engine are associated with Ubisoft.

Game data and assets are not included in this repository.
Users must obtain their own game files.

OpenJade is licensed under the GNU General Public License v3.0 or later
(GPL-3.0-or-later). See [LICENSE](LICENSE) for details.

> [!NOTE]
> This is a hobby project, and no completion date is planned at this time. Any project contributions are welcome 😊
