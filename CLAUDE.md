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
  released only after DAS certification. **David holds a copy** (the "Frontend CMD API
  Manual", 2021 revision) in his private Google Drive; the location is in Claude's private
  memory notes, not in this public repo. Read it through the Drive connector; never copy it
  here. The plugin `cmd-api.md` predates it and is wrong about the port and about "one
  connection at a time".
- **CMD API facts verified live 2026-09-24** (details in `docs/CMD-API-TESTING.md`):
  `SCRIPT <window> <text>` runs hotkey-script text in a named window; DAS answers
  "window name X does not exist!" for unknown names; DAS logs every API command,
  every `MsgLog`, and every script error to `C:\Cobra Trading_x64\LOG\YYMMDDLog.txt`;
  a script-error dialog freezes the API until it is dismissed (UI Automation via
  `/mnt/c/Python314/python.exe` + pywinauto does that); the live port is
  `CMDAPI:PORT:<n>` in `C:\Cobra Trading_x64\Config.cfg`. Harness:
  `tools/das_script_test.py`.
- **Grep `docs/text/`, never the PDFs.** All 20 are extracted to plain text there (373K chars)
  with `===== [file p.N] =====` page markers, via `pypdf`. poppler-utils is not installed and
  is not needed.
- **Both `docs/manuals/*.pdf` and `docs/text/` are gitignored** (DAS copyright), so a fresh
  clone has neither. Where the manuals live:
  - **On this machine:** `docs/manuals/` in this repo, re-fetched 2026-09-20 (4 of 20 so far:
    advanced hotkey guide, hotkeys guide, hot buttons guide, user manual), with text in
    `docs/text/`.
  - **In David's Google Drive, private, owner-only:** a `DASTrader` folder (link kept in
    Claude's private memory notes, not here) holding `AdvancedHotkeyGuide.pdf`,
    `ChartStudies.pdf`, `Triggerordersmanual.pdf` and a `MANIFEST-das-manuals.md` listing
    what still needs copying in. **Never share that folder or any manual publicly; DAS|Inc
    governs their distribution.**
  - **Upstream:** the URLs in `docs/manuals/MANIFEST.md`.
  To regenerate: `curl -sL -o docs/manuals/<file> <url>` per manifest row, then in a venv
  with `pypdf` write one `.txt` per PDF with `===== [<file> p.N] =====` before each page's
  `extract_text()`. Fetched sizes must match the manifest's byte counts.

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
