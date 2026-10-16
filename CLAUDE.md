# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

Git repo on `main`. `README.md` is the public-facing overview; this file is the working notes.

| Path | What it is |
|---|---|
| `scripts/00`–`05` | Fashionably Late (FL) desktop: load script, layout builder, chart coil detector, 9-EMA × 34-SMA trigger, operator hotkeys, `.cst` repaint test |
| `scripts/06`–`08` | Hand-pressed order entry with SLP stop-limit: 06 = ATR-sized long/short, 07 = buy fixed 11c, 08 = short fixed 11c (mirror of 07) |
| `scripts/10` | Ensures the default desktop has `montage1` and `hidden_chart1`, the two CMD API targets (`docs/DEFAULT-DESKTOP.md`) |
| `scripts/20`–`22` | Driven, not pressed: FL long, short, flatten. Injected into `montage1` by `tools/fl_forward_test.py` after it sets the `$FL_*` globals |
| `tools/` | Python over the CMD API: `das_script_test.py` (inject/eval/lint harness), `fl_forward_test.py` (forward-test driver), `das_tape_profile.py` (read-only L2 + T&S recorder) |
| `backtest/` | `fetch_bars.py` (Polygon REST), `fetch_flatfiles.sh` (Massive flat files), `backtest_fl.py`, `backtest_fl_week.py`, `backtest_sma34_trend.py`, `catalysts/` (SEC EDGAR); output in `results/` |
| `docs/` | `CONSTITUTION.md` (rules that never change, read first), `WISDOM.md`, `CMD-API-TESTING.md`, `ROADMAP.md`, `TECH-STACK.md`, `forward-tests/`, `playbook/`, `manuals/MANIFEST.md` |

There is **no build system or unit-test suite.** `.das` scripts are tested through the CMD API
harness, and order scripts are only ever tested by sending a real order on the **TR4425 paper
account** (`docs/CONSTITUTION.md` §1 — there is no dry run of an order script):

```bash
tools/das_script_test.py check scripts/<file>.das          # static lint, no socket needed
tools/das_script_test.py check scripts/<file>.das --live   # executes in DAS; refused for order code
```

Each script's header says where it goes and records what has been verified (account, symbol,
timestamp, fill). Keep those headers current; do not call a script verified unless a DAS log
line, socket reply, or header-recorded fill backs it.

Backtest commands (run from `backtest/`, uses its own `.venv`):

```bash
.venv/bin/python fetch_bars.py          # needs POLYGON_API_KEY; ~110MB, gitignored
.venv/bin/python backtest_fl.py --ref both
```

Gitignored on purpose: `backtest/bars/` (Polygon-licensed), `docs/manuals/*.pdf` and
`docs/text/` (DAS|Inc copyright). They exist locally but must never be committed.

## Intent

Per `INTENT.md`: **DASTRADER scripts and explanations of scripts.** DAS Trader is the
desktop trading platform; its automation surface is the CMD API that DAS exposes over a
local TCP socket.

Current build targets, in David's words: **variables**, **montage alignment**, and **chart
alignment**.

## Reference manuals — `docs/manuals/`

20 official DAS PDFs retrieved 2026-09-03 from the dastrader.com manual index
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
- **Grep `docs/text/`, never the PDFs.** Whatever has been fetched is extracted to plain text
  there with `===== [file p.N] =====` page markers, via `pypdf` (4 of 20 as of 2026-09-24). poppler-utils is not installed and
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

## DAS script pitfalls (learned on SIM, 2026-09-08)

Beyond `WISDOM.md` and the README's "Things that cost time to learn" list:

- **Long concatenated lines get mangled.** A 71-char order line arrived with 28 characters
  cut from its middle (`ScriptError:1 Function $sSend not exist!`). Build order strings in
  short `$s = $s + ...` steps and `MsgBox` the string before `Send()`. See `07` header.
- **`+` inside `Round()` threw `ScriptError:100 Invalid parameter`.** Negate first and use
  subtraction only: `$neg = 0 - $slip; Round($px - $neg, 2)`.
- **Read montage state via `GetWindowObj("montage1")`**, not bare properties. Order scripts
  assume the montage is named `montage1` and the ATR chart is `flChart1m`.
- **Position guard is mandatory.** Earlier buy/short scripts could open a naked opposite
  position; guard on the magnitude of `POS` before sending.
- **Argument order in SLP orders never flips between long and short — only the signs do.**
- **Stops anchor to the ASK at signal time, not the fill.** Open limitation (commit
  `cb5d243`): a fill at the entry limit instead of the ASK turns 0.11 intended risk into
  0.26, so `$entrySlip` is real slippage exposure. The fix is to anchor on fill price; its
  property name is still unknown (`ShowObject()` on the order/position object to find it).
  This note was dropped from the script headers in later commits, so it lives here now.

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
