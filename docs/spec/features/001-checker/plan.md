# 001 — Checker: plan

**Status: draft, 2026-10-21.** How `spec.md` gets built. Decisions marked **(proposed)**
close when the spec is accepted.

## Shape

```
tools/dascheck.py          lexer → parser → rules → diagnostics      (new, stdlib only)
tools/das_script_test.py   check: static pass calls dascheck; --live unchanged
tests/test_dascheck.py     unittest; python3 -m unittest discover tests
tests/conformance/*.das    one fixture per §5 probe, expectations in a header comment
```

- **New module (proposed).** `das_script_test.py` is a harness for a live DAS; the checker
  must run with no DAS at all (REQ-CHK-044). Separate files keep that boundary visible, and
  let `dastrader-mode` call `python3 tools/dascheck.py FILE` directly.
- **`unittest` (proposed).** Standard library, so it satisfies `TECH-STACK.md` without a new
  dependency. This adds the repo's first test suite; `CLAUDE.md` and `TECH-STACK.md` are
  updated in the same increment.

## Lexer

One pass over the source, producing tokens with `(line, col)` from the original text
(REQ-CHK-041).

- Order of recognition: string literal before comment, so `"http://x"` is a string
  (REQ-CHK-002, the bug in today's lint).
- Token kinds: `NAME`, `GLOBAL` (`$name`), `NUMBER`, `STRING`, `OP` (§2.6), `PUNCT`,
  `RAW` (produced on demand by the parser, see below), `EOF`.
- Comments are dropped, but a `'` inside one produces REQ-CHK-008.
- Lexical errors (REQ-CHK-001, 004, 005, 006) become diagnostics; the lexer skips the
  offending character and continues, so each stray quote is its own error.
- An unterminated string ends at the line break (REQ-CHK-005). The parser suppresses
  errors in a statement that already holds a lexical error, so one typo gives one error.
- After a `.` that follows a name, `$name` or `)`, a digit run is a property name, not a
  number, so `$o.1` reaches REQ-CHK-019 instead of lexing as `$o` `.1`.

## Parser

Recursive descent, one function per production of `grammar.md` §3.1.

- **Statement dispatch** follows the §3.8 table: after a leading `NAME`, the next token
  picks assignment, call, member access or command. A keyword in the wrong case is caught
  here (REQ-CHK-011): a `NAME` equal to a keyword ignoring case, but not lower case, is
  reported, then parsed as that keyword, so `IF (…) {…}` gives one error, not a cascade of
  missing-`;` errors.
- **Raw text.** `command` arguments and basic-tier `raw_value` are not tokenised as
  expressions. When the parser reaches one, it asks the lexer for everything up to the
  next `;`, `{`, `}` or line break as a single `RAW` token. A `$` inside a command's `RAW`
  is REQ-CHK-018.
- **Assignment fallback** (§3.6): parse `name = expression`; if that fails and the target
  is an unqualified name, re-read the right-hand side as `RAW`. An empty right-hand side is
  REQ-CHK-017 before either is tried. A raw value that starts with a comparison operator
  (`<=`, `>=`, `==`, `!=`, `<`, `>`) is REQ-CHK-021.
- **`logical`** keeps one flat list of operators per parenthesis level; both `&&` and `||`
  in one list is REQ-CHK-016. This replaces `mixed_logic()`.
- **`comparison`** with two or more `rel_op` is REQ-CHK-020.
- **Recovery** (REQ-CHK-022): on a syntax error, record it, skip to the next `;` or `}` at
  the current brace depth, and resume.

The parser returns a small tree (`dataclass` nodes). Nothing uses it yet beyond the rule
pass; `.htk` generation will.

## Rules

A pass over the tree for the repository rules (REQ-CHK-030 to 033). Each rule is a function
taking the tree and returning diagnostics, so a rule can be added without touching the
parser.

## Diagnostics

```
scripts/example.das:14:9: error DS201: keyword "IF" must be lower case: if
```

Codes are stable once published (REQ-CHK-048):

| Range | Kind |
|---|---|
| `DS1xx` | lexical (REQ-CHK-001 to 008) |
| `DS2xx` | syntax (REQ-CHK-010 to 022) |
| `DS3xx` | repository rules (REQ-CHK-030 to 033) |

The code table, with one example per code, goes at the end of `REQUIREMENTS.md` or in a
reference chapter; decided when the first code ships.

Exit status: 0 / 1 / 2 (REQ-CHK-042).

## Conformance fixtures

Each `grammar.md` §5 probe becomes `tests/conformance/<probe>.das`. Its first line states
what is expected:

```
// expect: DS204@2:26        (Q6: block-final ; required)
if (1==1) { MsgLog("q6") }
```

| Probe | DAS did | Expect | REQ |
|---|---|---|---|
| Q1 Q2 Q3 Q4 Q7 Q8 Q9 Q11 Q12 F1 F2 F5 F8 F9 F10 P2 P3 | accepted | none | 010, 014 |
| Q5 | ran, loaded symbol `$` | error | 018 |
| Q6 F3 | `ScriptError:100` | error | 012 |
| Q10 F4a F4b | `Function … not exist!` / `Invalid token` | error | 011 |
| F7 | accepted | error, by design | 017 |
| P1 P1b | evaluated left to right | error | 016 |
| P7 | evaluated left to right | warning | 020 |

§5 prints several probes as summaries (F1, F5, P1–P7, Q12) and escapes `|` as `\|` inside
table cells, so each fixture is written out as full script text from the probe's
description, with real `|`. This repo wrote every probe; no manual text is copied
(CONSTITUTION §16). The 13 `scripts/*.das` files are a second
corpus: zero errors expected (REQ-CHK-046).

## Integration with `das_script_test.py check`

- The static block in `cmd_check` (single quotes, `mixed_logic`) is replaced by a call to
  `dascheck.check(path)`; its diagnostics print in the new format.
- `ORDER_TOKENS`, the `--live` refusal, the `MsgBox`→`MsgLog` rewrite and the one-line join
  stay as they are (REQ-CHK-045).
- `mixed_logic()` is deleted once `S9`/`S10` pass through the new path.

## Risks

| Risk | Mitigation |
|---|---|
| The raw/expression fallback misreads a basic-tier line, giving a false error | The 13 scripts and the probes run on every change; a false error in `scripts/` blocks the increment (REQ-CHK-046) |
| A rule rests on `[I]` and DAS disagrees | Each such REQ is labelled; a contradicting probe changes the REQ, then the code (CONSTITUTION §22) |
| Layout inside the hotkey dialog differs from the API's one-line form (§2.1 open) | The checker treats line breaks as whitespace, which matches what the API runs; revisit if a dialog test disagrees |
