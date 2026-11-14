# Contributing

Thank you for looking. The project is small on purpose; the bar for a change is that it
keeps every check below green and is explained.

## Set up

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

## The checks CI runs

```bash
ruff check src tests tools
ruff format --check src tests tools
mypy
lint-imports
pytest
```

And before a change to the calculation, the mutation check - every planted bug must be
caught:

```bash
python tools/mutation_check.py
```

## Rules of the house

- **The domain stays pure**: standard library only, frozen dataclasses, no I/O. The
  `import-linter` contracts in `pyproject.toml` fail the build otherwise.
- **A new test is shown failing first.** Break the code on purpose, watch the test go
  red, then put the code back. If a test cannot fail, it does not prove anything.
- **Numbers need a witness.** A new formula comes with a worked example, a property, or
  a golden value from the full program (`tools/make_golden.py`).
- **Decisions are written down.** A change to the structure gets an ADR in `docs/adr/`.
- **Screenshots are generated**, never edited: `python tools/make_screenshots.py`.

## Commit messages

Imperative mood, one subject line under 72 characters, a body that says why.
