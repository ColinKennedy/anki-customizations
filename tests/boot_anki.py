"""Boot a *real* Anki main window with the add-on installed, then report as JSON.

Usage: python boot_anki.py <base-dir> <addon-src-dir>

The add-on is copied to <base>/addons21/anki_customizations_boot, exactly where
Anki loads it. Run by ``tests/test_boot.py`` in a subprocess because it starts a
whole Anki.

"""

import json
import os
import shutil
import sys

base, source = sys.argv[1], sys.argv[2]
_ADDON = "anki_customizations_boot"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
shutil.rmtree(base, ignore_errors=True)
shutil.copytree(
    source,
    os.path.join(base, "addons21", _ADDON),
    ignore=shutil.ignore_patterns("__pycache__", ".mypy_cache", "meta.json"),
)

# Skip Anki's first-run "Language" dialog by creating the prefs database up front.
from aqt.profiles import ProfileManager  # noqa: E402

_pm = ProfileManager(ProfileManager.get_created_base_folder(base))
_pm.setupMeta()
_pm.db.commit()
_pm.db.close()
del _pm

warnings: list[str] = []
uncaught: list[str] = []
report: dict = {}


def _finish() -> None:
    try:
        _collect()
    finally:
        report["uncaught_exceptions"] = list(uncaught)
        print("REPORT " + json.dumps(report), flush=True)
        os._exit(0)


def _collect() -> None:
    import aqt
    from aqt import gui_hooks

    report["startup_warnings"] = warnings
    report["addon_loaded"] = _ADDON in sys.modules

    # What Anki does when the study screen opens.
    review: list = []
    gui_hooks.state_shortcuts_will_change("review", review)
    report["review_shortcuts"] = [key for key, _ in review]

    other: list = []
    gui_hooks.state_shortcuts_will_change("deckBrowser", other)
    report["deck_browser_shortcuts"] = [key for key, _ in other]

    from aqt import reviewer

    taken = [str(key).lower() for key, _ in reviewer.Reviewer(aqt.mw)._shortcutKeys()]
    report["anki_uses_ctrl_r"] = "ctrl+r" in taken


def _hook() -> None:
    from aqt import gui_hooks
    from aqt.qt import QTimer

    def _later() -> None:
        QTimer.singleShot(3000, _finish)

    gui_hooks.main_window_did_init.append(_later)

    import aqt.addons
    import aqt.errors
    import aqt.utils

    def _capture(text: str, *args: object, **kwargs: object) -> None:
        warnings.append(str(text)[:300])

    def _record(self):  # type: ignore[no-untyped-def]
        text = self.pool[-1500:]
        self.pool = ""
        uncaught.append(text)

    # Anki would show an "Anki encountered a problem" dialog; record it instead.
    aqt.errors.ErrorHandler.onTimeout = _record  # type: ignore[method-assign]

    aqt.addons.showWarning = _capture  # type: ignore[attr-defined]
    aqt.utils.showWarning = _capture  # type: ignore[assignment]
    aqt.addons.showInfo = _capture  # type: ignore[attr-defined]


import aqt

# NOTE: Don't collide with (or reuse) any Anki the developer already has open.
aqt.AnkiApp.KEY = f"anki-customizations-boot-test-{os.getpid()}"

_orig_init = aqt.AnkiApp.__init__


def _init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
    _orig_init(self, *args, **kwargs)
    from aqt.qt import QApplication, QTimer

    def _watchdog() -> None:
        print("STALLED " + json.dumps(uncaught), flush=True)
        os._exit(3)

    QTimer.singleShot(90000, _watchdog)

    # Act like a user: click "OK" on any modal dialog.
    def _dismiss() -> None:
        modal = QApplication.activeModalWidget()

        if modal is not None:
            modal.accept() if hasattr(modal, "accept") else modal.close()

    dismisser = QTimer(self)
    dismisser.timeout.connect(_dismiss)
    dismisser.start(1000)


aqt.AnkiApp.__init__ = _init
_hook()
sys.argv = ["anki", "--base", base, "--lang", "en_US"]
aqt.run()
