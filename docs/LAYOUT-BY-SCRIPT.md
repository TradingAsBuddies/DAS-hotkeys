# Building windows by script

The CMD API does two things: FIX-style order and account calls, and executing scripts and
hotkeys. Building a desktop uses only the second. Every window, its place on screen and its
content come from hotkey script text sent with `SCRIPT`. The tool is `tools/das_layout.py`.
Layout files live in `scripts/layout/` (the example) or the gitignored `scripts/local/`.

Evidence labels follow `docs/spec/REQUIREMENTS.md`: **[V]** seen on a build with the source
named, **[D]** documented in a manual, **[I]** inferred and untested.

## What a script builds

| Part | Script | Evidence |
|---|---|---|
| A window of any type | `NewWindow Montage` (or Chart, TimeSale, MarketView, Position, …) | **[V]** 2026-09-20, `10-ensure-default-desktop.das` |
| Its name | A **separate** send after a pause: `$w = GetWindowObj(); $w.name = "x";`. Over the CMD API on 2026-11-19, `Wait(500)` in the same script as `NewWindow` still returned the previous newest window. Three names landed one window late, one of them on DAS's Internal Message window. The tool now creates, pauses, checks the newest window's name and kind, then names it | **[V]** 2026-11-19 10:19 (failure), fix not yet run live |
| Size and place | `SetPopOut Y; WSize w h; WPos x y;`. Size before move | **[V]** 2026-09-20 |
| Title bar | `TitleBar Y` or `TitleBar N` | **[D]** adv guide p.9 |
| Montage symbol | `$w.SYMBOL = "SPY";` | **[V]** `10-ensure` |
| Chart symbol | `Symbol SPY` | **[D]** hotkeys guide p.15 |
| Chart timeframe | `MinuteChart 5 10d`, `DayChart 1d 150d` | **[D]** hotkeys guide p.15 |
| Chart studies, colours, panes | `LoadSetting ema9-and-sma34.cst`, a file saved from the chart's menu. `.cst` is binary, so the tool loads files you already saved and never writes one | **[D]** p.15. The install holds 9 `.cst` files |
| A montage with its buttons and their scripts | `DuplicateWindow`, run inside a template window, then rename the copy | **[D]** hot buttons guide p.12–13 |
| A button's face | `GetCustButObj("dash_box")`, then `.text`, `.BkColor`, `.FgColor` | **[V]** 2026-11-18 |
| A button's action | The button runs `ExecHotkey("name");`, and `tools/gen_htk.py` writes that hotkey | **[V]** format 2026-11-19; loading it is L3 |
| Linking windows | `$w.LinkColor = "Blue";` on each window. Same colour means linked: a montage symbol change moved the chart, and after the chart was set to Green it stayed put. `LinkTo` (mouse drag) is not needed | **[V]** 2026-11-19, drill windows with a control |
| Closing a window | `SCRIPT <name> Close;`. DAS refuses an unknown name, so nothing else closes | **[D]** adv guide p.9; the refusal is **[V]** |

## What a script cannot do

- **Create a button by command.** No command does it **[V 2026-11-18]**. But a whole button
  panel is a `.cbf` file that `tools/gen_htk.py cbf` writes, and DAS loads it from the button
  window's menu (one click) **[V 2026-11-19]**. See *Button panels* below.
- **Keep names across a restart.** Only File > Save Desktop does **[V 2026-09-28]**. The tool
  never saves the desktop, because that overwrites the operator's saved layout.

## Button panels (`.cbf`)

A montage's hot buttons save and load as one `.cbf` file from the button window's menu. The
format, read from a DAS 5.8.4.8 export and rewritten byte for byte: `cbffile`, version 36,
length, button count, then per button its name, text, script, type, width, text colour and
background colour (Windows BGR), and a 9-byte tail. `gen_htk.py cbf scripts/htk/montage3.json`
writes `scripts/local/montage3-montage3.cbf` from the manifest: each `button` entry becomes a
button running `ExecHotkey("<hotkey>");`, and `panels` adds display-only buttons such as
`dash_box`. **[V 2026-11-19]** the operator loaded a generated panel into montage3, and
`GetCustButObj` found all four buttons by name with their generated text.

## Chart settings (`.cst`)

Studies reach a chart only as a whole `.cst` (`LoadSetting X.cst`). No command adds one study;
`StudyConfig` only opens the dialog. `tools/gen_cst.py` copies
a `.cst` you saved and patches moving averages and study names:

```sh
tools/gen_cst.py list ema9-and-ema21.cst                      # studies: type, name, MA period/type
tools/gen_cst.py make ema9-and-ema21.cst --ma 2:sma:50 --name 1:EMA9 --name 2:SMA50 \
    -o scripts/local/ema9-sma50.cst --install
```

- A study record is u32 LEN, u32 2, a 20-byte **type** (`Moving Average`, `Price`), then the
  study's **name** as a NUL-terminated string, defaulting to the class (`StudyMovingAvg`).
  A moving average's name is followed by a u32 period and a u32 type (0 = SMA, 2 = EMA).
- **[V 2026-11-21]**, on paper:
  - patching EMA 21 to SMA 50 loaded and drew (t2);
  - writing a name into the *type* field loaded with no error, but the study vanished (t3);
  - renaming in Study Config changed only the name string and LEN, by the length
    difference (107 to 97), and the tool's rename produces that record byte for byte.
  - t5 (EMA 9 named `EMA9`, SMA 50 named `SMA50`, both generated) loaded and drew; Study
    Config listed `EMA9 / Moving Average / Expone@9` and `SMA50 / Moving Average / Simple@50`.
- **[V 2026-11-21 08:44 ET]** `GetStudyVal` reads generated names: on montage3_chart1 with
  t5 loaded, `SMA50` and `EMA9` each returned a price-level number. A name not on the chart (`ATR(14)`)
  returns **0 with no script error**, so a script must treat 0 as "study missing".
- While a chart's Configuration dialog is open, scripts sent over the API wait. Three sent
  from short-lived connections were never run after it closed; resent, they ran at once.
- A study missing from the template (VWAP, ATR) cannot be added: save a template that has it.
- A `.cst` holds an account ID and symbol history, so `*.cst` is gitignored and `list` prints
  neither.

## The tool

```sh
tools/das_layout.py build scripts/layout/example.json          # dry run: every SCRIPT line
tools/das_layout.py build FILE --send                          # create missing windows
tools/das_layout.py build FILE --send --reconfigure            # also re-apply place and content
tools/das_layout.py check FILE                                 # which windows exist
tools/das_layout.py close FILE --send                          # close this file's windows only
tools/das_layout.py script FILE -o scripts/local/layout.das    # one script for a hotkey
```

- `--send` skips a window whose name already answers. It confirms each new window by name,
  and reads the DAS log for script errors.
- It refuses order tokens, and the commands `SaveDesktop`, `SaveLayout`, `ClearDesktop`,
  `SwitchDesktop` and `Close`, in any payload it builds.
- The `.cst` names are checked against the install before anything is sent.
- `script` writes the same layout as one hotkey script, for the Desktop Load Script or a key
  pressed once.

## Live drills (paper, and not while trading: every new window takes focus)

1. `build scripts/layout/example.json --send` with the `lay_m2` entry removed. Expect three
   `created` lines, and the charts showing the studies from their `.cst` files.
2. Run it again. Expect `present` for every window.
3. Put `lay_m2` back. Does `DuplicateWindow` run from `SCRIPT montage1` and rename the copy,
   leaving `montage1` in place **[I]**? Does the copy keep its buttons?
4. `close scripts/layout/example.json --send`. Expect every `lay_` window gone and
   `montage1` untouched.
