"""
ll_update_checker.py
Check installed Lovers Lab mods for newer versions.

Same shape as the Thunderstore checker, but with no API: each distinct file
page is fetched one at a time with a pause between requests, and the whole
batch stops at the first Cloudflare/captcha/login wall so the site is never
hammered. A page whose version can't be read is reported ``unknown``, never
as an update.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional

from LoversLab.ll_meta import now_stamp, read_meta, write_meta
from LoversLab.ll_page import PageBlocked, open_fetcher
from Nexus.nexus_update_checker import _version_is_newer
from Utils.app_log import app_log
from Utils.mods.metadata import locked_meta_write

REQUEST_DELAY = 2.0   # seconds between page requests


@dataclass
class LoversLabUpdateInfo:
    mod_name: str = ""
    file_id: int = 0
    installed_version: str = ""
    latest_version: str = ""
    has_update: bool = False
    unknown: bool = False      # page unreadable / no version found
    blocked: bool = False      # site challenged us; check was cut short
    page_url: str = ""


def scan_installed(staging_root: Path) -> list:
    """Every staging folder carrying ``[loverslab]`` metadata."""
    out: list = []
    staging_root = Path(staging_root)
    if not staging_root.is_dir():
        return out
    for folder in sorted(staging_root.iterdir()):
        meta_path = folder / "meta.ini"
        if not folder.is_dir() or folder.is_symlink() or not meta_path.is_file():
            continue
        try:
            meta = read_meta(meta_path)
        except Exception:
            continue
        if meta.file_id > 0:
            out.append((folder, meta))
    return out


def check_for_updates(staging_root: Path, *,
                      only_names: Optional[Iterable[str]] = None,
                      save_results: bool = True,
                      progress_cb: Optional[Callable[[str], None]] = None,
                      installed_mods: Optional[list] = None,
                      stop: Optional[threading.Event] = None,
                      delay: float = REQUEST_DELAY,
                      fetcher=None) -> list:
    """Check Lovers Lab mods in *staging_root*; returns one info per mod."""
    subset = set(only_names) if only_names else None
    installed = scan_installed(staging_root) if installed_mods is None else installed_mods
    if subset is not None:
        installed = [(f, m) for f, m in installed if f.name in subset]

    stop = stop or threading.Event()
    owns_fetcher = fetcher is None
    fetcher = fetcher or open_fetcher(stop)
    lookups: dict = {}          # file_id -> FileInfo | None | "blocked"
    results: list = []
    try:
        for folder, meta in installed:
            info = LoversLabUpdateInfo(
                mod_name=folder.name, file_id=meta.file_id,
                installed_version=meta.version, page_url=meta.page_url)
            results.append(info)
            if meta.file_id not in lookups:
                if stop.is_set() or "blocked" in lookups.values():
                    lookups[meta.file_id] = "blocked" if "blocked" in lookups.values() else None
                else:
                    if lookups:
                        _pause(delay, stop)
                    if progress_cb:
                        progress_cb(f"checking {meta.name or meta.file_id}")
                    try:
                        lookups[meta.file_id] = fetcher.file_info(meta.page_url)
                    except PageBlocked as exc:
                        app_log(f"loverslab: {exc}")
                        lookups[meta.file_id] = "blocked"
                    except Exception as exc:
                        app_log(f"loverslab: could not check {meta.file_id}: {exc}")
                        lookups[meta.file_id] = None
            found = lookups[meta.file_id]
            if found == "blocked":
                info.blocked = info.unknown = True
                continue
            if found is None or not found.version:
                info.unknown = True
                continue
            info.latest_version = found.version
            info.has_update = bool(meta.version) and _version_is_newer(found.version, meta.version)
            muted = meta.ignore_update or (
                meta.ignored_version and meta.ignored_version == found.version)
            flag = info.has_update and not muted
            if save_results:
                try:
                    meta.latest_version = found.version
                    meta.has_update = flag
                    meta.last_checked = now_stamp()
                    if found.name and not meta.name:
                        meta.name = found.name
                    write_meta(folder / "meta.ini", meta)
                except Exception as exc:
                    app_log(f"loverslab: could not save update state for {folder.name}: {exc}")
            if muted:
                info.has_update = False
    finally:
        if owns_fetcher:
            fetcher.close()
    app_log(f"loverslab: checked {len(installed)} mod(s), "
            f"{sum(r.has_update for r in results)} update(s) available")
    return results


def _pause(seconds: float, stop: threading.Event) -> None:
    deadline = time.monotonic() + seconds
    while not stop.is_set() and time.monotonic() < deadline:
        time.sleep(0.1)


@locked_meta_write
def set_ignore_update(meta_ini_path: Path, ignore: bool) -> None:
    meta = read_meta(meta_ini_path)
    meta.ignore_update = ignore
    if not ignore:
        meta.ignored_version = ""
    meta.has_update = False if ignore else meta.has_update
    write_meta(meta_ini_path, meta)
