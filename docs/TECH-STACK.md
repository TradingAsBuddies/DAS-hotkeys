# Tech stack

What runs where, and why each piece is there. Nothing in this list is optional; anything not
in it is not part of the project.

## Trading platform

| Piece | Role | Notes |
|---|---|---|
| **DAS Trader Pro 5.8.x** (Cobra Trading build) on Windows | Executes every order, draws every chart, owns the session | Install dir `C:\Cobra Trading_x64`. Binds loopback only. |
| **DAS advanced hotkey script** | The language every `scripts/*.das` file is written in | Off by default: Setup → Other Configuration → Hotkey Advanced Script. No functions, no `&&`/`\|\|`, no single quotes, 200-iteration loops, one `Send()` per second. |
| **CMD API** (TCP, plain text, `CMDAPI:PORT` in `Config.cfg`) | Bars, quotes, positions, orders, and the `SCRIPT` command that runs hotkey text in a named window | Spec is certification-gated; David holds a copy privately. Watch-mode login for everything that is not an order test. |
| **DAS log file** `LOG\YYMMDDLog.txt` | The read channel: every API command, every `MsgLog`, every script error | The socket never returns script output. |
| **Paper account TR4425** | The only account automation may touch | Live account is never scripted. |

## Host side

| Piece | Role | Notes |
|---|---|---|
| **WSL2, mirrored networking** | Where Python runs | DAS is reachable at `127.0.0.1`; never derive the host from the routing table. |
| **Python 3.14 (Linux)** standard library only | `tools/das_script_test.py`, `tools/fl_forward_test.py` | Sockets, `statistics`, `json`, `pathlib`. No third-party packages in the tools. |
| **Python 3.14 (Windows)** + **pywinauto** | The one Windows-side job: find and dismiss DAS modal dialogs through UI Automation | `C:\Python314\python.exe`; the 3.13 install lacks pywinauto. |
| **`~/.claude/.env`** | `DAS_HOST DAS_PORT DAS_USER DAS_PASSWORD DAS_ACCOUNT` | Inline `" #"` comments stripped on read; never committed. |

## Data

| Source | Used for | Not used for |
|---|---|---|
| DAS `SB … MINCHART` / `Lv1` | Live bars, quotes, the market clock | — |
| DAS `%POS %ORDER %TRADE` | Fills, positions, end-of-day report | — |
| Polygon flat files (`backtest/`) | Historical 1-minute bars for the backtest | Anything live; 15-minute lag. |
| `C:\Cobra Trading_x64\GamePlan\GamePlan-YYYY-MM-DD.txt` | The day's traded universe | — |

## Reference material

| Piece | Where |
|---|---|
| 20 official DAS manuals (PDF) and their extracted text | `docs/manuals/`, `docs/text/`, both gitignored; sources in `docs/manuals/MANIFEST.md`; private Drive copy |
| Synthesis with page citations | `docs/WISDOM.md` |
| Community reverse-engineering of the CMD API | `github.com/misantroop/das-bridge`, superseded by the manual |

## Repository

| Piece | Role |
|---|---|
| Git, `main`, GitHub `TradingAsBuddies/DAS-hotkeys`, **public** | Releases are tags `vX.Y.Z` with GitHub release notes. No manuals, credentials, account details beyond the paper account, or private links. |
| `CLAUDE.md` | Working agreement for the AI collaborator: connection facts, corpus rules, what is verified. |
| `docs/CONSTITUTION.md` | The rules that do not change per task. |
