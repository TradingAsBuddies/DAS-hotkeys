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

## Next

1. **Stop width.** 1.5 × ATR(14) on 1-minute bars stopped every trade on 09-24, two of them
   inside 30 seconds. Candidates: ATR on 5-minute bars, a floor of 0.5% of price, or a
   required close beyond the reference line. Decide with a backtest run, not a guess.
2. **Second forward test (2026-09-25, session to 12:00 ET)** with the VOLD filter and SIM R;
   results file and verdict.
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
