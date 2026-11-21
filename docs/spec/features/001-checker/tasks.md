# 001 — Checker: tasks

**Status: draft, 2026-10-21.** In order. Each task is one increment with its own commit
(CONSTITUTION §17), and is done when the listed acceptance criteria from `spec.md` pass.

| # | Task | REQ | Done when | State |
|---|---|---|---|---|
| T0 | Settle the open questions in `spec.md` and mark the `REQ-CHK-*` rows `accepted` | all | `spec.md` has no open question without an answer or a recorded deferral | — |
| T1 | `tests/` with `unittest`, an empty `tools/dascheck.py`, and the conformance fixtures from §5 (all failing) | 047 | `python3 -m unittest discover tests` runs and reports the fixtures as failures | — |
| T2 | Lexer: tokens with source positions, strings before comments, lexical diagnostics | 001–008, 041 | A1–A9, B2 | — |
| T3 | Parser: statements, blocks, `;` rules, keyword case, brace balance | 010–015 | S2–S8 | — |
| T4 | Parser: expressions, one-level `&&`/`\|\|`, chained comparisons | 016, 020 | S9, S10, S14 | — |
| T5 | Parser: assignment fallback, raw command arguments, empty right-hand side, numeric properties, operator values | 017–019, 021 | S11–S13, S15 | — |
| T6 | Error recovery | 022 | S16 | — |
| T7 | Corpus: all 13 `scripts/*.das` check clean; fix any script error found, in the same increment | 046 | S1 | — |
| T8 | Repository rules pass | 030–033 | R1–R5 | — |
| T9 | CLI and output format, exit status, no-socket guarantee | 040, 042–044 | B1, B3–B5 | — |
| T10 | Wire into `das_script_test.py check`; delete `mixed_logic()` | 045 | B6, and S9/S10 through `check` | — |
| T11 | Diagnostic-code table with examples | 048 | B8 | — |
| T12 | Docs follow: `README.md` (lint line), `TECH-STACK.md` (tests), `CLAUDE.md` (test suite exists), `grammar.md` §6, `ROADMAP.md` row → done; `REQ-CHK-*` rows → `verified` | — | CONSTITUTION §21 | — |
