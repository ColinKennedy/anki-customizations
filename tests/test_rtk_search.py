"""Tests for the "search the Browser for the selected text" shortcut."""

import unittest
from unittest import mock

from . import _support


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        _support.load_addon()

        from anki_customizations_under_test import rtk_search

        self.module = rtk_search


class BuildQuery(_Base):
    def test_basic(self) -> None:
        self.assertEqual('deck:Japanese::RTK "髪"', self.module.build_query("髪"))

    def test_nothing_selected(self) -> None:
        for blank in ("", " ", "\n\t "):
            with self.subTest(blank=blank):
                self.assertIsNone(self.module.build_query(blank))

    def test_whitespace_is_normalized(self) -> None:
        self.assertEqual(
            'deck:Japanese::RTK "a b"', self.module.build_query("  a \n b ")
        )

    def test_special_characters_are_literal(self) -> None:
        self.assertEqual(
            r'deck:Japanese::RTK "a\*b\_c\:d\"e\\f"',
            self.module.build_query('a*b_c:d"e\\f'),
        )

    def test_custom_deck(self) -> None:
        self.assertEqual('deck:Other "x"', self.module.build_query("x", deck="Other"))


class SearchSelection(_Base):
    def test_opens_browser_and_searches(self) -> None:
        main_window = mock.MagicMock()
        main_window.web.selectedText.return_value = "髪"
        main_window.addonManager.getConfig.return_value = {}

        with mock.patch.object(self.module.aqt, "mw", main_window), mock.patch.object(
            self.module.aqt, "dialogs"
        ) as dialogs:
            self.module.search_selection()

        dialogs.open.assert_called_once_with("Browser", main_window)
        dialogs.open.return_value.search_for.assert_called_once_with(
            'deck:Japanese::RTK "髪"'
        )

    def test_nothing_selected_only_shows_a_tooltip(self) -> None:
        main_window = mock.MagicMock()
        main_window.web.selectedText.return_value = " "
        main_window.addonManager.getConfig.return_value = None

        with mock.patch.object(self.module.aqt, "mw", main_window), mock.patch.object(
            self.module.aqt, "dialogs"
        ) as dialogs, mock.patch.object(self.module.utils, "tooltip") as tooltip:
            self.module.search_selection()

        dialogs.open.assert_not_called()
        tooltip.assert_called_once()


class Shortcut(_Base):
    def _shortcuts(self, state: str) -> list[tuple[str, object]]:
        main_window = mock.MagicMock()
        main_window.addonManager.getConfig.return_value = {}
        shortcuts: list[tuple[str, object]] = []

        with mock.patch.object(self.module.aqt, "mw", main_window):
            self.module._add_shortcut(state, shortcuts)  # type: ignore[arg-type]

        return shortcuts

    def test_only_added_while_reviewing(self) -> None:
        self.assertEqual(
            [("Ctrl+R", self.module.search_selection)], self._shortcuts("review")
        )

        for state in ("deckBrowser", "overview", "profileManager"):
            with self.subTest(state=state):
                self.assertEqual([], self._shortcuts(state))

    def test_is_registered_with_anki(self) -> None:
        from aqt import gui_hooks

        self.assertIn(
            self.module._add_shortcut,
            gui_hooks.state_shortcuts_will_change._hooks,
        )


_ALPHABET = (
    "髪型日本語漢字",  # Kanji, the expected input.
    "ひらがなカタカナｱｲｳ",
    "abcXYZ 0123",
    " \t\n\u3000",  # Whitespace, including full-width.
    "\"'\\*_:-()[]{}%?!&|<>=^~`;,./",  # Anki search syntax.
    "\x00\x07\x1b\u200b\ufeff\ud7ff",  # Control and invisible characters.
    "😀🎌\U0001f9d1\u200d\U0001f4bb",  # Emoji, incl. a joined sequence.
)
_SENTENCES = (
    "私は昨日、友達と一緒に新しい映画を見に行きました。",
    'He said "deck:*" -tag:x or (a OR b) \\ _ * :',
    "deck:Japanese::RTK 髪",
    "-髪",
    "re:.*",
    "nc:髪 is:due prop:ivl>3",
    '"',
    "\\",
    "a" * 10000,
)


class Fuzz(_Base):
    """Whatever gets selected (a kanji, a sentence, junk), the search must be valid."""

    def setUp(self) -> None:
        super().setUp()

        import pathlib
        import random
        import tempfile

        from anki import collection

        self._directory = tempfile.TemporaryDirectory()
        self.addCleanup(self._directory.cleanup)
        self.collection = collection.Collection(
            str(pathlib.Path(self._directory.name) / "collection.anki2")
        )
        self.addCleanup(self.collection.close)
        self.random = random.Random(1234)  # Deterministic, so failures reproduce.

    def _samples(self) -> list[str]:
        samples = list(_SENTENCES)
        pool = "".join(_ALPHABET)

        for _ in range(300):
            samples.append(
                "".join(self.random.choices(pool, k=self.random.randint(0, 40)))
            )

        for group in _ALPHABET:
            samples.extend(group)  # Every character on its own.

        return samples

    def test_every_selection_is_a_valid_search(self) -> None:
        for sample in self._samples():
            with self.subTest(sample=sample[:40]):
                query = self.module.build_query(sample)

                if query is None:
                    self.assertFalse(sample.split())

                    continue

                self.assertTrue(query.startswith("deck:Japanese::RTK "))
                # NOTE: Anki's real parser. It raises on invalid syntax.
                self.collection.find_cards(query)

    def test_selection_is_matched_literally(self) -> None:
        """Syntax characters must not act as search operators."""
        model = self.collection.models.by_name("Basic")
        self.assertIsNotNone(model)
        deck = self.collection.decks.id("Japanese::RTK")
        other = self.collection.decks.id("Other")

        for front, deck_id in (
            ("髪", deck),
            ("a*b", deck),
            ("髪型", deck),
            ("髪", other),
        ):
            note = self.collection.new_note(model)
            note["Front"] = front
            self.collection.add_note(note, deck_id)

        def _count(selection: str) -> int:
            query = self.module.build_query(selection)
            assert query is not None

            return len(self.collection.find_notes(query))

        self.assertEqual(2, _count("髪"))  # Not the "Other" deck's note.
        self.assertEqual(1, _count("髪型"))
        self.assertEqual(1, _count("a*b"))
        self.assertEqual(0, _count("ab"))  # "*" isn't a wildcard.
        # NOTE: A wildcard "*" would match every note in the deck (3).
        self.assertEqual(1, _count("*"))
        self.assertEqual(0, _count("deck:*"))
        self.assertEqual(0, _count("-髪"))

    def test_search_selection_never_raises(self) -> None:
        for sample in self._samples():
            with self.subTest(sample=sample[:40]):
                main_window = mock.MagicMock()
                main_window.web.selectedText.return_value = sample
                main_window.addonManager.getConfig.return_value = {}

                with mock.patch.object(
                    self.module.aqt, "mw", main_window
                ), mock.patch.object(self.module.aqt, "dialogs"), mock.patch.object(
                    self.module.utils, "tooltip"
                ):
                    self.module.search_selection()
