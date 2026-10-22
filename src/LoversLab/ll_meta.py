"""
ll_meta.py
Read and write LoversLab metadata in a mod's ``meta.ini`` [loverslab] section.

Lovers Lab has no public API, so a mod is identified only by the numeric id in
its file-page URL (``/files/file/6192-lets-dance-again/``). The slug can change
on the site; the id cannot, so ``fileId`` is the identity and ``slug`` is just
a cosmetic hint for building the page URL::

    [loverslab]
    fileId = 6192
    slug = lets-dance-again
    name = Let's Dance Again
    version = 1.2
    installed = 2026-10-22T12:00:00
    latestVersion = 1.3
    hasUpdate = true

Lives in its own section so it never collides with the Nexus ``[General]``
section or the ``[thunderstore]`` section; like those, unknown sections are
preserved on write.
"""

from __future__ import annotations

import configparser
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from Utils.app_log import app_log
from Utils.atomic_write import atomic_writer
from Utils.loverslab import is_loverslab_url
from Utils.mods.metadata import locked_meta_write, read_meta_ini

SECTION = "loverslab"
_PAGE_RE = re.compile(r"^/files/file/(\d+)(?:-([^/]*))?(?:/|$)")


@dataclass
class LoversLabModMeta:
    """LoversLab metadata for a single installed mod."""

    mod_name: str = ""          # folder name in staging
    file_id: int = 0            # numeric id from /files/file/<id>-<slug>/
    slug: str = ""              # url slug (cosmetic; may change on the site)
    name: str = ""              # title shown on the file page
    version: str = ""           # version the user has installed
    installed: str = ""         # ISO-8601 timestamp
    latest_version: str = ""    # newest version seen by the update checker
    has_update: bool = False
    ignore_update: bool = False
    ignored_version: str = ""
    last_checked: str = ""      # ISO-8601 timestamp of the last successful check

    @property
    def page_url(self) -> str:
        return file_page_url(self.file_id, self.slug)


_KEY_MAP: dict[str, str] = {
    "fileId": "file_id",
    "slug": "slug",
    "name": "name",
    "version": "version",
    "installed": "installed",
    "latestVersion": "latest_version",
    "hasUpdate": "has_update",
    "ignoreUpdate": "ignore_update",
    "ignoredVersion": "ignored_version",
    "lastChecked": "last_checked",
}
_BOOL_FIELDS = {"has_update", "ignore_update"}
# Stamped once at link time; a caller building a fresh meta to flip one flag
# must not blank them (same guard as the Nexus/Thunderstore writers).
_NEVER_BLANK = {"file_id", "slug", "name", "installed", "version"}


def parse_file_url(url: str) -> tuple[int, str]:
    """``(file_id, slug)`` from a Lovers Lab file-page URL, or ``(0, "")``."""
    url = (url or "").strip()
    if not is_loverslab_url(url):
        return 0, ""
    match = _PAGE_RE.match(urlparse(url).path)
    if not match:
        return 0, ""
    return int(match[1]), (match[2] or "").strip()


def file_page_url(file_id: int, slug: str = "") -> str:
    if file_id <= 0:
        return ""
    tail = f"{file_id}-{slug}" if slug else str(file_id)
    return f"https://www.loverslab.com/files/file/{tail}/"


def read_meta(meta_ini_path: Path) -> LoversLabModMeta:
    """Parse the [loverslab] section; missing keys default."""
    _, cp, _ = read_meta_ini(str(meta_ini_path))
    meta = LoversLabModMeta(mod_name=meta_ini_path.parent.name)
    if not cp.has_section(SECTION):
        return meta
    for ini_key, attr in _KEY_MAP.items():
        raw = cp.get(SECTION, ini_key, fallback=None)
        if raw is None:
            continue
        if attr == "file_id":
            try:
                meta.file_id = int(raw)
            except ValueError:
                pass
        elif attr in _BOOL_FIELDS:
            setattr(meta, attr, raw.strip().lower() in ("true", "1", "yes"))
        else:
            setattr(meta, attr, raw)
    return meta


@locked_meta_write
def write_meta(meta_ini_path: Path, meta: LoversLabModMeta) -> None:
    """Write the [loverslab] section, preserving every other section."""
    cp = configparser.ConfigParser()
    if meta_ini_path.is_file():
        try:
            cp.read(str(meta_ini_path), encoding="utf-8")
        except configparser.Error as e:
            app_log(f"loverslab write_meta: tolerating malformed "
                    f"{meta_ini_path}: {e}")
    if not cp.has_section(SECTION):
        cp.add_section(SECTION)
    for ini_key, attr in _KEY_MAP.items():
        value = getattr(meta, attr, None)
        if value is None:
            continue
        if attr in _BOOL_FIELDS:
            cp.set(SECTION, ini_key, "true" if value else "false")
            continue
        if attr in _NEVER_BLANK and not value:
            continue
        # '%' is configparser's interpolation sigil.
        cp.set(SECTION, ini_key, str(value).replace("%", "%%"))
    meta_ini_path.parent.mkdir(parents=True, exist_ok=True)
    with atomic_writer(meta_ini_path) as f:
        cp.write(f)
    app_log(f"Wrote loverslab meta.ini: {meta_ini_path}")


@locked_meta_write
def remove_meta(meta_ini_path: Path) -> None:
    """Drop the [loverslab] section (unlink the mod from Lovers Lab)."""
    cp = configparser.ConfigParser()
    try:
        cp.read(str(meta_ini_path), encoding="utf-8")
    except configparser.Error:
        return
    if cp.remove_section(SECTION):
        with atomic_writer(meta_ini_path) as f:
            cp.write(f)


def is_loverslab_mod(meta_ini_path: Path) -> bool:
    return meta_ini_path.is_file() and read_meta(meta_ini_path).file_id > 0


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
