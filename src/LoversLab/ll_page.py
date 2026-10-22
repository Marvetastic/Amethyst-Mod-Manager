"""
ll_page.py
Fetch and parse a Lovers Lab file page for its title and version.

There is no API, so this reads the public page HTML. Every extraction is a
best-effort heuristic and may return "" - callers must treat an empty version
as *unknown*, never as "up to date" or "has an update".

Built on the existing Wabbajack client (``Utils.loverslab.client``) for its
session handling, login and Cloudflare/captcha detection; nothing there is
modified.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from Utils.loverslab.client import LoversLabClient, _Page
from Utils.wabbajack.http import DownloadUnavailable

_VERSION_TOKEN = r"v?(\d[\w.\-+]*)"
_TITLE_VERSION_RE = re.compile(r"\s" + _VERSION_TOKEN + r"$", re.IGNORECASE)
_JSONLD_RE = re.compile(r'"softwareVersion"\s*:\s*"([^"]+)"')


class PageBlocked(DownloadUnavailable):
    """Cloudflare / captcha / login wall: stop hitting the site."""


@dataclass
class FileInfo:
    name: str = ""
    version: str = ""


def parse_file_page(page: _Page) -> FileInfo:
    """Extract ``name`` and ``version`` from an already-parsed page."""
    name, version = "", ""

    # The page <h1> carries the title, and in IPS Downloads the version is
    # usually a child element of it.
    for h1 in page.root.elements("h1"):
        spans = [s.text() for s in h1.elements("span") if s.text()]
        full = h1.text()
        if not full:
            continue
        if spans and full.endswith(spans[-1]) and _looks_like_version(spans[-1]):
            version = spans[-1].lstrip("vV ").strip()
            name = full[: -len(spans[-1])].strip()
        else:
            name = full
        break

    # Structured data, when the site emits it, is the most reliable source.
    match = _JSONLD_RE.search(page.html)
    if match:
        version = match[1].strip()
    else:
        for node in page.root.elements():
            if (node.attrs.get("itemprop") or "").lower() in {"softwareversion", "version"}:
                value = (node.attrs.get("content") or node.text()).strip()
                if value:
                    version = value
                    break

    # Last resort: "<name> 1.2.3 - <category> - LoversLab" in <title>.
    title = page.title.rsplit(" - LoversLab", 1)[0]
    head = title.split(" - ", 1)[0].strip()
    if not name:
        name = head
    if not version:
        match = _TITLE_VERSION_RE.search(head)
        if match and _looks_like_version(match[1]):
            version = match[1]
            if name == head:
                name = head[: match.start()].strip()
    return FileInfo(name=name.strip(), version=version.strip())


def _looks_like_version(text: str) -> bool:
    text = text.strip()
    return bool(re.fullmatch(_VERSION_TOKEN, text, re.IGNORECASE)) and any(c.isdigit() for c in text)


class PageFetcher(LoversLabClient):
    """Fetch file pages, signed in when credentials are saved, else as a guest."""

    def __init__(self, credentials=None, **kwargs):
        super().__init__(credentials, **kwargs)

    def file_info(self, url: str) -> FileInfo:
        with self._operation():
            if self._credentials is not None:
                self._login()
            with self._request(url) as response:
                page = self._read_page(response)
                status = response.status_code
            if page.browser_required:
                raise PageBlocked("LoversLab requires a browser security check. Open the page in a browser.")
            if status == 404:
                raise DownloadUnavailable("That LoversLab file page no longer exists.")
            if status != 200:
                raise DownloadUnavailable(f"LoversLab returned HTTP {status}.")
            if page.login_required:
                raise PageBlocked("LoversLab requires a login to view this page. Connect your account in Settings → Connections.")
            return parse_file_page(page)


def open_fetcher(stop=None) -> PageFetcher:
    """A fetcher using saved credentials if there are any (guest otherwise)."""
    credentials = None
    try:
        from Utils.loverslab.credentials import load_loverslab_credentials
        credentials = load_loverslab_credentials()
    except Exception:
        credentials = None
    return PageFetcher(credentials, stop=stop)
