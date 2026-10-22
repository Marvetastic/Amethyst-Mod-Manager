# Amethyst Plus

`Marvetastic/Amethyst-Mod-Manager` is a fork of
[ChrisDKN/Amethyst-Mod-Manager](https://github.com/ChrisDKN/Amethyst-Mod-Manager), a mod manager for Linux.
Amethyst Plus tracks upstream and adds extra features on top. It is licensed GPL-3.0-or-later like upstream.

## Branches
- `main` — exact mirror of upstream.
- `plus` — default branch; upstream plus our features.
- `feature/*` — work in progress, merged into `plus` by PR.

## How it differs from upstream
- Releases come from this repo, tagged `v<upstream version>-plus.N` (AppImage only; no Flatpak/AUR).
- The in-app update check and the installer script read **this fork's** releases, so updating never swaps in upstream's build.
- CI jobs that need upstream's infrastructure (Flatpak publishing, translation sync) are disabled here.
- Plugins, custom handlers and translations still come from upstream's `Resources` branch.
- New features are listed in [CHANGELOG-PLUS.md](CHANGELOG-PLUS.md); the backlog is in [ROADMAP.md](ROADMAP.md).

## Install
This build **replaces** the official one (same app name, desktop entry and config folder `~/.config/AmethystModManager`),
so existing profiles keep working. Run:

```bash
curl -sSL https://raw.githubusercontent.com/Marvetastic/Amethyst-Mod-Manager/plus/src/appimage/Amethyst-MM-installer.sh | bash
```
or download `AmethystModManager-<version>-<arch>.AppImage` from the
[Releases page](https://github.com/Marvetastic/Amethyst-Mod-Manager/releases). Updates are offered inside the app.

If you installed upstream's Flatpak or AUR package, remove it first to avoid two entries.

## Build from source
See `CLAUDE.md` ("Build and run").
