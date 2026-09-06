# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

No source code yet. There is no build system, no test suite, no package manifest, and this is
not a git repository. Any build/lint/test commands must be added here once the first code
lands — do not assume they exist. What exists today is `INTENT.md` and the reference corpus in
`docs/manuals/`.

## Intent

Per `INTENT.md`: **DASTRADER scripts and explanations of scripts.** DAS Trader is the
desktop trading platform; its automation surface is the CMD API that DAS exposes over a
local TCP socket.

Current build targets, in David's words: **variables**, **montage alignment**, and **chart
alignment**.

## Reference manuals — `docs/manuals/`

16 official DAS PDFs (226 pages) retrieved 2026-09-03 from the dastrader.com manual index
pages. **Read `docs/manuals/MANIFEST.md` first** — it maps each file to its source URL and to
the build targets above.

Two things that manifest records and you should not rediscover the hard way:

- **The CMD API specification is not in this corpus and is not publicly downloadable.** It is
  released only after DAS certification (API Request Portal → certification form → review).
  Anything written against the CMD API before that is working from
  `github.com/misantroop/das-bridge`, which is community reverse-engineering, not a spec.
- **Grep `docs/text/`, never the PDFs.** All 20 are extracted to plain text there (373K chars)
  with `===== [file p.N] =====` page markers, via `pypdf`. poppler-utils is not installed and
  is not needed.

**`docs/WISDOM.md` is the synthesis** — what the corpus actually says about variables, montage
alignment, and chart alignment, with page citations. Read it before opening any PDF. The four
constraints it establishes that shape every script: advanced scripting is **off by default**;
`WPos`/`WSize` need `SetPopOut Y` first; `while` loops cap at **200 iterations**; `Send()` is
limited to **one order per second**.

## Existing DAS tooling lives outside this repo

Working DAS Trader scripts already exist elsewhere on this machine and are the reference
implementations to read before writing anything new here:

- `~/.claude/Tools/das_quote.py`, `~/.claude/Tools/das_flat_check.py`
- `~/falcon/dashboard/` — `das_market_viewer.py`, `fl_shared.py`, `fl_monitor.py`,
  `soxl_fl_monitor.py`

## DAS connection facts (learned the hard way, verified 2026-09-01)

Any new script that talks to DAS must get these right:

- DAS binds **loopback only**. Under WSL2 mirrored networking that means the Windows DAS
  instance is reachable at `127.0.0.1`, *not* the WSL default route. Do not derive the host
  from the routing table.
- Read the host from the `DAS_HOST` env var (set in `~/.claude/.env`), and **strip inline
  `#` comments** when parsing that file — split only on a whitespace-preceded `" #"` so a
  `#` inside a password survives. A comment left attached to the value makes
  `socket.connect()` fail with `encoding of hostname failed`.
- Do not hardcode the port; it has drifted (9910 → 3192) and hardcoding it has caused
  repeated outages.
- Connection failures must not be reported as "no data". Helpers that log a warning and
  return `[]` on a refused connection hide the real fault — distinguish *no connection*
  from *no bars*.
