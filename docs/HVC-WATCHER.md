# HVC Watcher for DAS Trader

A daily scan that ports Major Hayden's TradingView indicator
[`hvc_watcher`](https://github.com/major/tradingview/tree/main/hvc_watcher) (Apache-2.0,
see `tools/hvc/NOTICE`) and delivers its results into DAS Trader Pro.

DAS has no Pine equivalent. Advanced scripts can read bars (`GetBar`), but loops cap at
200 iterations and only see loaded chart history, so HVE can't be computed inside DAS.
The math runs in Python on Massive daily bars, and DAS receives the outputs.

```
Massive daily bars ─► engine.py (pure port, parity-tested) ─► hvc_daily.py
                                                               ├─ GamePlan\HVC-Events-Today.txt   (Market Viewer → Load)
                                                               ├─ GamePlan\HVC-Touches-Today.txt
                                                               ├─ chart rays    --draw-window <chart>
                                                               ├─ price alerts  --alerts
                                                               └─ chart book    --chartbook (or chartbook.py)
```

## Signals (same as the Pine)

| Signal | Rule |
|---|---|
| **HVC** | Confirmed bar, volume > 0, volume ≥ multiplier × SMA(volume, 20). SMA includes the current bar. Daily multiplier 3.0x. |
| **HVE** | Confirmed bar, volume > 0, strictly greater than every earlier bar's volume (ties don't count). |
| **Ray** | One level per event at the bar's **close**; HVE kind wins when both fire. Newest `--ray-limit` (5) kept. |
| **Touch** | A later bar with `low ≤ level ≤ high`. Checked before a new ray evicts the oldest. A bar never touches its own ray. |

## Usage

```sh
# Preview everything, no socket opened
python3 tools/hvc/hvc_daily.py --symbols NVDA,SMCI,SPY --dry-run

# Today's game plan, rays in a chart named hvc_chart, alerts on every retained ray
python3 tools/hvc/hvc_daily.py \
    --symbols "/mnt/c/Cobra Trading_x64-NEW/GamePlan/GamePlan-Today.txt" \
    --draw-window hvc_chart --alerts
```

Run after 20:00 ET for final daily bars. Before that, today's bar is kept as *unconfirmed*:
it can touch older rays but cannot create an event, as in the Pine.

| Flag | Default | Notes |
|---|---|---|
| `--sma` / `--mult` / `--ray-limit` | 20 / 3.0 / 5 | Same defaults as the indicator. |
| `--hve-warmup BARS` | 252 | No HVE in the first N bars. `0` = exact Pine behaviour (see below). |
| `--hve-lookback-years N` | all | Trim history, e.g. to match a TradingView chart's loaded history. |
| `--clear-lines` | off | `RemoveAllTrendLines` before drawing. **Deletes your own lines on that symbol too.** |
| `--alert-field` | `L1 LAST` | `AddItem` field name. Unverified live (see below). |
| `--list-dir` | `<DAS_ROOT>\GamePlan` | Where the Market Viewer lists go. |
| `--offline` | off | Use cached bars in `backtest/bars/daily/` (gitignored: licensed data). |

Exit codes: `0` ok · `1` a symbol's data failed or DAS reported a script problem ·
`2` DAS unreachable or login refused (never reported as "no events").

## Chart book

`--chartbook` (or `python3 tools/hvc/chartbook.py [--report …] [--bars 260]`) writes
`tools/hvc/out/chartbook-<date>.html`: one page per scan and one chart per symbol, ordered
events first, then touches, then everything else. It's drawn with TradingView Lightweight
Charts v5.2.1.

- **Candles**, with HVC 🟠 and HVE 🟢 markers labelled with their multiplier, and a small blue
  ▲ under each bar that touched a retained ray.
- **Retained rays** as price lines, plus a table that marks levels **not reached** by the
  bars shown.
- **Volume pane** with event bars coloured and the HVC threshold (SMA × multiplier) dashed.
- **Light and dark** themes follow the OS.

The page loads the library from unpkg with a pinned version and SRI hash. For an offline
page, pass `--inline-lib <lightweight-charts.standalone.production.js>`. The charts are
recomputed from the cached bars with the report's parameters. If the cache has been
refreshed since the report, the symbol shows a red "cache newer than report" badge.

**The page embeds Polygon OHLCV.** It stays in the gitignored `out/` directory. Don't
commit it, attach it, or publish it. Anything public (docs, examples) must use synthetic
bars, like `test_chartbook.py` does.

## Nightly book (game plan → Notion)

Every weekday at **20:15 ET**, `tools/hvc/run_nightly.sh` runs:

```sh
hvc_daily.py --gameplan --symbols tools/hvc/watchlist.local.txt --chartbook --notion
```

- **Targets.** The newest `<DAS_ROOT>\GamePlan\GamePlan-YYYY-MM-DD.txt`, written by the
  morning game plan, plus the standing list in `tools/hvc/watchlist.local.txt`
  (gitignored, one ticker per line), with duplicates removed. To change tomorrow's book,
  change the game plan or edit the standing list.
- **Outputs.** The Market Viewer lists, `out/chartbook-<date>.html`, and a private Notion page
  "HVC Chart Book · <date>" under **HVC Chart Books** (`HVC_NOTION_PARENT` in
  `~/.claude/.env`). Re-running a date archives that date's page (Notion trash, restorable for
  30 days) and publishes a fresh one.
- **Why 20:15 ET.** Massive's daily bar is final after 20:00 ET, so events are confirmed.
  It doesn't draw rays or create DAS alerts, because those need a live DAS session.
- **Notion access.** `notion_publish.py` uses the REST API with `NOTION_API_KEY`. That
  integration must keep access to the parent page.

Install the timer (the units are in `tools/hvc/systemd/`):

```sh
ln -sf ~/Projects/DAS-hotkeys/tools/hvc/systemd/hvc-nightly.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now hvc-nightly.timer
systemctl --user list-timers hvc-nightly.timer      # next run
journalctl --user -u hvc-nightly -n 50              # last run's output
```

Exit codes mark the unit failed when a symbol's data failed (1) or Notion failed (3). The
local book is still written in both cases.

## DAS setup

1. Setup → Other Configuration → **Hotkey Advanced Script** on.
2. Pop out a chart and name it, e.g. `hvc_chart` (see `DEFAULT-DESKTOP.md` for naming).
3. `DAS_ROOT` in `~/.claude/.env` must point at the install DAS is actually running from.
   The Market Viewer lists are written under it.

Sending uses `tools/das_script_test.DAS`: watch-mode login, paper account only.
Every payload is screened for order and desktop tokens before it's sent.

## Differences from TradingView

1. **HVE history.** TradingView's HVE is a record over the chart's loaded history. Here it's
   a record over what Massive returns: currently **5 years** on this plan, even though 20 are
   requested. The first bars of any history are trivially records. In the Pine they fill the
   ray slots with noise, which is why the CLI default `--hve-warmup 252` suppresses them.
2. **Touch delivery.** TradingView alerts on a bar whose range includes the level. DAS alerts
   fire when Last crosses toward the level from the side the close was on (`>=` above,
   `<=` below). That's the same intraday event. Re-running the scan re-arms the alerts.
3. **Volume source.** Massive consolidated volume, including extended hours, can differ from
   TradingView's feed, so bars near the threshold can flip.
4. **No markers or labels.** DAS draws the rays. Multipliers are in the console and the
   `tools/hvc/out/<date>.json` report.

## Unverified live

The DAS script calls follow the advanced hotkey guide (`DrawHorzLineWithPrice`, `SYMBOL`,
`NewAlertObj` / `AddItem` / `save`), but haven't been run against DAS yet:

- ~~`AddItem` field spelling~~: `"L1 LAST"` created and read back on 5.8.4.8, 2026-11-19
  (`docs/CMD-API-ALERTS.md`).
- Whether drawing right after `SYMBOL X` lands on the new symbol (1.5 s pause between them).
- Duplicate alerts on re-run: alert names are deterministic, but whether DAS replaces or
  duplicates by name is unknown. Don't use `$a.Reset()` to clean up until it's confirmed
  what that clears.

Verify with `tools/das_alerts.py check "<alert name>"`, never with `eval` on
`GetAlertObj(...).Symb`, which freezes the API when the name is missing.

## Tests

```sh
python3 -m unittest discover -s tools/hvc
```

`test_engine.py` holds Major's PineTS fixtures, ported case by case: thresholds, warm-up,
zero or missing volume, HVE ties, unconfirmed bars, close anchors, touch boundaries, gaps,
retention at 1/5/200, and a retiring ray. `test_outputs.py` covers payloads, the order-token
filter, list files, and the CLI exit codes, all offline. `test_chartbook.py` covers the
series, markers, rays, the "not reached" label, the stale badge, the SRI pin, the
`</script>` escaping, and the offline library option, using synthetic bars only.
