# Amethyst Plus changelog

Releases of this fork only. Upstream's history is in `Changelog.txt`.
Versions are `<upstream version>-plus.<N>`; N resets to 0 on each new upstream version.

## Unreleased
- Removed the Lovers Lab source added in 2.5.5-plus.1 (link/open/update-check menu). Existing `[loverslab]` sections in mods' `meta.ini` are now ignored and harmless.

## 2.5.5-plus.1 (2026-10-22)
- Lovers Lab as a mod source (phase 1): right-click **Lovers Lab Actions** to link an installed mod to its file page, open it, and check for new versions. Rate-limited, stops at the first site security check. No automatic downloading yet.

## 2.5.5-plus.0
- Fork infrastructure: releases, updater and installer point at this fork; upstream-only CI jobs are guarded.
