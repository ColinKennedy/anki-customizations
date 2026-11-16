"""Boot a real Anki main window with the add-on installed.

This is the closest thing to "does the add-on work in Anki" we can run in CI.

"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

_TESTS = pathlib.Path(__file__).resolve().parent
_SOURCE = _TESTS.parent / "src"


class Boot(unittest.TestCase):
    def test_boots_without_startup_errors(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            env = dict(
                os.environ,
                QT_QPA_PLATFORM="offscreen",
                # NOTE: Chromium needs these in containers / on CI runners.
                QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --disable-gpu",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-W",
                    "ignore",
                    str(_TESTS / "boot_anki.py"),
                    os.path.join(base, "anki"),
                    str(_SOURCE),
                ],
                env=env,
                capture_output=True,
                text=True,
                timeout=240,
            )

        lines = [
            line for line in result.stdout.splitlines() if line.startswith("REPORT ")
        ]
        self.assertTrue(
            lines,
            "Anki never finished starting.\n"
            + result.stdout[-3500:]
            + f"\n--- stderr ---\n{result.stderr[-1500:]}",
        )
        report = json.loads(lines[-1][len("REPORT ") :])

        self.assertEqual(
            [],
            report["uncaught_exceptions"],
            "\n\n".join(report["uncaught_exceptions"]),
        )
        self.assertEqual([], report["startup_warnings"])
        self.assertTrue(report["addon_loaded"])
        self.assertEqual(["Ctrl+R"], report["review_shortcuts"])
        self.assertEqual([], report["deck_browser_shortcuts"])
        self.assertFalse(report["anki_uses_ctrl_r"])
