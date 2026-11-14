"""The window (Qt) and its presenters (no Qt).

``presenters``, ``parsing`` and ``view`` never import Qt - the rule is checked in CI -
so everything the user can do is tested without opening a window.
"""
