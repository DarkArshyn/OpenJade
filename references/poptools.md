# External reference: Swyter/poptools

Reviewed: 2026-10-09. Author: Swyter. Repository:
[Swyter/poptools](https://github.com/Swyter/poptools).
Pinned revision: `c1535e8df1e0e0a4336ba813ec041d0bc86f0ed8`
(commit timestamp 2024-08-08, retrieved from the GitHub API).

Relevant primary references:

- [POPData.BF template](https://github.com/Swyter/poptools/blob/c1535e8df1e0e0a4336ba813ec041d0bc86f0ed8/pop_data_bf.bt), internal version 2023.01.01.
- [POPData.BF extraction script](https://github.com/Swyter/poptools/blob/c1535e8df1e0e0a4336ba813ec041d0bc86f0ed8/pop_data_bf.1sc), internal version 2023.01.01.
- [BIG template](https://github.com/Swyter/poptools/blob/c1535e8df1e0e0a4336ba813ec041d0bc86f0ed8/pop_prince_bf.bt), internal version 2023.01.30.

The POPData layout corroborates the current index arithmetic. The BIG template
describes a distinct layout with numeric IDs and size-prefixed blocks; its
string-table positioning includes build-specific addresses. OpenJade uses this
as research evidence and validates the inspected ranges against local files.

The recursive tree at this revision contains no file named LICENSE, COPYING or
NOTICE. No licensing conclusion is inferred from public availability. No
upstream source file, executable or code fragment has been bundled here.

The repository also contains profile/savegame templates useful for later
research. Those have not been integrated or validated by this work. The
implemented BIG inspector does not modify executables, settings or savegames.
