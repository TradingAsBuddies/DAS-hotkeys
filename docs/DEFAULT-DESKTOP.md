# Default Desktop — `montage1` and `hidden_chart1`

Two windows every advanced script in this repo can address by name. This is the base
layer; the Fashionably Late layout in `DESKTOP-FASHIONABLY-LATE.md` sits on top of it and
uses its own `fl*` names.

| Window | Type | Where | Purpose |
|---|---|---|---|
| `montage1` | Montage | popped out, top-left | The montage scripts trade through. `GetWindowObj("montage1")` |
| `hidden_chart1` | Chart | popped out, parked off-screen | A chart nobody looks at. Scripts read its studies: `GetWindowObj("hidden_chart1").GetStudyVal("...")` |

Names are exact: lowercase, underscore, no spaces. Window-name case sensitivity is not
documented, so do not rely on `Montage1` matching.

## Why a script can do this at all

Naming a window used to mean right-clicking its title bar. The advanced guide shows it is a
writable property on the window object:

```
NewWindow Montage;
$myMontage = GetWindowObj();
$myMontage.name = "montageWindow";
```
— *das-advanced-hotkey-guide.pdf p.13*

`GetWindowObj()` with no argument returns the window just created. That is the whole
mechanism `10-ensure-default-desktop.das` is built on.

## What "hidden" means

DAS has its own definition, and it is geometric:

> "Hidden windows include child windows that are out of the main window display area and
> pop out windows that are out of the monitor display area."
> — *das-hotkeys-guide.pdf p.21*

So `hidden_chart1` is a popped-out chart moved past the edge of every monitor with
`WPos 10000 10000`. It keeps updating. `StopChartUpdate` was rejected because the chart
exists precisely to feed `GetStudyVal()`.

To get it back on screen:

```
ShowAllHiddenWindows;
```
> "Move all hidden windows to the center of the screen." — *das-hotkeys-guide.pdf p.21*

Re-run HOTKEY A of `10` to park it again. It will not be recreated; the name still exists,
so only the position changes.

## Verified on David's build, 2026-09-20

HOTKEY A and HOTKEY B both produced the expected results. That settles the three questions
the manuals leave open:

| Question | Answer |
|---|---|
| `GetWindowObj("missing")` | Returns a non-object. `isObject()` is `0`, no script error. The guards in `00`, `06`, `07`, `08`, `10` are sound; the old comment in `02` saying it errors was wrong and has been corrected. |
| `GetWindowObj()` right after `NewWindow` | **Failed on first run**: `ScriptError:100 Missing Object` at the `.name` line, leaving an unnamed montage. `NewWindow` is asynchronous. `10` now does `Wait(500)` between the two, then checks `isObject` and stops with instructions instead of a raw error. |
| `.name` on a chart window | Writable, same as the montage. `hidden_chart1` came back by name. |
| `WPos 10000 10000` | Y held (10063), X was clamped to 6162, the virtual desktop edge. Off-screen either way, so hidden. `GetRect` reports left,top,right,bottom in a popup. |
| `WSize` after an off-screen `WPos` | Did not take: the window measured 135 × 62. `10` now sizes before it moves. |

## Procedure

1. **Enable advanced scripting.** Setup → Other Configuration → *Hotkey Advanced Script*.
2. **Bind the three blocks of `scripts/10-ensure-default-desktop.das`** to three hotkeys. A and B
   can be throwaway keys; keep C (`ShowAllHiddenWindows`) bound for good.
3. **If an earlier run left an unnamed montage or chart behind**, close it first, or name it
   by hand (right-click title bar → Name). Otherwise you end up with a spare window.
4. **Press HOTKEY A.** It creates and names whichever of the two windows is missing, seeds
   the chart with the montage's symbol, and pops a MsgBox telling you what it did.
5. **File → Save Desktop.** Not optional:
   > "Give Montage window a name and then save desktop so restarting DAS will keep montage
   > name" — *das-advanced-hotkey-guide.pdf p.35*
6. **Add studies to `hidden_chart1`.** Press HOTKEY C to bring it on screen, then Chart →
   Study Config.
   Study configuration is not scriptable. Name each study in the Name field; that string
   is what `GetStudyVal()` resolves.
7. **Press HOTKEY A again.** It re-parks the chart on every press, created or not. Then
   **File → Save Desktop** again.
8. **Press HOTKEY B** whenever you want proof: it logs `isObject`, title, and name for both
   windows and runs `GetRect` on the chart. The title and name lines must say `montage1`
   and `hidden_chart1`.

`00-fl-desktop-load.das` checks for both names on every startup and pops a MsgBox naming
whichever is missing. It never creates them.

## Constraints specific to this feature

- Unique names. "We cannot use the same name for different windows." — *adv guide p.13*
- Geometry is literal in `10`. Whether `WPos` expands `$variables` is still undocumented and
  untested; every manual example uses literals.
- Repo-wide rules (no single quotes, no `&&`/`||`, `SetPopOut Y` before `WPos`) are in
  `WISDOM.md` and `CLAUDE.md`.

## Open naming split — decide before building on this

`06`/`07`/`08` and `04` F1 already address `montage1`. `01` builds a montage at the same
0,0 520×900 geometry and asks you to hand-name it `flMontage`, which `04` F11/F12 read.
Run both `01` and `10` and you get two montages stacked at the same pixel under two names.
`10` proves naming is scriptable, so the clean fix is for `01` to set `.name` itself and
for one name to win. That is a separate change; nothing here decides it.
