# 001 — Checker: feature spec

**Status: draft, 2026-10-21.** Roadmap row: *Standard-library recursive-descent checker in
`tools/`, replacing the regex lint in `das_script_test.py check`* (`docs/ROADMAP.md`, DSL
documentation). Requirements: `REQ-CHK-*` in `docs/spec/REQUIREMENTS.md`. Design:
`plan.md`. Work: `tasks.md`.

## Problem

DAS runs a script as it parses it. Every statement before a syntax error has already run
when the error dialog opens, and that dialog freezes the CMD API until something dismisses
it (`grammar.md`, *The execution model*; `docs/CMD-API-TESTING.md`). A typo near the end of
an order script can send the order and then report the typo. DAS's own error is not a
pre-flight check.

Today's pre-flight is the regex lint in `das_script_test.py check`. It catches two things:
single quotes, and `&&`/`||` mixed without parentheses. It also strips comments with
`line.split("//", 1)`, so a `//` inside a string literal hides the rest of that line from
both checks. The grammar now settles twelve rules the lint cannot see (§5 probes).

## Who uses it

| Who | When | What they need |
|---|---|---|
| The script author (David) | Before pasting a script into a hotkey or Chart Script | Every error at once, with line and column, before DAS sees the text |
| `das_script_test.py check --live` and the forward-test driver | Before injecting | A non-zero exit that stops the injection |
| `dastrader-mode` (later) | On save, through `compile`/`flymake` | `file:line:col: severity code: message` output |
| `.htk` generation (later) | Before writing a hotkey file | A parse tree, not just diagnostics |

## Scope

In:
- A lexer and recursive-descent parser for `grammar.md` §2 and §3.
- Diagnostics for every `REQ-CHK-*` requirement.
- `das_script_test.py check` calling it for the static pass.
- Conformance fixtures from the §5 probes, and the 13 `scripts/*.das` files as a corpus.

## Non-goals

- **Running anything.** The checker never opens a socket and never injects text. Live
  checking stays in `das_script_test.py check --live`, unchanged.
- **Runtime facts.** Unknown function names, read-only properties, the 200-iteration
  `while` cap, one `Send()` per second, and whether a window exists are runtime matters.
  The checker does not guess at them.
- **Type checking.** DAS's mixed-type rules are mostly untested (§3.9).
- **A formatter.** `INTENT.md` mentions a canonical formatter; it is a separate feature.
- **An LSP.** The output format is chosen so an editor can use it without one.
- **Third-party parser libraries.** The Lark grammar used to check `grammar.md` stays out
  of the repo (`TECH-STACK.md`).

## Acceptance criteria

Each criterion is one test. "Errors" means diagnostics of severity error; the checker exits
1 when there is at least one.

**Lexical**

| # | Given | When | Then | REQ |
|---|---|---|---|---|
| A1 | `MsgLog('x');` | checked | two errors on line 1, one at each `'` | 001 |
| A2 | `$u = "http://x"; MsgLog($u)` | checked | no diagnostics; `MsgLog($u)` is parsed, not treated as comment | 002 |
| A3 | `/* MsgLog("f2 HIDDEN"); */ MsgLog("f2 shown");` (F2) | checked | no diagnostics | 003 |
| A4 | `/*` on line 1, `*/` on line 3, code on line 4 | checked | no diagnostics; line 4 is parsed | 003 |
| A5 | `MsgLog("a"); /* never closed` | checked | one error at the `/*` | 004 |
| A6 | `MsgLog("abc);` | checked | one error at the opening `"`; no follow-on error for the unclosed `(` | 005 |
| A7 | `MsgLog(“TRTEST”);` | checked | two errors, one at each curly quote, naming `"` as the replacement | 006 |
| A8 | `MsgLog("a\qb");` | checked | one warning, no errors | 007 |
| A9 | `// it's fine` then `MsgLog("x");` | checked | one warning on line 1, no errors | 008 |

**Syntax**

| # | Given | When | Then | REQ |
|---|---|---|---|---|
| S1 | each of the 13 files in `scripts/` | checked | zero errors | 010, 046 |
| S2 | `IF (1==1) { MsgLog("q10"); }` (Q10) | checked | one error at `IF`, naming `if`; the rest parses as an `if` (DAS logged two errors here; the checker reports the cause once) | 011 |
| S3 | `if (1==1) { … } ELSE { … }` (F4b) | checked | one error at `ELSE` | 011 |
| S4 | `if (1==1) { MsgLog("q6") }` (Q6) | checked | one error at `}`: missing `;` | 012 |
| S5 | `if (1==1) { $f3=7 } MsgLog("x");` (F3) | checked | one error at `}`: missing `;` | 012 |
| S6 | `MsgLog("a") MsgLog("b");` | checked | one error between the two calls | 013 |
| S7 | `MsgLog("f9 a"); MsgLog("f9 b")` (F9) | checked | no diagnostics | 014 |
| S8 | `if (1==1) { MsgLog("x");` | checked | one error at end of file: unclosed `{` | 015 |
| S9 | `if (1==1 \|\| 1==2 && 1==2) { … }` (P1) | checked | one error at the condition | 016 |
| S10 | `if ((1==1 \|\| 1==2) && 1==2) { … }` | checked | no diagnostics | 016 |
| S11 | `MsgLog("f7 before"); $f7 = ; MsgLog("f7 after");` (F7) | checked | one error at `;` after `=` | 017 |
| S12 | `$q5="SPY"; SYMBOL $q5;` (Q5) | checked | one error at `$q5` in the command, suggesting `Exec` | 018 |
| S13 | `$o.1 = 20;` | checked | one error suggesting `.Set()` | 019 |
| S14 | `if (3 > 2 > 1) { … }` (P7) | checked | one warning, no errors | 020 |
| S15 | `AlertOperator=<=;` | checked | one warning suggesting `"<="` | 021 |
| S16 | three independent syntax errors on lines 1, 3, 5 | checked | three errors, one per line | 022 |

**Repository rules**

| # | Given | When | Then | REQ |
|---|---|---|---|---|
| R1 | `MsgBox("x");` | checked | one warning | 030 |
| R2 | `WPos 0 0;` with no earlier `SetPopOut Y` | checked | one warning | 031 |
| R3 | `SetPopOut Y; WPos 0 0;` | checked | no diagnostics | 031 |
| R4 | `NewWindow Chart; GetWindowObj("c").GetTicker();` | checked | one warning | 032 |
| R5 | `$w = GetWindowObj();` | checked | one warning | 033 |

**Behaviour**

| # | Given | When | Then | REQ |
|---|---|---|---|---|
| B1 | any file with a diagnostic | checked | each line reads `path:line:col: severity CODE: message` | 040 |
| B2 | an error on source line 7 of a multi-line file | checked | the diagnostic says line 7 | 041 |
| B3 | a clean file · a file with one error · a missing file | checked | exit 0 · 1 · 2 | 042 |
| B4 | `tools/` source | imports listed | standard library only | 043 |
| B5 | the checker run with networking blocked | checking any file | completes; no socket opened | 044 |
| B6 | `das_script_test.py check scripts/20-fl-long.das --live` | run | refused for order tokens, exactly as today | 045 |
| B7 | each §5 probe fixture | checked | diagnostics match the fixture's expected list | 047 |
| B8 | the diagnostic-code table | read | every code has an example and a REQ id | 048 |

## Open questions

1. **Single quote inside a string literal** (`"it's"`). The 09-24 rejection had the quote in
   code; inside a string is untested [?]. Proposed: error (REQ-CHK-001) until a probe says
   otherwise.
2. **Where does the code live?** `plan.md` proposes a new module `tools/dascheck.py`
   imported by `das_script_test.py`. Alternative: inside `das_script_test.py`, which is
   already 489 lines.
3. **Basic-tier raw values.** How DAS chooses between the raw and expression readings of
   `name = …` is unknown (§3.6). The checker uses the grammar's rule: try the expression,
   fall back to raw text for an unqualified name. Errors that hinge on this are possible.
