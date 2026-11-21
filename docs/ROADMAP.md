# Roadmap

Small increments, each shippable on its own. Done items stay here with their release so the
history reads top to bottom.

## Done

| Increment | Release |
|---|---|
| Manual corpus fetched, extracted, synthesised (`WISDOM.md`) | pre-release |
| Fashionably Late desktop layout, coil detector, signal locator, order-entry hotkeys (`00`–`08`) | pre-release |
| 3-year, 1-minute backtest of the FL signal (`backtest/`) | pre-release |
| 34-SMA premarket-trend pullback backtested three years on 15-minute bars (`backtest/backtest_sma34_trend.py`, `docs/forward-tests/sma34-trend-3y.md`): fails on extended-hours bars (−71R), +51R on regular-hours bars, +19R after 5¢ stop slippage | v0.4.0 |
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
| Structural filters from the splits: entries before 11:00 and single stocks only → +292R, drawdown 12.7R, Sharpe 3.5, survives 5¢ slippage at +198R; partial profits prove win rate cannot be bought | v0.3.1 |

## Next

-3. **Tape recorder (2026-09-28).** `tools/das_tape_profile.py SYM` records Level 2, time-and-sales and Level 1
   in watch mode and rewrites a day profile (volume by price, POC/value area, 15-minute bars with aggression,
   book imbalance, largest prints, venues) every five minutes; first used on KOD and MTEK. Next: a
   post-session summary that scores whether a news gapper held its value area.
-2. **Catalyst attribution (2026-09-27, `docs/forward-tests/catalysts-2023-2026.md`).** EDGAR 8-K join: the
   34-SMA play loses on earnings/8-K mornings (exclude them: +114R, +69R after slippage); FL earns 4× per
   trade on them and they carry the friction-adjusted edge. Next: an EDGAR check in the morning scan.
-2. **Four-box readout tile (2026-11-18, forum topic `four-box-readout`).** A DAS button cannot read a file, so `tools/four_box_feeder.py` reads Market Vision's `vision-log.jsonl` and writes the SPY box, plus QQQ when the two disagree, into the Text button `dash_box` on `montage1` over the CMD API. It colours the button by box and shows UNAVAILABLE for no read from today, STALE when older than 240 min. It never guesses and sends no order. Verified live on 11-18: the guarded write, a missing button reported without a dialog, colour names accepted (WISDOM). Runs as the systemd user service `tools/systemd/four-box-feeder.service`, started 2026-11-18. It dismisses only dialogs its own write caused; an operator's ScriptError dialog stays open. Not yet seen: a real session box on the tile (only premarket records so far); the face after a DAS restart; a long unattended run.
-2. **Alerts through the CMD API (2026-11-19, `docs/CMD-API-ALERTS.md`).** The API has no alert command, so alerts are `SCRIPT GLOBALSCRIPT` objects. `tools/das_alerts.py` makes them from a JSON plan: dry run by default; with `--send` it checks each name first, creates only the missing ones and reads each back, guarded by IsObj. The bare `GetAlertObj(x).Symb` froze the API on 11-19. `log` audits a day's alert activity from the DAS log alone. `das_script_test.py doctor` is the preflight. Verified live on 11-19: creation, read-back, the IsObj guard both ways, a skip on a present name. Open (drills 6 and 7): whether a fired alert is logged; whether alerts survive a restart; deleting one alert without `Reset`.
-2. **Hotkey dashboard (2026-11-19, `docs/spec/features/002-hotkey-dashboard/`).** Five display tiles on montage1 (four-box, session R, ladder level, per-symbol lockout, entry window) and five action buttons, and a gate: the feeder that paints the tiles also sets globals that every entry button checks first, so a LOSING_STREAK_POLICY stand-down or a 1R lockout refuses the order instead of only showing it. Exits never read the gate. Automation: `Hotkey.htk` is plain text and its `~ NNN` length prefix was verified on 11-19 against the live file, so the logic is generated (`gen_htk.py`, item 4) while the buttons are made once by hand as one-line `ExecHotkey` calls, saved in a desktop and cloned with `DuplicateWindow`. `.dsk` is binary and is not generated. Draft; live tests L1–L7 in `plan.md`; open questions: fail closed or open, and whether a feeder may read live-account `%POS`.
-2. **Bracket-at-fill montage button (2026-11-18, forum topic `bracket-at-fill`).** `scripts/30-bracket-at-fill.das`: marketable-limit entry sized to ⌊1R ÷ (1.5×ATR + entry slip + stop-limit slip)⌋ on the montage account, a 5 s fill poll, cancel of the working remainder, then an SLP stop on the filled position. R per account is generated from PREFERENCES R-CONFIG by `tools/baf_rconfig.py` into a gitignored Desktop Load snippet, never typed. Status BUILT; UNVERIFIED until the operator's SIM test (header U1–U6): `$m.Account` returns the montage account; `$m.POS` is that account's position; `.account` on a short-form order is honored (test on a montage whose account is not the order-template default); `CancelOrder("BUY|SELL", sym)` cancels a working SS entry; re-pinning `$m.SYMBOL` mid-script is harmless; the stop is accepted (nothing reads order status). Sizing counts whole shares with `while`, because `Round` documents no precision 0. Adversarial review 2026-11-18: 9 findings, all addressed before BUILD.
-2. **Trade manager `tm` (2026-11-17, operator).** Tickets are identified with the AI and executed deterministically through the CMD API: conditions → ASET (1.5×ATR stop, R-sized shares) → marketable entry → STOPMKT stop → targets / breakeven / flat-by. Paper only. Built and unit-tested (62 tests); the order path is UNVERIFIED until the operator's SIM test (`docs/spec/trade-manager.md`). This supersedes the "driver mode for limit entries with a bracket" in item 0 and the breakeven item in item 1(b).
-1. **FL gate correction (2026-09-27).** The 15-minute regular-hours FL results before this date let a
   cross on the prior day's last bar be entered at the 09:30 open; corrected improved rule is +201R
   (was +292R), +65R with 5¢ slip. The overnight cross itself (+242R on 387 trades) is an untested
   idea that needs its own study. SMB-format PlayBooks for FL and the 34-SMA play live in
   `docs/playbook/` (decks built by `make_charts.py` + `make_decks.py`).
0. **34-SMA pullback (regular-hours chart) as a second 1R experiment**: premarket volume 2–3× the
   20-day median, limit at the regular-hours 34-SMA between 10:00 and 14:00, 0.75×ATR stop, 1.8R
   target. Needs an `--entry-window` flag in the backtester, a driver mode for limit entries with
   a bracket, and a walk-forward that picks the premarket band on 2024 alone.
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
4. **Hotkey file generation.** BUILT 2026-11-19: `tools/gen_htk.py` reads and writes `*.htk`
   (round trip byte-identical on all eight live files; `tests/test_gen_htk.py`) and builds
   `scripts/local/<manifest>.htk` from a manifest in `scripts/htk/`. UNVERIFIED until the
   operator loads a generated file (plan.md L3) and a button runs a record with `ExecHotkey` (L4).
5. **Trailing stop management** from the driver: `%OrderAct` shows the resting stop, so
   re-price it as ATR moves, the way `fl_trading_agent.py` does.
6. **Chart-with-studies from script.** `LoadSetting <file>.cst` may carry named studies; if
   it does, one saved `.cst` gives every hidden chart `ema9 / sma34 / atr / vwap` without the
   Study Config dialog, and a fully DAS-native timer version of the FL scan becomes possible.
7. **Signal parity check** between the DAS chart script (`03`) and the driver on the same
   bars, so a divergence shows up as a diff instead of a missed trade.
8. **Reconcile the two FL definitions**: 9-EMA × 34-SMA (this repo) versus 9-EMA × VWAP
   (`fl_monitor_spec.md`). One definition, one backtest, one driver.

## DSL documentation (`INTENT.md`, 2026-10)

The language itself as the product: a reference in the spirit of the JLS, a cookbook, a
tutorial for traders, and an Emacs `dastrader-mode`. Each step is shippable alone.

| Step | State |
|---|---|
| Grammar draft with evidence labels, manual-vs-build table and open questions (`docs/spec/grammar.md`) | done 2026-10-15 |
| Open questions Q1–Q12 settled live on 5.8.4.4 Beta, plus 13 follow-up probes: `&&`/`\|\|` work at one shared precedence level, lower-case keywords only, block-final `;` required, no `$var` expansion in command args, DAS executes before it rejects | done 2026-10-15 |
| `&&`/`\|\|` allowed with full parentheses (CONSTITUTION §10, README, `check` lint flags unparenthesised mixes); `02` passes `.cst` names to `LoadSetting` through `Exec` | done 2026-10-15 |
| Standard-library recursive-descent checker in `tools/`, replacing the regex lint in `das_script_test.py check` — spec `docs/spec/features/001-checker/`, requirements `REQ-CHK-*` in `docs/spec/REQUIREMENTS.md` | next: spec drafted 2026-10-21 |
| Reference chapters: built-ins and commands, object model, execution contexts, limits | — |
| `dastrader-mode`: font-lock and indentation from the grammar, `.das`/`.htk` activation | — |
| Cookbook: one recipe per pattern already proven in `scripts/` | — |
| Tutorial for domain experts | — |
| `.htk` generation from `scripts/*.das` (item 4 above) on top of the checker | — |

## Later

- Paper-account order round trip in the harness (`NEWORDER` + `CANCEL` on a normal login)
  for scripts that must send an order to be tested.
- Session capture to CSV after each forward test, using the existing `das_session_capture.py`.
- A `--replay` mode for the driver that feeds recorded bars instead of live ones.

## Not planned

- Anything that touches an account other than TR4425 from automation.
- Publishing the DAS manuals or the CMD API specification in this repository.
