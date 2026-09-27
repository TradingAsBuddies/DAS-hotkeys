# 34-SMA pullback in the premarket trend — three-year backtest, 15-minute bars

Tested 2026-09-27 on the Massive.com minute data already on disk (2023-09-25 to 2026-09-25,
754 trading days). Script `backtest/backtest_sma34_trend.py`.

**Verdict.** The setup as David described it, on a 15-minute chart that includes premarket bars,
does not work: −70.7R on 1,034 trades, win rate 35.5% against a breakeven of 35.7% for a 1.8R
target, negative in every parameter cell of a 27-cell sweep. **The same rule on a regular-hours
chart, where the 34-SMA is still the prior session's average and has not repriced for the gap,
is a modest, consistent edge: +50.7R on 576 trades, positive in all four years, both sides
positive, max drawdown 16.3R, and it survives five cents of stop slippage at +18.7R.** It is not
in the FL improved rule's class (+295R on the same names and span) but it is a different kind of
trade, a 41% win-rate pullback with a fixed target, and the two are not correlated by
construction.

## The rule as tested

| Element | Definition |
|---|---|
| Universe | 14 medium/large-cap single stocks from the recent gameplans: AMD BB CRWD DELL DRI INTC IONQ META MSTR NVDA RKLB SMCI TSLA XOM. No ETFs, commodities or small caps. |
| Premarket filter | Today's 04:00–09:29 volume ≥ 2× the median premarket volume of the prior 20 trading days |
| Direction | 9-EMA (15-minute) below the day's premarket VWAP → SHORT; above → LONG. Re-read every bar. |
| Entry | Limit at the 34-SMA of the last completed 15-minute bar, good for the next window, only when the last close and the 9-EMA are on the trade side of the SMA (a pullback to the level). Filled when a 1-minute bar touches it. |
| Stop | 0.75 × ATR(14, true range, 15-minute) |
| Target | 1.8R. Same-minute stop and target counts as the stop. |
| Session | Entries 09:45–15:00, flat at 15:55. One entry per name per day. |
| Sizing | 1R = $75, capped at 300 shares. |

Everything used for an entry, stop or target comes from bars completed before the window in which
the fill happens; an independent review of the fill logic found no look-ahead, fills never better
than the limit, and intrabar ambiguity resolved against the trader.

## Two charts, two results

| Chart bars | Trades | Win rate | P&L | R | Per trade | Max DD | Sharpe | Every year positive |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| All sessions from 04:00 (extended-hours chart) | 1,034 | 35.5% | −5,306 | **−70.7** | −0.068R | 103.9R | −1.18 | no (2024 −38, 2025 −48) |
| **Regular hours only 09:30–16:00** | 576 | 41.3% | +3,806 | **+50.7** | +0.088R | 16.3R | 1.02 | yes: 2023 +5, 2024 +21, 2025 +13, 2026 +12 |

Sharpe here is annualised over every trading day in the span, flat days included.

Why the difference matters more than the numbers: on an extended-hours chart the 34-SMA is
mostly premarket bars by 09:45, so it has already moved to the premarket price and sits under the
action. It is touched constantly (1,034 fills) and means nothing. On a regular-hours chart the
34-SMA at the open is the prior session's average price. On a heavy-premarket-volume day price
opens far from it, and a pullback to it is a retrace into yesterday's value, which is a level
other participants also watch. That is the level David's description is actually about: "the
SMA does not consider volume, but the price is still a relevant point."

## The all-sessions sweep: nothing rescues it

27 cells, premarket multiple {1.5, 2, 3} × stop {0.5, 0.75, 1.0} ATR × target {1.2, 1.8, 2.5} R,
plus nine single-flag variants. Best cell −35R, worst −91R; median −64R. Full table in
`backtest/results/sma34-sweep.md`. Also negative: gate 09:30, no entries after 11:00 or 12:00,
two entries per day, fill-through 1¢, shorts only, longs only, a 1–2 ATR cap on pullback depth,
and hold-to-close with breakeven instead of the target. The only positive slice was the
premarket ratio between 2 and 3 (+19R), and that was entirely 2026.

The premarket-ratio split runs backwards from the thesis on this chart: 2–2.5× +38R, and every
bucket above 2.5× negative. The heavier the premarket volume, the less the extended-hours
34-SMA holds.

## The regular-hours rule: neighbourhood and friction

| Change from the regular-hours base | Trades | R | Max DD | Read |
|---|---:|---:|---:|---|
| Base | 576 | +50.7 | 16.3R | |
| Stop 0.5× / 1.0× ATR | 576 | +50.3 / +32.3 | 16.4R / 13.2R | flat across the stop width |
| Target 1.2R / 2.5R | 576 | +41.2 / +40.2 | 21.1R / 15.9R | 1.8R is the best of three, not a spike |
| Premarket 1.5× / 3× | 947 / 313 | +54.3 / +11.3 | 28.3R / 19.4R | edge lives in the 2–3× band |
| Premarket 1–2× only | 1,157 | −23.3 | 53.1R | the volume filter is doing real work here |
| Gate 09:30 | 890 | +55.6 | 32.9R | more trades, double the drawdown |
| No entries after 11:00 | 191 | +19.4 | 12.3R | unlike FL, this one earns all day |
| Hold to close, breakeven at 0.5R (no target) | 576 | +61.4 | 16.6R | win rate 15%, more R; David's target is fine |
| Fill-through 1¢ | 548 | +46.9 | 16.3R | not a touch artifact |
| Shorts only / longs only (true side filter) | 332 / 292 | +33.0 / +25.8 | 11.2R / 10.0R | both sides carry |
| Warm-up 10 days | 576 | +50.7 | 16.3R | insensitive |
| **5¢ adverse slippage on every stop** | 576 | **+18.7** | 20.8R | survives; each year still positive (+1, +8, +4, +6) |
| 5¢ slippage and 1¢ fill-through | 548 | +17.0 | 20.3R | |

Commissions: 165,000 shares both sides, 11R at half a cent, 22R at a cent. Net of five cents of
stop slippage and a cent of commission the three years are roughly flat to +10R. This is a thin
edge that depends on fill quality, as every tight-stop rule on this data has.

**By hour** (regular-hours base): 09:45–10:00 −2.4R, 10:00–13:59 all positive (+22, +10, +12,
+16R), 14:00–15:00 −7.0R. The first bar is stale (the regular-hours 9-EMA has not caught up with
the gap yet, so the direction read lags) and the last hour cannot reach 1.8R before the close.
Restricting entries to 10:00–14:00 is the obvious next filter; it was not applied here because it
was found after the fact.

**Distribution:** 238 winners averaging +$100 (1.33R; many target fills are partial-R eod exits
and gap-through fills), 338 losers averaging −$59 (0.79R; the limit often fills better than the
level). The ten largest wins are 35% of the profit, against 50% for the FL candidate. Peak
same-day notional $82,000, average position $10,900.

## Against the FL rule on the same names

| Rule, same 14 names, same three years | Trades | Win rate | R | Style |
|---|---:|---:|---:|---|
| FL improved (15m cross, 0.75×ATR, BE at 0.5R, before 11:00) | 1,579 | 11.7% | +294.7 | first-hour momentum, runners |
| 34-SMA regular-hours (this test) | 576 | 41.3% | +50.7 | midday pullback, fixed target |

FL earns six times as much. But the 34-SMA rule trades at different hours (10:00–14:00), on
different days (only 1,920 of 10,990 symbol-days pass the premarket filter), in the opposite
direction to the move (a pullback, not a break), with a 41% win rate instead of 12%. If both are
traded, they do not stack drawdowns; that is worth something on its own.

## Caveats, in proportion

- **The regular-hours result was found by a flag in the sweep, not predicted.** The story about
  the unrepriced prior-session average is a plausible reading, not a proven mechanism. Treat the
  +50.7R as in-sample; the defence is that it is flat across stop, target, warm-up and fill
  assumptions and positive in all four years and on both sides.
- The premarket VWAP is volume-weighted minute closes, not trades.
- Touch equals fill at the default; the 1¢ fill-through row is the check.
- Universe is today's 14 names run backwards.
- ATR is a simple 14-bar mean of true range, not Wilder smoothing; DAS's ATR study will differ
  slightly.

## What this means

1. **Do not trade the setup off an extended-hours chart.** Three years, every cell negative.
2. **On a regular-hours chart it is a legitimate 1R experiment**, with David's own stop and target:
   premarket volume 2–3× the name's 20-day median, entry at the regular-hours 34-SMA between
   10:00 and 14:00, 0.75×ATR stop, 1.8R target. Expect about one fill every other day across the
   14 names, four wins in ten, and a thin edge that fills decide.
3. **Measure stop fills first**, same as for FL. Five cents is the difference between +51R and +19R.
4. Next build: `--entry-window 10:00-14:00` in the driver, and a walk-forward that chooses the
   premarket band on 2024 alone and reads 2025–2026 blind.

## Reproduce

```bash
cd backtest
python3 backtest_sma34_trend.py                              # extended-hours chart: -70.7R
python3 backtest_sma34_trend.py --rth-only                   # regular-hours chart: +50.7R
python3 backtest_sma34_trend.py --rth-only --stop-slip 0.05  # friction: +18.7R
python3 backtest_sma34_trend.py --rth-only --pm-vol-mult 1.0 --pm-vol-max 2.0   # quiet premarkets: -23.3R
# sweep: backtest/results/sma34-sweep.tsv (27 cells + 9 variants)
```

Each three-year run takes about 30 seconds.
