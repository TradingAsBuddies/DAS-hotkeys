# Roadmap

Small increments, each shippable on its own. Done items stay here with their release so the
history reads top to bottom.

## Done

| Increment | Release |
|---|---|
| Manual corpus fetched, extracted, synthesised (`WISDOM.md`) | pre-release |
| Fashionably Late desktop layout, coil detector, signal locator, order-entry hotkeys (`00`–`08`) | pre-release |
| 3-year, 1-minute backtest of the FL signal (`backtest/`) | pre-release |
| Default desktop named from script: `montage1`, `hidden_chart1` (`10`) | v0.1.0 |
| CMD API test harness: inject, observe via DAS log, clear dialogs (`tools/das_script_test.py`) | v0.1.0 |
| Runtime script errors surfaced; MsgBox and notice dialogs dismissed; honest safety claims | v0.1.1 |
| FL trading scripts driven over the API: long, short, per-symbol close (`20`–`22`) | v0.2.0 |
| Forward-test driver across the day's gameplan with JSONL log and report (`tools/fl_forward_test.py`) | v0.2.0 |
| First forward test (2026-09-24): verdict not successful; 13 of 13 in-session round trips stopped | v0.2.1 |
| Signed positions from `%POS` Type, close side chosen by the driver, flatten on host sleep, report on exit | v0.2.1 |
| Breadth dashboard (`TICK$ JVNT$ ADVN$ DECN$ VIX$`) logged each cycle; `--vold-filter` on entry side | v0.2.1 |
| Second forward test (2026-09-25 to 12:00): no trades executed, target window lost its name; replay −1.3R over 10 | v0.2.2 |
| Every injection verified against the socket reply and the DAS log; loud halt when the target is gone | v0.2.2 |
| Week backtest on Massive flat files (`backtest/backtest_fl_week.py`): −51R, 62% of stops inside one minute; stop width is not the fix | v0.2.3 |
| Monday thesis tested: hold-N, first-cross, opposite-cross exit, 5-min trend, 5/15-min signal bars; every variant negative | v0.2.4 |
| 15-minute bars done properly (warm-up, RTH, end-of-day close): +7.5R this week on one trade, −9R prior week, −1.5R over two weeks | v0.2.5 |
| Exit review: MFE/MAE shows the 1-minute entry unsalvageable; on 15-minute entries a 0.75×ATR stop + breakeven at +0.5R is +14R over two weeks, positive both weeks; 9-EMA-close trails destroy the payoff | v0.2.6 |
| Three-year backtest on Massive flat files (740 days, 23 names): 1-minute −7,680R; 15-minute 1.5×ATR −310R; candidate +169R, every full year positive, but two cents of stop slippage halves it | v0.3.0 |

## Next

1. **Candidate rule confirmed thin over three years** (+169R paper, +270R with no entries
   after 15:00; friction-sensitive). Next: (a) measure real stop-fill slippage from the DAS
   execution log on the first twenty paper stops; (b) driver flags `--bar-minutes 15`,
   `--stop-mult 0.75`, `--be-after 0.5`, `--last-entry 15:00`, single stocks only, and a
   breakeven order update through `%OrderAct`; (c) the serverless harness in TELOS so the
   parameter grid runs as one submission instead of an afternoon. Before any further live run: either a
   different setup from `PlaybookSetups.md`, or the same tool pointed at the names and days
   where the cross did work (SPY, XOM, AMD, USO, DELL trend days) to find what they had in
   common. Also: join Friday's `$VOLD` log to Friday's bars for one day of breadth evidence.
2. **Per-name side rule from the gameplan** (runners long-only) and **no entries inside the
   last 15 minutes** of the session window, both learned on 09-25.
3. **Run the driver where the positions are.** Thursday's flatten was lost because the laptop
   left for a conference. Either the driver runs on the trader desk as a service, or entry,
   stop and EOD close move into DAS scripts (Timer Event) so the platform supervises its own
   positions. Until then the driver's ten-minute gap guard is the only protection.
4. **Hotkey file generation.** `*.htk` is plain text (`Key:Name:~ len:script` with
   `~0D~0A` escapes). Generate it from `scripts/*.das` so the paste step disappears.
5. **Trailing stop management** from the driver: `%OrderAct` shows the resting stop, so
   re-price it as ATR moves, the way `fl_trading_agent.py` does.
6. **Chart-with-studies from script.** `LoadSetting <file>.cst` may carry named studies; if
   it does, one saved `.cst` gives every hidden chart `ema9 / sma34 / atr / vwap` without the
   Study Config dialog, and a fully DAS-native timer version of the FL scan becomes possible.
7. **Signal parity check** between the DAS chart script (`03`) and the driver on the same
   bars, so a divergence shows up as a diff instead of a missed trade.
8. **Reconcile the two FL definitions**: 9-EMA × 34-SMA (this repo) versus 9-EMA × VWAP
   (`fl_monitor_spec.md`). One definition, one backtest, one driver.

## Later

- Paper-account order round trip in the harness (`NEWORDER` + `CANCEL` on a normal login)
  for scripts that must send an order to be tested.
- Session capture to CSV after each forward test, using the existing `das_session_capture.py`.
- A `--replay` mode for the driver that feeds recorded bars instead of live ones.

## Not planned

- Anything that touches an account other than TR4425 from automation.
- Publishing the DAS manuals or the CMD API specification in this repository.
