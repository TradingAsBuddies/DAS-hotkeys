# FL Backtest — 3 Years, 1-Minute Bars

**Run:** 2026-09-05 · **Window:** 2023-09-05 → 2026-09-04 · **4,929,583 one-minute bars**
**Universe:** the 10-ticker `fl_shared.WATCHLIST` — MSFT PANW NVDA DELL HPE AVGO CRWD SMCI SPY QQQ
**Logic:** replays `fl_trading_agent._tick()` with the reference line switchable.

---

## Headline

**Both definitions lose money on this universe. The 2026-09-05 switch to the 34-SMA made it
slightly worse, not better.**

| | trades | win rate | mean R | total R |
|---|---:|---:|---:|---:|
| **9-EMA × 34-SMA** (new) | 15,080 | 38.18% | **−0.0220** | **−331.2** |
| **9-EMA × VWAP** (old) | 15,080 | 38.53% | **−0.0182** | **−274.9** |

Head to head: **−56.3R worse** under the 34-SMA, and it beat VWAP on only **4 of 10** symbols.
That is not a decisive verdict either way — the per-symbol spread swamps the difference — but
nothing here supports the change on performance grounds.

---

## The three findings that matter more than the headline

### 1. Ticker selection dominates everything

Per-symbol totals under the 34-SMA, same logic, same window:

| symbol | total R | | symbol | total R |
|---|---:|---|---|---:|
| CRWD | **+242.1** | | AVGO | −4.8 |
| PANW | **+137.1** | | SPY | −47.2 |
| DELL | **+111.8** | | QQQ | −54.9 |
| MSFT | +19.8 | | NVDA | −104.3 |
| | | | SMCI | −192.7 |
| | | | **HPE** | **−438.1** |

The spread between CRWD and HPE is **680R** on identical rules. HPE alone accounts for more
than the entire net loss; drop it and the book is roughly flat. Whether FL works is mostly a
question of *what you point it at*, not which moving average it crosses.

### 2. 89% of these trades are not the FL setup

| trigger | trades | share | win rate | mean R |
|---|---:|---:|---:|---:|
| `cross` — the documented FL trigger | 1,611 | 11% | 33.6% | −0.022 |
| `sustained` — the bolt-on path | 13,469 | 89% | 38.7% | −0.022 |

The `sustained_long/short` branch — EMA held one side of the reference for 3 refreshes with an
expanding gap — fires nine times more often than the cross the spec describes. It was added to
catch tickers that had already crossed, and it has quietly become the strategy. Both paths lose
at the same rate, so this isn't the source of the loss, but you are not trading the setup you
documented.

### 3. It fires the maximum every single day

**2 round trips on all 754 trading days, for every symbol, in both modes.** `MAX_RT_PER_TICKER`
is the only thing stopping it. **100% of trades exit on a stop** — none survive to the EOD gate.

This is a strategy that is always in the market, not one that waits for a setup. Combined with
finding 2, the practical read is that the entry condition is too loose at 1-minute resolution.

---

## By year

| year | sma34 total R | vwap total R |
|---|---:|---:|
| 2023 (partial) | −126.9 | −136.7 |
| 2024 | **+70.5** | **+125.2** |
| 2025 | −113.2 | −226.3 |
| 2026 (partial) | −161.6 | −37.1 |

2024 is the only positive year under either definition. No stable regime edge.

---

## What this does NOT show — read before acting

**This is not how you trade FL.** The live watchlist is curated daily to catalyst names from
the gameplan. This applies FL indiscriminately to 10 fixed mega-caps for three straight years.
That is a *floor*, not a fair test of the strategy as operated. Finding 1 is the direct evidence
— the daily curation step is doing work this backtest deliberately removes.

Other gaps between this and production:

- **Refresh cadence.** Live updates `consec_above`/`conf_carry`/`prev_gap` on 45-second bar
  refreshes; this replays one per 1-minute bar. Live reaches `SUSTAINED_BARS=3` *sooner*, so
  production fires at least as often as shown, not less.
- **Fills.** Entries fill at the next bar's open ±$0.01. Live sends a marketable limit at
  last ±$0.15 that may not fill, may partial, or may fill better.
- **Stops.** Checked against bar high/low; live checks every `$Quote` tick. When a bar's range
  spans both the stop and a favourable extreme, this assumes **stop first** (pessimistic).
- **No commission.** Slippage is a flat $0.01/share per side.
- **Data source.** Polygon **REST**, not the flat files the falcon pipeline mandates. Flat-file
  access is unavailable on this machine — `FlatFilesClient` needs `MASSIVE_ACCESS_KEY` +
  `MASSIVE_SECRET_KEY`, only `MASSIVE_API_KEY` is present, and every local AWS profile returns
  403 against `files.polygon.io`.

---

## Bugs found and fixed during the run

**R-multiple explosion (fixed).** First pass reported `worst_R = −2.8e12`. Cause: `stop` is
rounded to 2dp while `entry` keeps full precision. On a run of ~14 flat premarket bars ATR
collapses toward zero, the rounded stop lands on the entry, and risk becomes a fraction of a
cent — so `R = move / risk` explodes. Fixed with `MIN_RISK = 0.02`, which rejects signals whose
ATR stop is under two cents wide. It rejected 16–96 signals per symbol. This mirrors live
invariant I-1 with a floor that is actually tradeable — **and it is a live-code gap too:** I-1
requires `current_atr > 0`, which a 0.001 ATR satisfies while producing an untradeable stop.

**Identical trade counts (not a bug).** Every symbol returning exactly 1,508 looked wrong. It
is finding 3: the 2-per-day cap binding on all 754 shared trading days.

---

## Reproduce

```bash
cd ~/Projects/DASTrader/backtest
set -a; source ~/.claude/.env; set +a
.venv/bin/python fetch_bars.py          # cached in bars/, ~100MB
.venv/bin/python backtest_fl.py --ref both
```

Outputs: `results/trades_sma34.csv`, `results/trades_vwap.csv`, `results/summary.json`,
`results/per_symbol.csv`.

---

## Suggested next cuts

1. **Re-run on the curated daily gameplan lists** instead of a fixed universe. That measures the
   strategy as actually operated and would confirm or kill finding 1.
2. **Disable the `sustained` path** and test the documented cross alone — 1,611 trades is a
   workable sample, and it isolates the setup from the bolt-on.
3. **Drop or blacklist the persistent losers.** HPE is −438R across three years and 30.8% win
   rate; `BANNED_TICKERS` already exists as the mechanism.
4. **Raise `MIN_RISK` into the live code** as an I-1 companion invariant.
