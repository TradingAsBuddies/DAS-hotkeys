# Requirements

**Status: draft, 2026-10-21.** What each deliverable in `INTENT.md` must do, one numbered
line per requirement, so that a feature spec, a test and a roadmap row can all point at the
same thing. `docs/spec/grammar.md` says what the language *is*; this file says what the
tools and documents built on it *must do*.

## Conventions

**Ids.** `REQ-<AREA>-<NNN>`. An id is never reused or renumbered. A dropped requirement
stays in its table with state `withdrawn` and a reason.

| Area | Deliverable | Feature spec |
|---|---|---|
| `CHK` | stdlib checker in `tools/` | `features/001-checker/` |
| `MODE` | Emacs `dastrader-mode` | not yet written |
| `REF` | language reference | not yet written |
| `HTK` | `.htk` generation from `scripts/*.das` | not yet written |

Only `CHK` has requirements so far. The other areas get theirs when their feature spec is
written, not before.

**Keywords.** **SHALL** is required for the feature to be called done. **SHOULD** is
expected unless the feature spec records why not. **MAY** is optional.

**Evidence.** The labels from `grammar.md` (`[D adv p.N]`, `[D hk p.N]`, `[V date]`, `[I]`,
`[?]`), plus **[C §N]** for a CONSTITUTION rule. A requirement that rests on `[I]` or `[?]`
says so; it is a design choice, not a fact about DAS.

**Severity** (checker only). **error**: DAS rejects it, or it does something the author
never means, or CONSTITUTION forbids it; the checker exits non-zero. **warning**: legal but
untested or risky; reported, exit status unchanged.

**State.** `draft` → `accepted` (feature spec agreed) → `verified` (a test citing the id
passes) · `withdrawn`.

## CHK — checker

Why it exists: DAS executes a script as it parses, so statements before a syntax error have
already run when the error dialog opens (`grammar.md`, *The execution model*). The checker
is the pre-flight that DAS does not have.

### Lexical

| Id | Requirement | Sev | Source | Evidence | State |
|---|---|---|---|---|---|
| REQ-CHK-001 | The checker SHALL report a single quote anywhere outside a comment. | error | §2.5, C §10 | [V 2026-09-24, 5.8.2.5]; inside a string literal [?] | draft |
| REQ-CHK-002 | The checker SHALL treat `//` and `/*` inside a string literal as string text, not as a comment. | — | §2.2, §2.5 | [I] | draft |
| REQ-CHK-003 | The checker SHALL recognise `/* … */` block comments, including ones spanning lines. | — | §2.2 | single-line [V 2026-10-15, F2]; multi-line [I] | draft |
| REQ-CHK-004 | The checker SHALL report an unterminated block comment. | error | §2.2 | [I] | draft |
| REQ-CHK-005 | The checker SHALL report an unterminated string literal. | error | §2.5 | [I] | draft |
| REQ-CHK-006 | The checker SHALL report typographic quotes (`“ ” ‘ ’`) in code, naming the straight quote to use. | error | §2.5, §4 row 5 | straight `"` only [D adv p.17]; curly quotes untested [I] | draft |
| REQ-CHK-007 | The checker SHOULD warn on any string escape other than `\"`, `\n`, `\t`. | warning | §2.5 | [?] | draft |
| REQ-CHK-008 | The checker SHALL warn on a single quote inside a comment. | warning | §2.2 | [V 2026-09-24, 5.8.2.5] ran; kept out by rule | draft |

### Syntax

| Id | Requirement | Sev | Source | Evidence | State |
|---|---|---|---|---|---|
| REQ-CHK-010 | The checker SHALL parse every production in `grammar.md` §3.1. | — | §3.1 | per production | draft |
| REQ-CHK-011 | The checker SHALL report `if`, `else`, `while` or `return` written in any case other than lower case. | error | §2.3 | [V 2026-10-15, Q10, F4] | draft |
| REQ-CHK-012 | The checker SHALL report a simple statement (assignment, call, member command, command, `return`) inside a block that is not ended by `;`, the last one included. `if` and `while` need no `;` after `}`. | error | §3.2 | [V 2026-10-15, Q6, F3] | draft |
| REQ-CHK-013 | The checker SHALL report two top-level simple statements not separated by `;`. | error | §3.2 | [D adv p.4] | draft |
| REQ-CHK-014 | The checker SHALL accept a script whose final top-level statement has no `;`. | — | §3.2 | [V 2026-10-15, F9] | draft |
| REQ-CHK-015 | The checker SHALL report unbalanced `( )` and `{ }`. | error | §3.1 | [I] | draft |
| REQ-CHK-016 | The checker SHALL report `&&` and `\|\|` mixed at one parenthesis level. | error | §3.9, C §10 | [V 2026-10-15, P1, P1b] | draft |
| REQ-CHK-017 | The checker SHALL report an assignment with an empty right-hand side (`$x = ;`). | error | §3.6, §4 row 7 | DAS accepts it [V 2026-10-15, F7]; flagged by design | draft |
| REQ-CHK-018 | The checker SHALL report a `$variable` in a command's raw arguments and suggest `Exec`. | error | §3.8, C §10 | [V 2026-10-15, Q5] | draft |
| REQ-CHK-019 | The checker SHALL report a numeric property name (`$o.1`), suggesting `.Set()`/`.Get()`. | error | §3.6 | [D adv p.30] | draft |
| REQ-CHK-020 | The checker SHOULD warn on a chained comparison (`a > b > c`). | warning | §3.9 | [V 2026-10-15, P7] | draft |
| REQ-CHK-021 | The checker SHOULD warn on an unquoted operator value (`AlertOperator=<=`). | warning | §3.6 | [D adv p.7] | draft |
| REQ-CHK-022 | The checker SHOULD report more than one syntax error per file, resuming at the next `;` or `}`. | — | — | design | draft |

### Repository rules

| Id | Requirement | Sev | Source | Evidence | State |
|---|---|---|---|---|---|
| REQ-CHK-030 | The checker SHALL warn on `MsgBox` (a modal freezes the CMD API). | warning | C §10 | [I]: error dialogs freeze it [V 2026-09-24, 5.8.2.5]; MsgBox itself untested | draft |
| REQ-CHK-031 | The checker SHOULD warn on `WPos` or `WSize` with no earlier `SetPopOut Y` in the same script. | warning | C §10 | [D hk, ~24 places; `WISDOM.md`] | draft |
| REQ-CHK-032 | The checker SHOULD warn on `NewWindow` not followed by `Wait(` before the next window call. | warning | C §10 | [V 2026-09-20, 5.8.2.5, `WISDOM.md`] | draft |
| REQ-CHK-033 | The checker SHOULD warn on `GetWindowObj()` called with no argument. | warning | C §11 | [V 2026-09-20, 5.8.2.5] | draft |

### Behaviour

| Id | Requirement | Source | State |
|---|---|---|---|
| REQ-CHK-040 | Each diagnostic SHALL carry file, line, column, a stable code, a severity and a message. | — | draft |
| REQ-CHK-041 | Line and column SHALL refer to the source file as written, not the one-line text the harness injects. | `das_script_test.py` | draft |
| REQ-CHK-042 | The exit status SHALL be 0 with no errors, 1 with one or more errors, 2 on a usage or file error. | — | draft |
| REQ-CHK-043 | The checker SHALL use the Python standard library only. | TECH-STACK | draft |
| REQ-CHK-044 | The checker SHALL run without a DAS connection and SHALL never open a socket. | C §1.2 | draft |
| REQ-CHK-045 | `das_script_test.py check` SHALL use the checker for its static pass, keeping its `--live` order-token refusal unchanged. | C §1.2 | draft |
| REQ-CHK-046 | All 13 files in `scripts/` SHALL check with zero errors, or each error SHALL be fixed in the script in the same increment. | §How this grammar was checked | draft |
| REQ-CHK-047 | Every §5 probe SHALL be a conformance fixture whose expected diagnostics match what DAS did, except where a requirement flags by design what DAS ran: REQ-CHK-016 (P1, P1b), 017 (F7), 018 (Q5), 020 (P7). | §5 | draft |
| REQ-CHK-048 | Each diagnostic code SHALL be documented with an example and its REQ id. | `INTENT.md` (diagnostic codes for completion) | draft |
