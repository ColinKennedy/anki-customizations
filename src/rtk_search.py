"""Search the Browser for the text selected while studying a card.

While reviewing, press the shortcut (Ctrl+R by default) to open the Browser and
search ``deck:Japanese::RTK <selection>``.

Anki doesn't use Ctrl+R anywhere in the reviewer, so it's safe to claim. The
shortcut is registered as a *state* shortcut, so it only exists in the main
window while reviewing. It does nothing in the deck list, the Browser, etc.

"""

import logging
import typing

import aqt
from aqt import gui_hooks, main, utils

_LOGGER = logging.getLogger(__name__)

_DEFAULT_SHORTCUT = "Ctrl+R"
_DEFAULT_DECK = "Japanese::RTK"
_REVIEW_STATE = "review"


def _main_window() -> main.AnkiQt:
    # NOTE: Anki always has a main window by the time a shortcut can be pressed.
    # But it is typed as optional in older Anki versions.
    assert aqt.mw is not None

    return aqt.mw


def _config() -> dict[str, typing.Any]:
    package = __name__.split(".")[0]
    loaded = _main_window().addonManager.getConfig(package)

    return loaded if isinstance(loaded, dict) else {}


def quote(text: str) -> str:
    """Make ``text`` match literally in an Anki search, e.g. ``a*b`` -> ``"a\\*b"``."""
    for character in ("\\", '"', "*", "_", ":"):
        text = text.replace(character, "\\" + character)

    return f'"{text}"'


def build_query(selection: str, deck: str = _DEFAULT_DECK) -> typing.Optional[str]:
    """Get the Browser search for ``selection``.

    Returns:
        The search, e.g. ``'deck:Japanese::RTK "髪"'``. This is None if nothing
        is selected.

    """
    text = " ".join(selection.split())

    if not text:
        return None

    return f"deck:{deck} {quote(text)}"


def search_selection() -> None:
    """Open the Browser and search for the text selected in the reviewer."""
    main_window = _main_window()
    query = build_query(
        main_window.web.selectedText(),
        deck=str(_config().get("rtk_search_deck", _DEFAULT_DECK)),
    )

    if query is None:
        utils.tooltip("Select some text on the card first.")

        return

    browser = aqt.dialogs.open("Browser", main_window)
    browser.search_for(query)


def _add_shortcut(
    state: str,
    shortcuts: list[tuple[str, typing.Callable[[], None]]],
) -> None:
    if state != _REVIEW_STATE:
        return

    shortcut = str(_config().get("rtk_search_shortcut", _DEFAULT_SHORTCUT))
    shortcuts.append((shortcut, search_selection))


def register() -> None:
    """Hook into Anki. This is called once, when the add-on loads."""
    gui_hooks.state_shortcuts_will_change.append(_add_shortcut)
