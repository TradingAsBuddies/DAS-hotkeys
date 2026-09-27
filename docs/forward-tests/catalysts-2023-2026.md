# Catalyst attribution — do earnings and filings explain the trades? (2026-09-27)

**Question (David).** The PlayBooks name no market catalyst as a trigger. Across the backtest
trades, is performance related to earnings or SEC filings?

**Answer.** Yes, in opposite directions for the two setups, and both splits are statistically
distinguishable from chance.

- **34-SMA premarket trend:** earnings-reaction days are the losing subset. 84% of the universe's
  earnings sessions pass the 2× premarket-volume filter (earnings is what makes a heavy premarket),
  yet those trades lose −0.28R each while every other day makes +0.14R. **Exclude earnings and
  fresh-8-K days from this play.**
- **Fashionably Late:** catalyst days are 9% of the trades and 30% of the profit. Earnings-reaction
  days make +0.35R a trade and other-8-K days +0.24R, against +0.07R on days with no filing.
  **Prefer names with a fresh 8-K or an earnings release** for FL; the setup still works without one.

## Method

SEC EDGAR submissions API for each CIK (`backtest/catalysts/catalysts.py`, cached JSON under
`backtest/catalysts/edgar/`). An 8-K carrying item 2.02 (Results of Operations) is an earnings
release; its *reaction session* is the filing day if the filing was accepted before 09:30 ET, else
the next session. Other tags, applied to the same 24-hour window: `offering` (S-1, S-3, 424B),
`8-K` (any other 8-K or 6-K), `10-Q/K`. A trade day takes the highest-priority tag it matches
(earnings > offering > 8-K > 10-Q/K), else `none`. XOM is read from both its pre- and post-2026
CIKs. GRML and GLND have no 8-K history (foreign filers), so their days are `none` by construction.

Universe: the 14 single stocks (34-SMA) and 16 single stocks (FL) of the earlier reports.
Filing counts since 2023-08-01 range from 66 (GLND) to 1,491 (META, mostly Form 4s); earnings
sessions per name 12 to 17, TSLA 24 because its delivery-report 8-Ks also carry item 2.02.

## 34-SMA premarket trend (pre-open order, 1.0×ATR stop, 9-EMA exit; 733 trades)

| Tag | Trades | Share | Win rate | R | R per trade | Avg win | Avg loss |
|---|---:|---:|---:|---:|---:|---:|---:|
| earnings reaction | 58 | 8% | 21% | **−16.2** | **−0.28** | +2.21 | −0.93 |
| offering | 9 | 1% | 44% | +29.2 | +3.24 | +8.53 | −0.99 |
| other 8-K | 48 | 7% | 29% | −11.4 | −0.24 | +1.20 | −0.83 |
| 10-Q / 10-K | 6 | 1% | 33% | +2.0 | +0.33 | | |
| **none** | **612** | **83%** | 27% | **+82.8** | **+0.14** | +2.65 | −0.81 |

Earnings-and-8-K days together: 106 trades, −0.26R each (standard error 0.13); the chance of a
random 106-trade subset doing that badly is 1.7% (permutation test). By year the catalyst subset
is +2, −11, 0, −7R; the rest is +36, +8, +13, +45R. None of the fifteen largest wins came on an
earnings day; two (RKLB 2025-09-16, RKLB 2026-05-11, the PlayBook example) carried an `offering`
tag, an S-3 or 424B on file within the prior day, which for RKLB means its at-the-market
programme rather than a discrete event. Nine trades is not a sample; do not build on it.

Why this makes sense: the premarket filter is meant to find a name with a fresh reason to move.
On an earnings morning everyone has the same reason and the same levels, the opening range is
widest, and a resting limit at yesterday's 34-SMA is filled by the flush and stopped by the next
minute. On a non-earnings heavy premarket (a sympathy move, an upgrade, a sector headline, a
reaction to a peer's report) the level is respected more often.

**Rule change for the PlayBook:** skip any name that reported earnings after yesterday's close or
before today's open, and any name with an 8-K accepted in the prior 24 hours.

| 34-SMA premarket trend | Trades | Win rate | R | R per trade | Max DD | With 5¢ stop slippage |
|---|---:|---:|---:|---:|---:|---:|
| All trades | 733 | 27% | +86.5 | +0.118 | 35.4R | +35.3 |
| Earnings and 8-K days only | 106 | 25% | −27.5 | −0.260 | 39.4R | −33.5 |
| **Earnings and 8-K days excluded** | 627 | 28% | **+114.0** | **+0.182** | **26.7R** | **+68.8** |

Removing 14% of the trades adds 28R, cuts the drawdown by a quarter and doubles the
friction-adjusted result. The catalyst rule is the largest single improvement found for this
setup and it is structural, not tuned.

## Fashionably Late (15-minute, corrected rule; 2,282 trades)

| Tag | Trades | Share | Win rate | R | R per trade | Avg win | Avg loss |
|---|---:|---:|---:|---:|---:|---:|---:|
| earnings reaction | 86 | 4% | 13% | **+30.1** | **+0.35** | +3.86 | −0.40 |
| offering | 21 | 1% | 5% | +0.6 | +0.03 | | |
| other 8-K | 118 | 5% | 13% | **+28.9** | **+0.24** | +3.11 | −0.43 |
| 10-Q / 10-K | 11 | 0% | 9% | 0.0 | 0.00 | | |
| none | 2,046 | 90% | 10% | +141.6 | +0.07 | +2.45 | −0.42 |

Earnings-and-8-K days together: 204 trades, +0.29R each (standard error 0.10) against +0.07R
(standard error 0.02) on the rest; the chance of a random 204-trade subset doing that well is
0.4%. The uplift is in the winners, not the losers: the average catalyst-day winner is 3.1 to
3.9R against 2.45R, with the same 0.4R average loss, because the breakeven stop caps the downside
either way. Three of the fifteen largest wins were earnings reactions (SMCI 2024-01-19, RKLB
2026-05-08, MSTR 2024-04-30). By year the catalyst subset is 0, +16, +3, +11R; the rest −3, +100,
+11, +64R, so the non-catalyst trade is the bulk of the P&L and the catalyst trade is the richer
one per unit of risk.

| Fashionably Late (15m, corrected) | Trades | Win rate | R | R per trade | Max DD | With 5¢ stop slippage |
|---|---:|---:|---:|---:|---:|---:|
| All trades | 2,282 | 10% | +201.1 | +0.088 | 12.4R | +64.9 |
| **Earnings and 8-K days only** | 204 | 13% | +58.9 | **+0.289** | 6.1R | **+48.1** |
| Earnings and 8-K days excluded | 2,078 | 10% | +142.1 | +0.068 | 12.4R | +16.8 |

The friction column is the important one. Paper, the non-catalyst trades are 70% of the profit;
after five cents of stop slippage they are a quarter of it (+17R against +48R), because they
are ten times as many trades carrying the same per-stop cost. **With ordinary fills, FL is a
catalyst trade.** With excellent fills it works on any in-play name.

**Rule change for the PlayBook:** a fresh 8-K or an earnings release is a reason to *prefer* a
name when more FL signals fire than can be taken, and the condition under which the setup
survives realistic friction. Without one, take the trade only if your measured stop slippage is
under two cents.

## Caveats

- EDGAR items are self-reported by filers; a few earnings releases go out as press releases under
  item 7.01 or 8.01 only and are counted here as `8-K`, not `earnings`. That blurs the two catalyst
  rows toward each other, not toward `none`.
- The 24-hour window is a choice; events more than a day old (an earnings gap on day two) are
  `none`.
- No news-wire catalysts (upgrades, sector headlines, peer earnings) are in the data. The 34-SMA
  result says those are where its non-earnings heavy premarkets come from; that is an inference,
  not a measurement.
- Small cells (offering, 10-Q/K) are reported for completeness and carry no weight.

## Reproduce

```bash
python3 backtest/catalysts/catalysts.py          # cached EDGAR JSON; add --refresh to re-pull
~/.venvs/playbook/bin/python backtest/catalysts/catalyst_charts.py   # equity curves by tag, exclusion tables, permutation test
# built by backtest/catalysts/catalyst_charts.py, which also prints the exclusion tables)
```
