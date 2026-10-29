# OpenJade

<p align="center">
  <img src="src/img/openjade-banner.jpg" width="100%">
</p>

## About the project

OpenJade is an independent research project aimed at reimplementing
*Prince of Persia: The Sands of Time* and the necessary Jade Engine functionality
from scratch, without Ubisoft's source code. The reference is the **PC GOG edition**.
Native Windows, Linux and macOS support is a long-term objective.
Game resources must come from your own local installation and are not distributed here.

> [!NOTE]
> Generative AI assists with research and implementation under human supervision.
> Findings and generated code are subject to testing and verification.

## Current status

**An early native menu prototype runs on Windows. The game is not playable.**

The Rust/Vulkan viewer combines decoded 3D menu scenery with an interactive main
menu. Selecting Start New Game hides the interface and plays a nine-second
Camera02 transition toward the balcony, where the camera stops. Escape returns
to the main menu. There is no controllable Prince, cutscene playback or level loading.

The scenery includes 46 decoded objects, textures, depth testing, three fog panels
and multi-pass light-fixture materials. Scene textures retain their decoded dimensions;
filtering and generated mipmaps can be compared in the viewer. Lighting, transparency ordering and visual
fidelity remain under investigation; this is not a faithful recreation yet.
The current scene still omits the sky, moon and some small effects. Named scene
lights are not yet reproduced as runtime lights; recorded vertex colors provide
part of the current appearance.

The detailed menu screens now run in the native viewer alongside the 3D scenery.
Gamma, texture filtering, window resolution and V-Sync can be changed there,
with changes applied only after Back and confirmation, plus OpenJade-owned persistence.
Profile selection and keyboard-binding editing are available; they do not load
original saves or control a playable character. Audio/gameplay and unsupported
graphics options are visibly disabled. Python is used for offline preparation
and research, not required alongside a prepared native menu.

## Prototype preview

The native prototype displays the main menu and its 3D background in one window,
with mouse/keyboard navigation, profile creation/selection, Controls, Game,
Graphics Effects/Advanced, Sound and confirmation screens. Original credits
remain an explicit notice and Load Game is unavailable. Text and widgets are
composed in Rust using locally prepared MFT/DDS resources. The logo and cursor
retain their original image dimensions, and text selects among twelve bitmap
font variants as the window grows; the interface uses linear filtering.

Captures and generated asset bundles remain local and are not included in the
repository. See the [native prototype workflow](README-dev.md#native-menu-prototype)
and the [separate Python simulation](README-dev.md#menu-simulation).

## Implemented capabilities

| Area | Available today | Main limit |
| --- | --- | --- |
| Archives | Tested BF/BIG extraction and recognized POP-LZO decoding | Not a universal archive decoder |
| Resources | MGM structure/materials, menu links, DDS and MFT previews | Selected layouts; font styling remains experimental |
| Python menu simulation | Retained as a research/reference tool | No gameplay; optional legacy gamma bridge |
| Native menu | Detailed screens over 3D scenery, four confirmed display controls, local profiles/settings and confirmations | Unsupported systems disabled; bindings stored but no gameplay |
| Camera02 | Nine-second transition sampled from decoded tracks and played by the native viewer | Baked 60 Hz poses; no original scripting runtime or gameplay trigger chain |
| Scene materials | Textures, depth, fog and multi-pass fixture blending | Original lighting, particles and exact filtering remain unresolved |
| Validation | Synthetic tests, Vulkan validation and local visual checks | Windows/AMD tested; no Linux/macOS validation |

## Roadmap

1. Improve scene fidelity: lighting, fog, filtering and transparency ordering.
2. Connect remaining menu settings to implemented game systems and refine interface fidelity.
3. Extend animation and scene/object systems beyond the baked camera transition.
4. Investigate collision, player control, cutscenes, audio and gameplay incrementally.
5. Build and validate Linux/macOS ports.

There is no completion date or reliable overall completion percentage.
See [milestones and validation criteria](README-dev.md#roadmap-and-milestones).

## Getting started

Development currently uses Windows. The native viewer requires the Rust/Vulkan
build environment and locally generated scene/menu bundles; research tools use
PowerShell and Python. Ghidra supports optional static analysis and is not required
to launch a prepared preview.

Start with the [developer setup guide](README-dev.md#getting-started), then choose
the [native menu prototype](README-dev.md#native-menu-prototype) or the
[Python menu simulation](README-dev.md#menu-simulation). A fresh checkout contains
neither original game resources nor generated bundles.

## Documentation

- [Developer guide](README-dev.md): setup, commands, tests, milestones and architecture.
- [Engine guide](engine/README.md): native viewer build and launch.
- [Format notes](docs/formats): observed layouts and local interchange formats.
- [Research observations](docs/observations): dated evidence and experiments.
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
