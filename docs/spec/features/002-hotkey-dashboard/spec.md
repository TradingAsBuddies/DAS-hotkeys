# 002 — Hotkey dashboard: feature spec

**Status: draft, 2026-11-19.** Not built. Grew out of the `four-box-readout` tile (`dash_box`,
live since 2026-11-18) and a review of a DAS scripts-and-hotkeys walkthrough video (PIRATA TRADER,
2026-01-10). Evidence labels follow `docs/spec/REQUIREMENTS.md`: **[V]** verified live on this
build and cited, **[D]** documented in a manual, **[I]** inferred and unverified.

## Problem

The risk rules exist on paper and nowhere on the screen. PREFERENCES holds R per account,
`MIN_STOP_ATR`, the per-symbol 1R lockout, `MAX_LIVE_TICKERS`, the no-entry window at the end
of the session, and the `LOSING_STREAK_POLICY` ladder (any of T1–T3 moves it up a level: stand-down, half size, session
over). At the moment a trader presses a key, none of that is visible, and none of it is checked
by the key.

The 2026-08-28 session shows the cost. The ladder would have fired, and a new position opened
eight minutes after the loss that should have fired it. QNRX was sized with an ATR read 35
minutes late and ran to well past 1R. Each rule was written down. None was in front of the
trader, and no key refused.

A dashboard has two jobs, and the second is the one that matters:

1. **Show** the state the rules depend on, where the eyes already are: the montage.
2. **Gate** the entry buttons on that same state, so a stand-down or a lockout refuses the
   order instead of only being displayed next to it.

## What it is not

- Not a charting page or a browser dashboard. State that does not change a keypress belongs in
  the morning plan, not on the montage.
- Not a place to type R. R comes from R-CONFIG through `tools/baf_rconfig.py` (CONSTITUTION,
  PREFERENCES). The video's `Ctrl+R` risk prompt is the pattern this project rejects.
- Not a price-based risk cap. The video caps risk per share at 10% of the share price; ours is
  `shares = R ÷ (1.5 × ATR + slippage)`, because stop distance comes from volatility, not price
  (PREFERENCES, *Position size is bounded by ATR, not by notional*).

## Layout (montage1)

Two rows of montage buttons. The top row displays and runs nothing. The bottom row acts.

```
┌───────────────┬───────────────┬───────────────┬───────────────┬───────────────┐
│ dash_box      │ dash_r        │ dash_ladder   │ dash_lock     │ dash_clock    │
│ SPY HSLW 09:45│ SIM -0.8R pk+.4│ L0 CLEAR      │ LOCK none     │ NEW OK 4h10m  │
│ green         │ green/yel/red │ gray/yel/red  │ gray / red    │ gray/yel/red  │
├───────────────┼───────────────┼───────────────┼───────────────┼───────────────┤
│ BAF LONG      │ BAF SHORT     │ BE STOP       │ FLAT SYM      │ CXL SYM       │
│ 30 block A    │ 30 block B    │ proposed      │ 22 pattern    │ CancelOrder   │
└───────────────┴───────────────┴───────────────┴───────────────┴───────────────┘
```

## Display tiles

Each tile is written by a feeder over the CMD API, with the guarded `GetCustButObj` write already
verified for `dash_box` (WISDOM, *Hot Buttons Are a Display the CMD API Can Write*). Any tile
the feeder cannot compute shows `UNAVAILABLE` in gray. It never carries yesterday's value and
never guesses.

| Tile | Shows | Source | On failure | State |
|---|---|---|---|---|
| `dash_box` | SPY four-box, QQQ when it disagrees, time of read | Market Vision `vision-log.jsonl` | `BOX: UNAVAILABLE`, `BOX STALE hh:mm` | **[V]** running as `four-box-feeder.service` |
| `dash_r` | Session realized R for the paper account, and the intraday peak | `%POS` Realized per symbol ÷ R from R-CONFIG | `R: UNAVAILABLE` | **[I]** `%POS` carries Realized (`das_flat_check.py` reads it); not yet summed live |
| `dash_ladder` | Ladder level 0–3, the trigger that fired, the stand-down end time | T1 per-symbol −1R and T2 2R peak drawdown from `%POS`; T3 three losing round trips from `%TRADE` | `LADDER: UNAVAILABLE` (and gate closes, below) | **[I]** |
| `dash_lock` | Symbols at −1R today, up to three | `%POS` per-symbol Realized | `LOCK: UNAVAILABLE` | **[I]** |
| `dash_clock` | Minutes of entry window left; `NO NEW` in the last 15 min; `FLAT BY` near the close | Session window in PREFERENCES; clock source below | `CLOCK: UNAVAILABLE` | **[I]** |

Colours follow `four_box_feeder.py`, all names already accepted by `Color()` on this build
**[V]**: Green clear, Yellow caution, Red stop, Gray unavailable. Ladder: L0 Gray, L1 Yellow,
L2 Red, L3 Black.

Clock source is a conflict to settle. CONSTITUTION §7 takes timestamps from the exchange, and
the feeder runs on the host clock. The tile only gates entries by minutes, so the proposal is
the host clock with NTP, labelled as such in the feeder header, and a `BOX`-style STALE check
on the DAS log's own time stamps.

## The gate

The same GLOBALSCRIPT write that paints the tiles also sets operator-setting globals
(CONSTITUTION §12 allows globals for exactly this):

| Global | Meaning |
|---|---|
| `$DASH_OK` | 1 only when every input is available and at most three symbols are locked. The Desktop Load Script sets it to 0, so a fresh DAS starts closed |
| `$DASH_STAMP` | Feeder heartbeat: `GetSecond()` seconds since midnight **[D]** (advanced guide; hotkeys guide), written from inside DAS so both sides use DAS's clock |
| `$DASH_HOLD` | 1 during a stand-down (levels 1 and 2) or after level 3: refuse |
| `$DASH_LEVEL` | Ladder level 0–3, for display and for the size multiplier |
| `$DASH_SIZE` | 1, or 0.5 from level 2 for the rest of the session |
| `$DASH_LOCK1..3` | Locked symbols, `"none"` when empty, because a global assigned `""` stays unregistered (grammar.md 2.5) |
| `$DASH_NEWOK` | 0 inside the no-entry window |

The feeder writes the stamp in the same script that writes the rest, so the stamp and the values
cannot disagree. It sends the stamp as `$DASH_STAMP = GetSecond();`. One-line scripts carry no
`//` comments, because only the harness strips them.

Each **entry** script gets two guards. The first goes at the top, before any order object exists:

```
if ($DASH_OK != 1) { MsgLog("DASH REFUSE feeder"); return; }
if ((GetSecond() - $DASH_STAMP) > 150) { MsgLog("DASH REFUSE stale"); return; }
if ($DASH_HOLD == 1) { MsgLog("DASH REFUSE ladder"); return; }
if ($DASH_NEWOK != 1) { MsgLog("DASH REFUSE window"); return; }
```

The second goes immediately after the script reads its own ticker. It must not go earlier,
because `$sym` is a global and at the top it still holds the previous press's ticker:

```
if ($sym == $DASH_LOCK1) { MsgLog("DASH REFUSE lock"); return; }
if ($sym == $DASH_LOCK2) { MsgLog("DASH REFUSE lock"); return; }
if ($sym == $DASH_LOCK3) { MsgLog("DASH REFUSE lock"); return; }
```

Size: `$r = $r * $DASH_SIZE;` goes before the whole-share loop in script 30, so half size still
comes out in whole shares. `GetSecond()` wraps at midnight. That is harmless inside a morning
trading window, and it is written down here so nobody is surprised.

**Ladder, as PREFERENCES states it.** Any trigger (T1 a symbol at −1R, T2 a 2R drawdown
from the intraday peak, T3 three losing round trips) fires the *next* level:

- The first trigger is level 1: a 15-minute stand-down.
- A second trigger, or a drawdown of 3R or more, is level 2: a 30-minute stand-down, then half
  size for the rest of the session.
- A drawdown at `DAILY_MAX_R` is level 3: the session is over. This is also 3R, so at 3R level 3
  wins.

PREFERENCES adds a re-entry gate after a stand-down: the name and trigger must be on the published
plan, and size must come from `MIN_STOP_ATR`. The script can check size. It cannot check the
plan, so the tile shows `L1 OVER: PLAN NAMES ONLY` as a reminder, and the spec does not claim to
enforce it.

**Exit buttons never read the gate.** Flatten, cancel and breakeven work at every level,
because a gate that can block an exit is a new way to hold a position without a stop
(CONSTITUTION §1.3, §1.5).

**What the gate does not cover.** It guards only the scripts that carry it. The montage's own
BUY and SELL buttons, every other hotkey, and keyboard order entry stay ungated. The generator
(plan.md) emits only gated entry hotkeys, and the operator removes or unbinds ungated entry keys
from the dashboard desktop. Until that is done, the dashboard advises; it does not enforce.

**Fail closed or fail open** is the operator's call (open question 1). The proposal is fail
closed: no feeder or a stale heartbeat means no new entries, and the tile says why. It costs a
missed trade when the service dies. Fail open costs a re-entry like 08-28.

## Action buttons

| Button | Script | State |
|---|---|---|
| BAF LONG / BAF SHORT | `scripts/30-bracket-at-fill.das` blocks A and B, plus the gate | BUILT; SIM test pending (U1–U6) |
| BE STOP | Moves the stop to the average cost on the filled position. The video's breakeven key; `tm` has the engine logic | not built; propose as a forum topic |
| FLAT LONG / FLAT SHORT | Per-symbol limit close, the `22-fl-flatten.das` pattern. It needs two buttons because a button only has the unsigned `.POS`, and guessing the side is how the 09-25 double short happened. If the close does not fill, it places the stop again | **[I]**: script 22 ran only when a driver supplied a signed side |
| FLAT ALL | Level 3 needs every position flat and every order cancelled; one button per montage symbol is not enough | **[I]**, not built |
| CXL SYM | Cancels working entries on the symbol and **refuses while `POS != 0`**, because `CancelOrder("BUY\|SELL", sym)` also cancels the protective stop (CONSTITUTION §1.3) | **[V]** that the call cancels (script 22); refusal not built |

Cloned montages: script 30 sets `$bafMontage = "montage1"` itself, so a copy made with
`DuplicateWindow` would trade montage1's symbol and account. In the generated version, each thin
button sets `$bafMontage` to its own window name before `ExecHotkey`, and the generated script
does not assign it.

## Ideas from the video, sorted

| Idea | Verdict |
|---|---|
| Globals set in the Desktop Load Script | Already ours (`00`, `baf-rconfig.das`) |
| `Ctrl+R` prompt to type today's risk | Rejected: R is never typed |
| Size so risk per share is at most 10% of price | Rejected: price-based; ours is ATR-based |
| Sound when a short locate fills | Adopt as a DAS setting, no script; note in the playbook |
| Route by time of day (ARCA before 13:00, else EDGX) | Open: no route policy exists here yet |
| Breakeven stop key | Adopt as `BE STOP`, forum topic first |
| Old basic hotkeys break when advanced scripting is on | Matches WISDOM; worth a line in the tutorial |

## Automation

See `plan.md`.

## Open questions

1. Fail closed or fail open when the feeder is down (proposal: closed, entries only).
2. May the feeder **read** live-account `%POS` to fill a LIVE R tile and `MAX_LIVE_TICKERS`?
   CONSTITUTION §1.1 limits automation to the paper account; reading is not trading, but the
   rule does not say so. Until it does, every tile covers the paper account only.
3. Does `GLOBALSCRIPT` set globals that a montage button then reads? Variables are global
   across windows per the hot buttons guide **[D]**; one probe settles it on this build.
4. Restart state. Nobody knows yet whether `%TRADE` still carries fills from before a DAS
   restart. T3 needs round trips rebuilt across partial fills, and level 2 lasts for the rest of
   the session. Proposal: the feeder appends each trigger event to a dated local file outside
   the repo and reads it back on start, and `plan.md` L8 tests `%TRADE` after a restart.
5. The no-entry window (last 15 minutes) comes from the 09-25 lesson in `docs/ROADMAP.md`
   (*Next*, item 2), not from PREFERENCES. PREFERENCES gives only the trading window. Should it
   move into PREFERENCES, so there is one source?
