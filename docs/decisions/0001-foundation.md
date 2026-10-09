# 0001: Research foundation

Date: 2026-10-09. Source: project owner's instructions in this conversation.

- Use Windows and Windows PowerShell 5.1 for the initial research tools.
- Preserve the game in `game/TSoT-GOG` as read-only input.
- Keep the published tools and tests self-contained. Do not include Ubisoft
  source code or game data in publication.
- Write source comments and PowerShell help in English. Use English for new
  repository documentation as an implementation choice for future publication.
- Separate modules from command scripts and tests. Avoid external dependencies
  for the initial tests so they run on the user's current environment.
- Generate synthetic fixtures in the test runner; do not commit copied assets.
- Defer runtime language and rendering choices until a concrete need exists.
- Record evidence separately from hypotheses; structural coverage does not
  demonstrate semantic understanding of a format.

The implemented scope is BF reading/extraction and Windows-1252 text DAT/INI
conversion, plus read-only MGM structural and material inspection. Rendering,
resource resolution and game behavior are not implemented yet.
Git initialization, remote publication and license selection remain pending.
