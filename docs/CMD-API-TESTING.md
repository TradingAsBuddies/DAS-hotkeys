# Testing hotkey scripts through the CMD API

How to drive, observe, and lint DAS hotkey scripts from WSL without touching the keyboard.
Everything below was verified live on 2026-09-24 against DAS 5.8.x (Cobra build) on the
TR4425 paper account. The harness is `tools/das_script_test.py`.

## The source that made this possible

The real **Frontend CMD API Manual** (2021 revision) sits in David's private Drive
`dastrader` folder. It documents a command the public reverse-engineering never mentions:

> `SCRIPT WindowName ScriptString…` Especially, if WindowName is "GLOBALSCRIPT", it means
> global script, not for specified window. Example: `SCRIPT Montage1 SYMBOL MSFT` …
> `SCRIPT GLOBALSCRIPT SwitchDesktop default`

So any hotkey-script text can be injected into a named window from Python. That is why the
default desktop carries `montage1` and `hidden_chart1`: they are the two addressable targets.

## The five channels

| Channel | What it gives you | Verified how |
|---|---|---|
| `SCRIPT <window> <text>` | Executes script in that window's context. `$variables`, `if`, object access all work. | `$dst_v = 42; MsgLog("dst var=", $dst_v);` produced `Log,dst var=42` within the same second. |
| `SCRIPT <name> …` reply | **Existence oracle.** Unknown name → `Wrong command, window name X does not exist!` Known name → silence. Names are case-insensitive. | `montage1`, `Montage1`, `MONTAGE1` all answered the same way. |
| `C:\Cobra Trading_x64\LOG\YYMMDDLog.txt` | **The event log as a file.** Every API command (`CMDAPILog`), every `MsgLog` (`Log`), every script error (`Error`). | Grep it from `/mnt/c/...`. This is the read channel; the socket never returns script output. |
| `MsgLog("tag=", expr)` + log grep | **Value return.** Read any property or function result out of a window. | `$w.BID` → `763.76`; `GetTicker()` on `hidden_chart1` → `SPY`. |
| `SB symbol MINCHART … LATEST 1` | Minute bars, plus `Lv1` quotes and `DAYCHART`. Ground truth to compare against what a script computes. | 379 `$Bar` lines for SPY in one call. |

## The one thing that bites

**A script error opens a modal dialog in DAS, and that dialog freezes the CMD API thread.**
Every command sent while it is up is queued; when the dialog closes they are logged in a burst
with the closing timestamp and none of them run. Symptoms: subscriptions return nothing,
`exists` checks hang, the log stops.

The socket never reports the error. The only way to see it is the dialog text, and the only
way to clear it programmatically is Windows UI Automation:

```
/mnt/c/Python314/python.exe   (has pywinauto; the 3.13 install does not)
Desktop(backend="uia") → DAS main window → descendants(control_type="Text") containing
"ScriptError" → parent → Button "OK" → .invoke()
```

`click_input()` does not work on that dialog; `.invoke()` does. `tools/das_script_test.py
dismiss` wraps this, and `run` / `check --live` call it unconditionally after every injection,
because the `Error` line is only written to the log at the moment the dialog closes.

## Small behaviours worth knowing

- **Unknown property reads do not error.** `eval montage1 '$w.NoSuchProp'` returned
  `Obj:TradeWindowObject`, the object's own type string. A typo in a property name looks
  like a value. `GetWindowTitle()` on a montage returns the same string, not the title bar.
- **Single quotes inside `//` comments survived a live run** of `00`, whose three quoted
  comments were stripped by the harness before injection. The rule stands for code.
- **`check --live` on `00` printed both of its startup messages** (`FL desktop loaded.`,
  `desktop-load: montage1 and hidden_chart1 present`), so a Desktop Load Script can be
  exercised on demand without restarting DAS.

## What does not work

- **`Shell` through `SCRIPT`.** Logged, executes nothing, writes no file. Do not plan on a
  file-based return channel; use `MsgLog`.
- **Timestamps.** The WSL clock and DAS's log stamps were 54 minutes apart. The harness
  uses a byte offset into the log file, never the clock.
- **UIA reading the Event Log pane.** It exposes no text. Read the file instead.
- **`GetWindowObj()` with no argument** returned the montage, not the chart that was created
  last, and during HOTKEY A it returned nothing at all until a `Wait(500)`. Treat it as
  unreliable; always address windows by name.

## Test loop for a script

1. **Static lint.** `das_script_test.py check scripts/NN.das` flags single quotes and
   `&&`/`||`, the two things DAS rejects outright.
2. **Preconditions.** `exists montage1 hidden_chart1` before anything else. The oracle is
   free and it is the failure mode that looks like everything else.
3. **Inject.** `run <window> '<script>'` for a snippet, or `check --live` to execute a whole
   file. Live mode is refused for any file whose code contains `BUY`, `SELL`, `SS`, `CXL`,
   `Send(`, `NewOrderObj`, `Panic`, `SwitchDesktop` or `ClearDesktop`: `SCRIPT` executes
   inside DAS, so there is no such thing as a dry run of an order script. Those get the
   paper-account round trip below.
4. **Observe.** New `Log` and `Error` lines print. `eval <window> '<expr>'` reads back any
   value a script would have used: `$w.BID`, `$w.POS`, `$w.GetStudyVal("atr")`.
5. **Assert against ground truth.** `bars SPY` gives the same minutes the chart is drawing
   from; compare a script's `GetBar(-1).Close` against the last `$Bar`.
6. **Clean up.** If an `Error` line appeared, the dialog is already dismissed. The file is
   injected as one line, so `Line:N` is always 1; find the source line from the quoted
   fragment after `Error at:`.

## Paper-account order round trip (designed, not yet run)

The harness logs in as a **watch** connection and has no order path by design. When order
scripts (`06`/`07`/`08`) need live testing on TR4425:

1. Inject the script with a far-off limit, e.g. `Price` 30% below `BID`, so nothing fills.
2. Read `%ORDER` / `%OrderAct` lines from the socket: id, side, price, route, status.
3. `CANCEL <id>` over the same socket (needs a normal login, flag `0`).
4. Confirm `%OrderAct … Canceled` and that `%POS` is unchanged.

Only TR4425. The harness refuses to run if `DAS_ACCOUNT` is anything else.

## Other things found along the way

- `Config.cfg` line `CMDAPI:PORT:3192` is the authoritative port. The harness warns if
  `~/.claude/.env` disagrees.
- `*.htk` hotkey files are plain text: `Key:Name:~ <len>:<script with ~0D~0A escapes>`.
  Generating them from `scripts/*.das` would remove the paste step. Not built yet.
- `default.dsk` saved 2026-09-20 contains `montage1` and `hidden_chart1`, but the live
  desktop on 2026-09-24 had an unnamed montage. The API renamed it back. **Save Desktop.**
- Something else on this machine already uses `SCRIPT frmMktViewer …`: the falcon market
  viewer. Its `DASClient` has the tab-delimiting and quoting rule this harness copies.
