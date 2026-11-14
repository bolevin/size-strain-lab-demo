# 8. Fluent widgets, and therefore GPL-3.0

Date: 2026-11-14 · Status: accepted

## Context

The full program uses PySide6 with PySide6-Fluent-Widgets for a native Windows 11 look.
The demo should look like a sibling of it. PySide6-Fluent-Widgets is licensed under
GPL-3.0.

## Decision

Use the same stack - PySide6, PySide6-Fluent-Widgets, pyqtgraph - and license the demo
under GPL-3.0-or-later. Third-party licences are listed in
[THIRD-PARTY-NOTICES.md](../../THIRD-PARTY-NOTICES.md).

## Consequences

* A built executable is distributed together with its source (the release workflow
  attaches both).
* Only the `ui` layer depends on the widget library; replacing it with plain PySide6
  would touch no other layer (ADR 2).
