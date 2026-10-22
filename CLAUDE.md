# Amethyst Plus — standing rules for Claude

This repo is `Marvetastic/Amethyst-Mod-Manager`, a long-lived fork of
`ChrisDKN/Amethyst-Mod-Manager` ("Amethyst Plus"). Python 3.12 + PySide6 (Qt 6)
app with a Rust extension (`native/amethyst_filegraph`) and libloot (maturin).
Read `FORK.md` (what the fork is) and `ROADMAP.md` (backlog) when relevant.

## Remotes and branches
- `origin` = `Marvetastic/Amethyst-Mod-Manager`, `upstream` = `ChrisDKN/Amethyst-Mod-Manager`.
- `main` mirrors upstream exactly. **Never commit to `main`.**
- `plus` is the integration branch (the fork's default branch) holding all our work.
- `feature/<short-name>` branches hold work in progress; they branch from `plus`
  and merge back into `plus` through a PR on the fork.
- **Never push to upstream. Never force-push `plus`.** PRs always target
  `Marvetastic/Amethyst-Mod-Manager` base `plus` (use `gh pr create -R Marvetastic/Amethyst-Mod-Manager --base plus`).
- Git identity is set repo-locally (Marvetastic, GitHub noreply address). Don't change global git config.

## Start of every session: sync upstream
```bash
gh repo sync Marvetastic/Amethyst-Mod-Manager -b main
git fetch origin
git checkout main && git merge --ff-only origin/main
git checkout plus && git pull --ff-only origin plus
git merge main          # resolve conflicts, then rebuild (see below) and test
```
Keep conflict resolutions minimal. When a new upstream version lands, reset the
fork suffix to `.0` for the next release (e.g. `2.5.6-plus.0`). Push `plus` with a
normal push after the merge.

## Feature workflow
1. `git checkout plus && git checkout -b feature/<short-name>`
2. Implement, rebuild, launch the app and actually test it.
3. Commit after every coherent step (conventional commits: `feat:`, `fix:`, `ci:`, `docs:`, `refactor:` ...).
4. Push and open a PR into `plus` on the fork. **Wait for the user's approval before merging.**
5. Update `ROADMAP.md` (move the item) and `CHANGELOG-PLUS.md` as part of the feature.

## Code rules
- Keep changes minimal and localized to upstream files; prefer **new modules** over
  edits to existing ones, so upstream merges stay easy. Hook into upstream code with
  the smallest possible call site.
- The app is GPL-3.0-or-later; keep the license and source available.
- Fork identity lives in few places: `_APP_UPDATE_REPO` in `src/Utils/github/app_updates.py`,
  `REPO=` in `src/appimage/Amethyst-MM-installer.sh`, and workflow guards
  (`github.repository == 'ChrisDKN/Amethyst-Mod-Manager'`). Don't spread it further.
- `src/version.py` stays at upstream's version. CI stamps the fork version from the tag.
- **Never commit secrets, tokens or API keys.**
- The Nexus API key lives in the OS keyring, not in files.

## Build and run (Pop!_OS 24.04, local only; no system install)
One-time prerequisites (already done on this machine): apt packages
`python3-venv python3-dev meson ninja-build libxcb-cursor0 unzip git`, and Rust via rustup
(`export PATH=$HOME/.cargo/bin:$PATH`).

```bash
export PATH=$HOME/.cargo/bin:$PATH
bash native/amethyst_filegraph/build.sh                      # -> src/amethyst_filegraph.abi3.so
CARGO_BUILD_JOBS=2 RUST_MIN_STACK=67108864 bash src/LOOT/rebuild_libloot.sh 0.29.6   # -> src/loot.cpython-312-*.so
meson setup builddir --prefix=$PWD/.local-install            # first time only
meson compile -C builddir && meson install -C builddir       # packaging check, installs to .local-install/
```
- libloot 0.29.6 is the tag the Flatpak pins. The default rustc build segfaulted at full
  parallelism on this machine; `CARGO_BUILD_JOBS=2` + `RUST_MIN_STACK` fixed it.
- Rebuild the two `.so` files only after a fresh clone or when `native/` or the libloot tag changes (they are gitignored).

Run the GUI from source (uses `./.venv`, forces XWayland/xcb, installs PySide6 on first run):
```bash
src/run_qt.sh
```
CLI: `python3 -m cli` from `src/` (see `amethyst-mod-manager-cli`).

**Caution:** this fork *replaces* the official app on this machine (same app name and
config `~/.config/AmethystModManager`, same data under `~/Games/Amethyst`). Running from
source uses the user's real profiles, so don't test destructive actions (deploy/restore,
delete) on real games without asking.

## Release (always ask the user first)
**Never tag or push a release without explicit approval.** Version = upstream version +
`-plus.N` (e.g. `v2.5.5-plus.1`).
```bash
git checkout plus && git pull --ff-only origin plus
git tag v<upstream>-plus.<N>
git push origin v<upstream>-plus.<N>
gh run watch -R Marvetastic/Amethyst-Mod-Manager      # pick the "Build Release Artifacts" run
gh release view v<upstream>-plus.<N> -R Marvetastic/Amethyst-Mod-Manager
```
The tag triggers `.github/workflows/release.yml`, which builds the AppImage (x86_64; aarch64 is
best-effort) and publishes a normal (non-prerelease) GitHub release, so `/releases/latest`
(used by the in-app updater and installer) resolves to it. Flatpak, GitHub Pages publishing,
translation sync and Crowdin jobs are skipped on the fork. Then add the entry to `CHANGELOG-PLUS.md`.
Install command for users: see `FORK.md`.
