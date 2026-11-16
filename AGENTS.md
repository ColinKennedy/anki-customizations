# Development guide

Personal Anki add-on. Code lives in `src/` (Anki loads `src/` as the
add-on package).

## Supported versions

Both are supported explicitly and tested as separate CI matrix entries:

| Anki     | Python | PyQt6 | tox envs                            |
| -------- | ------ | ----- | ----------------------------------- |
| 24.04    | 3.9    | 6.6.1 | `mypy-anki2404`, `test-anki2404`    |
| 26.09.4  | 3.13   | 6.11.0 | `mypy-anki2609`, `test-anki2609`   |

## One-liners

Setup (once): `python -m pip install tox`

| Task                      | Command                              |
| ------------------------- | ------------------------------------ |
| Check formatting (black)  | `tox -e check-black`                 |
| Check import order        | `tox -e check-isort`                 |
| Auto-format               | `tox -e black && tox -e isort`       |
| Type-check, Anki 24.04    | `tox -e mypy-anki2404`               |
| Type-check, Anki 26.09.4  | `tox -e mypy-anki2609`               |
| Tests, Anki 24.04         | `tox -e test-anki2404`               |
| Tests, Anki 26.09.4       | `tox -e test-anki2609`               |
| Everything CI runs        | `tox` (runs every env above)         |

CI (`.github/workflows/`) runs on every pull request and on pushes to `master`:
black, isort, mypy (`--strict`, once per Anki version above) and the tests
(once per Anki version above).

tox needs Python 3.9 and 3.13 installed (`py -3.9` / `py -3.13` on Windows).

## Trying changes in Anki

Link `src/` into Anki's add-ons folder instead of copying it:

- Windows (PowerShell): `New-Item -ItemType Junction -Path "$env:APPDATA\Anki2\addons21\anki-customizations" -Target (Resolve-Path src)`
- Linux/macOS: `ln -s "$PWD/src" ~/.local/share/Anki2/addons21/anki-customizations`

## Conventions

- Add type hints to everything; `mypy --strict` must stay clean for new code.
- Prefer explicit `typing` imports compatible with Python 3.9.
- Each customization is its own module in `src/`, registered from `src/__init__.py`.
