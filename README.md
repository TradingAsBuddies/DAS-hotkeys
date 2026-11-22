# DAS-hotkeys

Advanced hotkey scripts, desktop layout, and signal research for **DAS Trader Pro**.

DAS ships a real scripting language behind the hotkey dialog — `$` variables, objects, `if`/`while`,
a one-second timer, and a startup script. It is **disabled by default** and documented almost
entirely in one 40-page PDF. This repo is what that language is actually good for.

---

## What's here

| Path | |
|---|---|
| `scripts/` | `.das` scripts — desktop bootstrap, layout builder, signal detection, order entry, montage buttons, bracket-at-fill and the montage3 desk buttons |
| `docs/spec/grammar.md` | The language grammar (draft): EBNF with every rule tagged documented, verified or inferred |
| `docs/WISDOM.md` | What the 20 official DAS manuals actually say about scripting, with page citations |
| `docs/DEFAULT-DESKTOP.md` | The base layer: `montage1` and `hidden_chart1`, named from script |
| `docs/CMD-API-TESTING.md` | Driving and observing hotkey scripts from Python over the CMD API |
| `tools/das_script_test.py` | The harness: inject script, read DAS's log, clear error dialogs, fetch bars; `doctor` is the preflight |
| `tools/das_alerts.py` | DAS price alerts over the CMD API: dry-run by default, idempotent `--send`, IsObj-guarded read-back, log audit (`docs/CMD-API-ALERTS.md`) |
| `tools/das_layout.py` | Builds DAS windows by script from a JSON layout: create, name, size, place, chart symbol/timeframe/`.cst`, montage clones with buttons, button faces; dry-run by default (`docs/LAYOUT-BY-SCRIPT.md`) |
| `tools/gen_cst.py` | Copies a saved chart setting (`.cst`) and patches moving-average periods, types and study names (the names `GetStudyVal()` uses); `list` shows a file's studies (`docs/LAYOUT-BY-SCRIPT.md`) |
| `tools/gen_htk.py` | Reads and writes DAS `.htk` hotkey files; builds dashboard hotkeys from `scripts/htk/*.json` into `scripts/local/` |
| `tools/four_box_feeder.py` | Writes Market Vision's SPY four-box read into the `dash_box` hot button over the CMD API; UNAVAILABLE when there is no fresh read. Display only |
| `tools/fl_forward_test.py` | Forward-test driver: scans the day's gameplan on DAS bars, injects the FL scripts, closes at EOD, writes a report |
| `docs/ROADMAP.md` · `docs/TECH-STACK.md` · `docs/CONSTITUTION.md` | Where this is going, what it runs on, the rules that do not change |
| `docs/forward-tests/` | One dated log and report per forward test |
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
| `10-ensure-default-desktop.das` | three hotkeys — A creates/names `montage1` and `hidden_chart1` if missing, B verifies, C un-hides. See `docs/DEFAULT-DESKTOP.md` |
| `20-fl-long.das` / `21-fl-short.das` | FL entry with a 1.5×ATR stop-limit, driven by `$FL_SYM` / `$FL_QTY` / `$FL_ATR`; injected by the driver or bound to a hotkey |
| `22-fl-flatten.das` | per-symbol close at any hour; `Panic` refuses outside market hours |
| `30-load-shares.das` | montage buttons — LOAD 10/20/30/40/50/100, sets the share box |
| `31-buy-ask-slp.das` / `32-buy-bid-slp.das` | montage buttons — Buy ASK/BID 10 and 50, each with an 11c SLP stop from the fill; unfilled BID remainder is cancelled |
| `33-risk-buy-bid.das` | montage buttons — R$7 / R$15 BID buys and R$10 LOAD, sized to 1.5×ATR |
| `34-cover-pct.das` | montage buttons — cover 100/50/25% of a short at ASK or BID; refuses unless short |
| `35-buy-ask-range.das` | hotkey — buy at ASK+8c on REB25L, then a range exit from the fill: market stop −0.50, limit target +1.50; flat only, regular hours |
| `36-short-bid-range.das` | hotkey — short at BID−8c on REB25L, then a range cover from the fill: market stop +0.50, limit target −1.50; mirror of `35` |
| `40-bracket-at-fill.das` | montage button, two blocks (long, short): entry plus a 1.5×ATR SLP stop on the **filled** quantity, sized to 1R for the montage's account. R comes from `tools/baf_rconfig.py` (private Desktop Load snippet). UNVERIFIED until a SIM test; see its header |
| `41-montage3-atr-entry.das` | montage3 buttons LONG / SHORT 1ATR: sized from the per-account R, limit 5c through the touch on the montage route, stop sent at the fill with no confirmation box, order id read back, then named rays drawn at 1R, 2R and 3R |
| `42-montage-exits.das` | montage3 buttons CANCEL / FLATTEN: through the account and an order object, so they work while the montage is locked |
| `43-montage3-targets.das` | montage3 button 1R 2R 3R: replaces the stop with three range orders, a third each, targets at 1, 2 and 3 × the R taken at entry |
| `44-montage3-ah-stop.das` | montage3 button AH STOP: swaps the resting orders for one LimitP stop for the whole position |

## Things that cost time to learn

- **Advanced scripting is off by default.** Setup → Other Configuration → *Hotkey Advanced Script*.
- **`WPos`/`WSize` do nothing on a docked window.** `SetPopOut Y` first — stated ~24 times in the
  hotkeys guide and easy to miss every one of them.
- **Globals collide across chart windows.** Two charts overwrite each other's `$vars` mid-script.
  Per-chart state belongs on the window's own `data` object:
  `if (isObject(data) == 0) { data = NewUserObj(); }`
- **`while` caps at 200 iterations** and **`Send()` at one order per second.**
- **No user-defined functions.** Unbound named hotkeys called via `ExecHotkey()` are the substitute.
- **`&&` and `||` share one precedence.** Undocumented, but they work: `a || b && c` means
  `(a || b) && c`. Parenthesise every mixed condition. (Verified on 5.8.4.4, 2026-10-15.)
- **DAS executes before it rejects.** Statements before a syntax error have already run.
  Lint first: `tools/das_script_test.py check`.
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

- `tools/das_tape_profile.py SYM` — read-only Level 2 / time-and-sales recorder with a rolling day profile (`docs/forward-tests/tape/`).
