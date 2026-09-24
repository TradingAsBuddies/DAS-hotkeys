# Testing hotkey scripts through the CMD API

How to drive, observe, and lint DAS hotkey scripts from WSL without touching the keyboard.
Verified live on 2026-09-24 against DAS 5.8.x (Cobra build) on the TR4425 paper account.
Claims marked **(log)** are backed by lines in that day's DAS log file; claims marked
**(socket)** were observed in socket replies, which DAS does not log. The harness is
`tools/das_script_test.py`.

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
| `SCRIPT <window> <text>` | Executes script in that window's context. `$variables`, `if`, object access all work. | **(log)** `$dst_v = 42; MsgLog("dst var=", $dst_v);` produced `Log,dst var=42` within the same second. |
| `SCRIPT <name> …` reply | **Existence oracle.** Unknown name → `Wrong command, window name X does not exist!` Known name → silence. Names are case-insensitive. | **(socket)** for the reply text. **(log)** for case: `Hidden_Chart1` and `HIDDEN_CHART1` both logged their `MsgLog` while `hidden_chart1` was the saved name. |
| `C:\Cobra Trading_x64\LOG\YYMMDDLog.txt` | **The event log as a file.** Every API command (`CMDAPILog`), every `MsgLog` (`Log`), every script error (`Error`). | Grep it from `/mnt/c/...`. This is the read channel; the socket never returns script output. |
| `MsgLog("tag=", expr)` + log grep | **Value return.** Read any property or function result out of a window. | **(log)** `$w.BID` → `763.76`; `GetTicker()` on `hidden_chart1` → `SPY`. |
| `SB symbol MINCHART … LATEST 1` | Minute bars, plus `Lv1` quotes and `DAYCHART`. Ground truth to compare against what a script computes. | **(socket)** 379 `$Bar` lines for SPY in one call. |

## The one thing that bites

DAS has two kinds of script error, and only one of them is dangerous:

| Error | Example | What happens |
|---|---|---|
| `ScriptError:100` (parse) | a single quote, `$x = ;` | **A modal dialog opens and the CMD API thread freezes.** Every command sent while it is up is queued and never runs; their log stamps vary. The `Error` line is written only when the dialog closes. **(log)** |
| `ScriptError:1` (runtime) | `$w.NoSuchProp` | Logged immediately, no dialog, execution continues, and the "value" that follows is the object's type string such as `Obj:TradeWindowObject`. **(log)** |

Symptoms of the frozen state: subscriptions return nothing, logins get an empty reply,
`exists` gets no reply and no log line (the harness raises rather than guessing).

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

- **A typo in a property name is a runtime error that still returns a value.** `eval
  montage1 '$w.NoSuchProp'` logged `ScriptError:1 … Properity NoSuchProp not exist!` and
  then `Obj:TradeWindowObject`. The harness prints the error and exits 1. `GetWindowTitle()`
  on a montage returns that same type string, not the title bar. **(log)**
- **`study hidden_chart1 atr` returns 0 on the current desktop** because no studies have
  been added to the hidden chart yet. 0 means missing, misnamed, or not warmed up.
- **Single quotes inside `//` comments survived a live run** of `00`, whose three quoted
  comments were stripped by the harness before injection. The rule stands for code.
- **`run` rewrites `MsgBox(` to `MsgLog(` before injecting**, because a MsgBox is a modal
  and would freeze the API the way a parse error does. That freeze is inferred, not yet
  observed: no MsgBox has been injected.
- **`check --live` on `00` printed both of its startup messages** (`FL desktop loaded.`,
  `desktop-load: montage1 and hidden_chart1 present`), so a Desktop Load Script can be
  exercised on demand without restarting DAS.

## What does not work

- **`Shell` through `SCRIPT`.** Logged, executes nothing, writes no file. Do not plan on a
  file-based return channel; use `MsgLog`.
- **Timestamps.** DAS stamps the log with its own server-synced clock; the WSL clock has
  been seen 54 minutes off it. The harness uses a byte offset into the log file, never
  the clock.
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

**Watch mode protects one thing only:** the socket's own `NEWORDER` command. Text injected
with `SCRIPT` runs inside DAS under whatever account DAS is logged into, and neither the
watch flag nor the harness's `DAS_ACCOUNT` check can stop it. The refusal list in
`check --live` and your own discipline in `run` are the only guards. When order scripts
(`06`/`07`/`08`) need live testing on TR4425:

1. Inject the script with a far-off limit, e.g. `Price` 30% below `BID`, so nothing fills.
2. Read `%ORDER` / `%OrderAct` lines from the socket: id, side, price, route, status.
3. `CANCEL <id>` over the same socket (needs a normal login, flag `0`).
4. Confirm `%OrderAct … Canceled` and that `%POS` is unchanged.

Only TR4425. The harness refuses to run if `DAS_ACCOUNT` is anything else, and the DAS
log's first line (`Login to OrderServer Successful!`) is where to confirm which session DAS
itself is in before any order test.

## Other things found along the way

- `Config.cfg` line `CMDAPI:PORT:3192` is the authoritative port. The harness warns if
  `~/.claude/.env` disagrees.
- `*.htk` hotkey files are plain text: `Key:Name:~ <len>:<script with ~0D~0A escapes>`.
  Generating them from `scripts/*.das` would remove the paste step. Not built yet.
- `default.dsk` saved 2026-09-20 contains `montage1` and `hidden_chart1`, but the live
  desktop on 2026-09-24 had an unnamed montage. The API renamed it back. **Save Desktop.**
- Something else on this machine already uses `SCRIPT frmMktViewer …`: the falcon market
  viewer. Its `DASClient` has the tab-delimiting and quoting rule this harness copies.
