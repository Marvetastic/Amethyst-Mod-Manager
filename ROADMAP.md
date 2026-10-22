# Roadmap

## Ideas
Based on open upstream issues and the codebase (numbers refer to `ChrisDKN/Amethyst-Mod-Manager`):
- **Native Wayland option** (#671): setting to run on native Wayland instead of forced XWayland (`QT_QPA_PLATFORM=xcb` in `src/run_qt.sh`), with a fix/workaround for the NVIDIA OpenGL failure.
- **r2modman / Gale / Thunderstore profile import and export** (#684), building on `src/Thunderstore`.
- **Merge mod INI files** when a mod is replaced by a new install (#683).
- **Use `unrar`/system extractor fallback for RAR archives** (#707).
- **Register as the `nxm://` handler** and offer Amethyst in the "open Nexus links with" chooser (#704).
- **Steam overlay when launching games** through Amethyst (#720).
- **New game support**: Prey (2017) + Mooncrash (#716), Spore (#639) — new modules under `src/Games`.
- **Plus about/version badge** showing the `-plus.N` version and a changelog link in Settings.
- **Update-channel toggle** for the fork (stable plus releases vs. follow-upstream notice).
- **Upstream-sync status check** (CLI helper that reports how far `plus` is behind `main`).

## Planned

## In progress
- **Lovers Lab source, phase 1** (`src/LoversLab`, branch `claude/modest-pascal-xybla8`): `[loverslab]` meta, link-to-page, update check. Still to do: update flag in the modlist, link archives from the downloads folder by file id.
- **Lovers Lab source, phase 2** (blocked on reading LL's terms on automated access): "Add from URL" with automatic download via the existing `Utils/loverslab` client.

## Done
- Fork infrastructure: independent releases, updater and installer repointed, upstream-only CI guarded.
