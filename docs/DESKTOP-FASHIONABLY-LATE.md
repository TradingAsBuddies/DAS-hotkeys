# DAS Desktop — Fashionably Late

A window layout plus five scripts that locate the FL setup and flag 9-EMA / 34-SMA
convergence. Every command used is documented in `docs/manuals/`; anything unverified is
labeled as such in the script that uses it.

---

## What changed — 2026-09-05

Three decisions from David, and one defect I found and fixed while acting on them.

### 1. FL is now the 9-EMA × 34-SMA cross

`03-fl-locate.das` now crosses the 9-EMA against the **34-SMA**, not VWAP. VWAP stays charted
for context. `fl_monitor_spec.md` was updated to match.

**But the Python stack was not.** `fl_shared.py` has no 34-SMA anywhere — it tracks `prev_ema9`
and `prev_vwap`, and `grep -n 'sma\|34'` over it returns nothing. So `fl_monitor.py` and these
chart scripts are now watching for two different events on the same tickers, and cannot
corroborate each other. That divergence is recorded prominently in the spec rather than left
to be discovered mid-session. Closing it means adding a 34-SMA to `fl_shared.py` and swapping
the VWAP leg of the cross test.

### 2. Tolerance is ATR-relative

`data.tol = GetStudyVal("atr") * $FL_TOL_ATR`, defaulting to **0.5 × ATR**, floored at $0.05 so
an unwarmed ATR study can't collapse the band to zero. Needs an ATR study named `atr` in Study
Config. F2/F3 adjust the multiple live.

### 3. Color — I found two more mechanisms

You asked me to dig into the advanced hotkey material. I did, and there is more than I first
reported.

| # | Mechanism | Changes | Confidence |
|---|---|---|---|
| 1 | `getCustButObj(n).BkColor / .FgColor` | a hot button | **Documented, working example** |
| 2 | `LoadSetting <file>.cst` | the chart's saved configuration | **Documented command, ambiguous scope** |
| 3 | `SwitchTheme DAS_DARK` | the whole platform | Documented, too blunt for per-chart |

**`LoadSetting` is the one worth your time.** It's a scriptable chart command —

> "LoadSetting — Load .cst file. For example, `LoadSetting ChartSetting.cst`"
> — *das-hotkeys-guide.pdf p.16*

— and `.cst` files come from the chart's own right-click menu:

> "Save Screen Setting — Save a chart configuration as a .cst file."
> — *das-trader-pro-user-manual.pdf p.918*

So: save two chart configurations with different color schemes, swap between them from script
on a state change. That genuinely repaints the chart.

**What I can't tell you** is whether `.cst` captures *study* colors (your price bars) or only
*screen* colors (background, grid, labels). That sentence sits under a "Set Screen Colors"
heading but says "chart configuration," which is broader. The manual is ambiguous and I'm not
going to guess. **`05-fl-cst-test.das` is a hand-run procedure that settles it on your build**
in about five minutes. Until then `$FL_USE_CST = 0` and the swap is inert.

Worth noting: if it turns out to be background-only, that may actually read better. A
background wash is easier to catch peripherally than a bar color change.

Still true: **no command sets a study's color directly.**

### 4. Defect I shipped, now fixed — globals collide across chart windows

My first version stored `$FL_COIL`, `$FL_GAP`, and `$FL_SIDE` as globals. The hot buttons guide
p.13 warns against exactly that:

> "there is a possibility that TSLA window updates the global variable `$vwap`. Before it can
> set `$vwapDisplay` with `$vwap`, MSFT window updates `$vwap` with MSFT's vwap value... DAS
> recommends using the Data property to store such values."

With `flChart1m` and `flChart5m` both running, they would have overwritten each other — you'd
have seen the 5-minute chart's coil state on the 1-minute button, intermittently, in a way that
looks like a flaky indicator rather than a bug. All per-chart state now lives on each window's
own `data` object, created with `if (isObject(data) == 0) { data = NewUserObj(); }`.

Globals are now operator settings only — the ATR multiple, the mute flag, study names — things
that are deliberately identical everywhere.

## Layout

Coordinates assume 2560×1440 primary with a second monitor to the right. Change the numbers in
`01-fl-layout-build.das`; the structure holds at any size.

```
┌──────────────┬─────────┬───────────────────────────┬──────────────────┐
│              │         │                           │                  │
│  flMontage   │  flTime │      flChart1m            │   flChart5m      │
│  520×900     │  Sales  │      1100×900             │   616×900        │
│  order entry │  300×900│      PRIMARY SIGNAL       │   context        │
│  Level 2     │  tape   │  ema9·sma34·atr·vwap      │   same studies   │
│              │         │  [FLCOIL] [FLSIG] buttons │   no scripts     │
├──────────────┴─────────┴───────────┬───────────────┴──────────────────┤
│                                    │                                  │
│           flWatch                  │  flPositions  │   flAlerts       │
│           1100×500                 │  700×500      │   744×500        │
│           FL candidate list        │               │                  │
└────────────────────────────────────┴───────────────┴──────────────────┘
```

**The constraint that governs the whole layout**, repeated ~24 times in the hotkeys guide:

> "Note: WPos and WSize can only be used with windows that pop out."

`SetPopOut Y` before every `WPos`/`WSize`. Docked windows silently ignore both.

---

## Build order

Do these in sequence. Steps 2 and 5 are the ones people skip and then wonder why nothing works.

**1 — Enable advanced scripting.**
Setup → Other Configuration → **Hotkey Advanced Script**. Off by default. Until it's on, every
`$variable` in these files is a syntax error.

**2 — Build and name the windows.**
Bind `01-fl-layout-build.das` to a throwaway hotkey and press it once. Then right-click each
window's title bar and name it *exactly*: `flMontage`, `flTimeSales`, `flChart1m`,
`flChart5m`, `flWatch`, `flPositions`, `flAlerts`.

Names must be unique across the whole desktop — DAS cannot resolve a duplicate, and
`GetWindowObj()` will return the wrong window or nothing.

**Then File → Save Desktop.** Window names do not survive a restart otherwise, and the Desktop
Load Script will reference names that no longer exist.

**3 — Configure the studies on `flChart1m`.**
Chart → Study Config. Add four, and set the **Name** field exactly:

| Name | Study |
|---|---|
| `ema9` | Moving Average · EMA · period 9 |
| `sma34` | Moving Average · SMA · period 34 |
| `atr` | ATR · period 14 — **required**, drives the tolerance band |
| `vwap` | VWAP — context only since 2026-09-05 |

`GetStudyVal()` resolves by this string. A typo returns `0`, and a zero gap reads as perfect
convergence — the button would sit amber all day. `02` guards against this by treating a zero
on either leg as "no data", but get the names right anyway.

Repeat on `flChart5m` for consistency. No scripts attach there.

**4 — Create the hot buttons.**
Right-click the button row → New. Two Text-type buttons:

| Name | Purpose |
|---|---|
| `FLCOIL` | MA convergence state — driven by `02` |
| `FLSIG` | FL cross state — driven by `03` |

Names are case-sensitive in `getCustButObj()`. Make them wide; they display live numbers.

**5 — Install the scripts.**

| File | Goes in |
|---|---|
| `00-fl-desktop-load.das` | Setup → Hotkey → Scripts → **Desktop Load Script** |
| `01-fl-layout-build.das` | throwaway hotkey, used once |
| `02-fl-chart-update.das` | `flChart1m` → right-click → **Chart Script** |
| `03-fl-locate.das` | append below `02` in the same Chart Script |
| `04-fl-hotkeys.das` | one hotkey per block — see the file |
| `05-fl-cst-test.das` | two throwaway hotkeys, run once by hand |

**6 — Verify before trusting it.**
Press **F8** and **F9** (from `04`). They dump the real property sets of a bar object and the
chart window on *your* DAS build. `03` assumes a bar exposes `.Volume`, which the manuals never
confirm — they only ever show `.HI` and tell you to discover the rest with `ShowObject()`. If
volume is named something else, fix the two references in `03`.

**7 — Save the desktop again.** File → Save Desktop.

---

## Operator controls

| Key | Action |
|---|---|
| F2 / F3 | widen / tighten the coil band by 0.1 × ATR |
| F4 | mute / unmute spoken alerts |
| F5 | enable / disable the `.cst` chart color swap |
| F6 | draw both MAs as horizontal lines |
| F7 | snapshot **this chart's** ema9 / sma34 / atr / gap / band / coil / side |
| F8 | dump bar object properties — settles the `.Volume` question |
| F9 | dump this chart's `data` object |
| F10 | dump the chart window object |

---

## Tunables

Set in `00-fl-desktop-load.das`, adjustable live with F2/F3.

| Variable | Default | Meaning |
|---|---|---|
| `$FL_TOL_ATR` | `0.5` | convergence band as a multiple of ATR |
| `$FL_TOL_MIN` | `0.05` | dollar floor, guards an unwarmed ATR study |
| `$FL_VOL_MULT` | `1.5` | volume confirmation multiple, from your spec |
| `$FL_GATE_SEC` | `35100` | 09:45 local, seconds since midnight |
| `$FL_USE_CST` | `0` | chart color swap — leave off until `05` is run |

**`$FL_TOL` is the number to think hardest about.** You said "within +/-1" without units, and I
defaulted to $1.00 absolute. That is ~1.7% on a $60 stock and ~0.17% on a $600 one — the same
setting means very different things across your watchlist. Two alternatives, if absolute
dollars turn out to be wrong:

```
// percent of price
$FL_TOL = GetChartLv1("Last") * 0.005;      // 0.5% of last

// ATR-relative, which matches how the rest of your stack sizes risk
$FL_TOL = $FL_ATR * 0.5;                    // half an ATR
```

The ATR variant needs an ATR study named in Study Config and read via `GetStudyVal()`.

---

## Limits this build works around

| Limit | Where it bites |
|---|---|
| `while` caps at **200 iterations** | 20-bar volume average is fine; a 500-bar lookback is not |
| **One `Send()` per second** | why nothing here sends orders |
| No user-defined functions | shared logic goes in unbound named hotkeys, called with `ExecHotkey()` |
| No `&&` / `\|\|` documented | every compound condition is written as nested `if` |
| `GetStudyVal()` returns last value only | previous values persist in globals across updates |
| `GetQuoteObj()` returns zeros unless the symbol is open in a montage | not used here for that reason |

---

## Scope

These scripts **signal only**. Nothing sends an order.

FL order submission lives in `~/falcon/dashboard/fl_trading_agent.py` against SIM account
TR4425, and that spec's I-1 invariant forbids entry without a computed ATR — which a chart
script has no way to satisfy. Keeping execution there and signaling here is the right split.
