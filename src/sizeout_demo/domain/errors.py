"""Typed errors: the caller decides how to show them, the domain only names them."""

from __future__ import annotations


class DomainError(Exception):
    """The input makes the calculation meaningless."""


class InvalidInput(DomainError):
    """A value lies outside the range in which the formulas hold."""


class InsufficientData(DomainError):
    """Too few reflections for the requested fit."""


class ReferenceModelRequired(DomainError):
    """The line says "no strain" or "no size broadening" and the value has to come
    from a reference model that was not entered."""
