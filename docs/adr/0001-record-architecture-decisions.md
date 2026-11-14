# 1. Record architecture decisions

Date: 2026-11-14 · Status: accepted

## Context

The demo is small, but it is written to show how a scientific desktop program can be
built: why it is shaped the way it is matters as much as the code.

## Decision

Every decision that shapes the structure, the dependencies or the numbers is recorded
as a short Architecture Decision Record (context, decision, consequences), one file
each, numbered, never rewritten - a changed mind is a new record that supersedes the
old one.

## Consequences

The records are linked from [architecture.md, section 9](../architecture.md#9-architecture-decisions).
A reviewer can follow the reasoning without reading the history of the code.
