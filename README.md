# DAS-hotkeys

Advanced hotkey scripts, desktop layout, and signal research for **DAS Trader Pro**.

DAS ships a real scripting language behind the hotkey dialog — `$` variables, objects, `if`/`while`,
a one-second timer, and a startup script. It is **disabled by default** and documented almost
entirely in one 40-page PDF. This repo is what that language is actually good for.

---

## What's here

| Path | |
|---|---|
| `scripts/` | Seven `.das` scripts — desktop bootstrap, layout builder, signal detection, order entry |
| `docs/WISDOM.md` | What the 20 official DAS manuals actually say about scripting, with page citations |
| `docs/DESKTOP-FASHIONABLY-LATE.md` | Desktop design + build order for the Fashionably Late setup |
| `docs/manuals/MANIFEST.md` | Every official DAS manual with its source URL |
| `backtest/` | 3-year, 1-minute backtest of the FL signal |

## Scripts

| File | Goes in |
|---|---|
| `00-fl-desktop-load.das` | Setup → Hotkey → Scripts → **Desktop Load Script** |
| `01-fl-layout-build.das` | throwaway hotkey, run once |
| `02-fl-chart-update.das` | chart → right-click → **Chart Script** |
| `03-fl-locate.das` | append below `02` in the same Chart Script |
| `04-fl-hotkeys.das` | one hotkey per block |
| `05-fl-cst-test.das` | two throwaway hotkeys, run once by hand |
| `06-entry-with-slp-stop.das` | two hotkeys — long entry and short entry, each with a 1.5×ATR stop-limit |

## Things that cost time to learn

- **Advanced scripting is off by default.** Setup → Other Configuration → *Hotkey Advanced Script*.
- **`WPos`/`WSize` do nothing on a docked window.** `SetPopOut Y` first — stated ~24 times in the
  hotkeys guide and easy to miss every one of them.
- **Globals collide across chart windows.** Two charts overwrite each other's `$vars` mid-script.
  Per-chart state belongs on the window's own `data` object:
  `if (isObject(data) == 0) { data = NewUserObj(); }`
- **`while` caps at 200 iterations** and **`Send()` at one order per second.**
- **No user-defined functions.** Unbound named hotkeys called via `ExecHotkey()` are the substitute.
- **No `&&` or `||`.** Compound conditions are nested `if`.
- **No single quotes.** DAS rejects them outright.
- **`GetQuoteObj()` returns zeros** unless that symbol is open in a montage.
- **Study colors cannot be set from script.** Hot buttons, trendlines, and drawn lines can.
  `LoadSetting <file>.cst` swaps a whole saved chart configuration — the closest thing to
  repainting bars. See `05-fl-cst-test.das`.

## Backtest

`backtest/` replays the Fashionably Late signal over **4,929,583 one-minute bars**
(10 tickers, 2023-09-05 → 2026-09-04) and compares two definitions of the trigger.

Read `backtest/RESULTS.md` for the findings and — more importantly — the fidelity caveats.
Headline: on an *uncurated* universe both definitions lose, and ticker selection swamps the
choice of moving average by ~680R.

```bash
cd backtest
python3 -m venv .venv && .venv/bin/pip install pandas requests pyarrow
export POLYGON_API_KEY=...
.venv/bin/python fetch_bars.py        # ~110MB, not committed
.venv/bin/python backtest_fl.py --ref both
```

## Not in this repo

- **The DAS manuals themselves.** They are DAS|Inc's copyright. `docs/manuals/MANIFEST.md` lists
  all 20 with direct source URLs so you can pull your own copies.
- **Minute bars.** Polygon-licensed. `backtest/fetch_bars.py` regenerates them with your own key.
- **The CMD API specification.** Not public — it is released only after DAS certification.
  See the manifest for the approval path.

## Disclaimer

Research and tooling, not advice. Nothing here is a recommendation to trade. These scripts place
real orders — test every one on a SIM account before pointing it at live money, and read the
warning headers, which are there because the failure modes are specific and expensive.
