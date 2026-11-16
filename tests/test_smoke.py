"""Make sure the add-on loads on whichever Anki version is installed."""

import unittest

from . import _support


class Smoke(unittest.TestCase):
    def test_addon_imports(self) -> None:
        """The add-on's ``__init__`` must import. This is what Anki does at startup."""
        _support.load_addon()
