"""Right-click "Lovers Lab Actions" for the modlist.

Kept out of ``modlist_menu`` so the upstream file only needs a one-line call
site. Network work runs on a daemon thread and reports back through a
``_Bridge`` QObject living on the UI thread (a queued signal), never by
touching widgets from the worker.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, Signal

from gui_qt.safe_emit import safe_emit
from gui_qt.text_input_overlay import TextInputOverlay


class _Bridge(QObject):
    done = Signal(object)

    def __init__(self, view):
        super().__init__(view)
        self._view = view
        self.done.connect(self._on_done)

    def _on_done(self, payload):
        text, state, refresh = payload
        _notify(self._view, text, state)
        if refresh:
            _refresh(self._view, refresh)


def _bridge(view) -> _Bridge:
    bridge = getattr(view, "_loverslab_bridge", None)
    if bridge is None:
        bridge = view._loverslab_bridge = _Bridge(view)
    return bridge


def _notify(view, text, state="info"):
    cb = getattr(view.window(), "_notify", None)
    if callable(cb):
        cb(text, state)


def _refresh(view, names):
    cb = getattr(view.window(), "_refresh_modlist_flags", None)
    if callable(cb):
        cb(set(names))


def loverslab_meta(view, name):
    """Parsed [loverslab] metadata for *name*, or None if it isn't linked."""
    staging = getattr(view, "staging_dir", None)
    if staging is None:
        return None
    path = staging / name / "meta.ini"
    if not path.is_file():
        return None
    try:
        from LoversLab.ll_meta import read_meta
        meta = read_meta(path)
    except Exception:
        return None
    return meta if meta.file_id > 0 else None


def menu_items(view, name, tr):
    """(label, callback) items for the submenu; ``tr`` is the menu translator."""
    meta = loverslab_meta(view, name)
    if meta is None:
        return [(tr("Link to Lovers Lab page…"), lambda: link(view, name))]
    return [
        (tr("Open on Lovers Lab"), lambda: open_page(view, name)),
        (tr("Check for Updates"), lambda: check_updates(view, [name])),
        (tr("Unlink from Lovers Lab"), lambda: unlink(view, name)),
    ]


def open_page(view, name):
    meta = loverslab_meta(view, name)
    if meta is not None:
        from Utils.environment.xdg import open_url
        open_url(meta.page_url)


def unlink(view, name):
    from LoversLab.ll_meta import remove_meta
    remove_meta(view.staging_dir / name / "meta.ini")
    _refresh(view, [name])


def link(view, name):
    """Ask for a file-page URL and stamp [loverslab] onto the mod."""
    def _picked(text):
        from LoversLab.ll_meta import parse_file_url
        file_id, slug = parse_file_url(text or "")
        if not file_id:
            if (text or "").strip():
                _notify(view, view.tr("That is not a Lovers Lab file-page URL "
                                      "(expected …/files/file/<id>-<name>/)."), "warning")
            return
        _start_link(view, name, file_id, slug)

    TextInputOverlay.show_over(
        view, view.tr("Link to Lovers Lab page"),
        view.tr("Paste the file page URL for {0}:").format(name), _picked)


def _start_link(view, name, file_id, slug):
    meta_path = view.staging_dir / name / "meta.ini"
    bridge = _bridge(view)
    installed_version = ""
    try:
        from Utils.mods.metadata import read_meta_ini
        _, cp, _ = read_meta_ini(str(meta_path))
        installed_version = cp.get("General", "version", fallback="")
    except Exception:
        pass
    error_prefix = view.tr("Linked, but could not read the page")

    def worker():
        from LoversLab.ll_meta import LoversLabModMeta, file_page_url, now_stamp, write_meta
        meta = LoversLabModMeta(file_id=file_id, slug=slug, installed=now_stamp(),
                                version=installed_version)
        text, state = view.tr("Linked {0} to Lovers Lab.").format(name), "success"
        try:
            from LoversLab.ll_page import open_fetcher
            fetcher = open_fetcher()
            try:
                info = fetcher.file_info(file_page_url(file_id, slug))
            finally:
                fetcher.close()
            meta.name = info.name
            meta.latest_version = info.version
            # No recorded installed version: assume the page's, so the first
            # update check doesn't raise a bogus "update available".
            meta.version = meta.version or info.version
        except Exception as exc:
            text, state = f"{error_prefix}: {exc}", "warning"
        try:
            write_meta(meta_path, meta)
        except Exception as exc:
            text, state = f"{exc}", "error"
        safe_emit(bridge.done, (text, state, [name]))

    threading.Thread(target=worker, daemon=True, name="ll-link").start()


def check_updates(view, names):
    """Rate-limited update check for *names* (see ll_update_checker)."""
    staging = getattr(view, "staging_dir", None)
    if staging is None or not names:
        return
    bridge = _bridge(view)
    names = list(names)
    _notify(view, view.tr("Checking Lovers Lab for updates…"), "info")
    msgs = {
        "failed": view.tr("Lovers Lab update check failed - see the log."),
        "blocked": view.tr("Lovers Lab is asking for a browser check; update check stopped."),
        "none": view.tr("All Lovers Lab mods are up to date."),
        "unknown": view.tr("{0} Lovers Lab mod(s) could not be checked."),
        "some": view.tr("Lovers Lab updates available: {0}"),
    }

    def worker():
        from LoversLab.ll_update_checker import check_for_updates
        try:
            res = check_for_updates(staging, only_names=names)
        except Exception:
            safe_emit(bridge.done, (msgs["failed"], "error", None))
            return
        updates = [r.mod_name for r in res if r.has_update]
        unknown = [r for r in res if r.unknown]
        if updates:
            text, state = msgs["some"].format(", ".join(updates)), "warning"
        elif any(r.blocked for r in res):
            text, state = msgs["blocked"], "warning"
        elif unknown:
            text, state = msgs["unknown"].format(len(unknown)), "warning"
        else:
            text, state = msgs["none"], "info"
        safe_emit(bridge.done, (text, state, names))

    threading.Thread(target=worker, daemon=True, name="ll-check-updates").start()
