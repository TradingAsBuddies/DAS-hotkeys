// ============================================================================
// 06-entry-with-slp-stop.das  —  entry + protective 1.5x ATR Stop-Limit-P
// Two hotkeys. Block A = LONG. Block B = SHORT. Bind each separately.
// Run from the MONTAGE window.
// ============================================================================
//
// ─────────────────────────────────────────────────────────────────────────────
// BEFORE YOU BIND THESE — four things that will bite
//
// 1. SLP IS NOT ENABLED BY DEFAULT.
//      "Stop Limit P is for pre-post market stop limit orders. This is not
//       enabled by default and needs your broker to enable for your account."
//      — das-advanced-hotkey-guide.pdf p.27
//    If your account lacks it, these orders reject. Use SL instead (regular-
//    hours stop limit) — same argument order, drop the P.
//
// 2. YOUR OWN CODE FOUND A STOP THAT WASN'T A STOP.
//    fl_monitor.py, place_stop():
//      "LIMITP via CMD API executes immediately as a limit order in SIM — it is
//       not a stop. Stop enforcement happens in process_inbound()"
//    That was the CMD API, not hotkeys, so it may not apply here. But verify on
//    a SIM account that the SLP order actually RESTS rather than filling on
//    submission. If it fills instantly you have just market-ordered yourself out.
//
// 3. ONE Send() PER SECOND. Entry and stop are two orders, hence Wait(1100).
//    Without the wait the stop is silently dropped and you sit unprotected.
//
// 4. TRIGGER COMES BEFORE LIMIT.  "SLP <trigger> <limit>"
//    (DAS's own manual prints "B" for both its Buy and Sell stop-limit examples.
//     That is a copy-paste error in their doc. The sides below are correct.)
//
// SETUP: chart named flChart1m with an ATR study named exactly "atr".
// ─────────────────────────────────────────────────────────────────────────────


// ============================================================================
// BLOCK A — LONG:  buy, then rest a SELL stop 1.5x ATR below the fill
// ============================================================================

// ---- inputs ----------------------------------------------------------------
$stopMult   = 1.5;      // ATR multiple for the stop distance
$limitSlip  = 0.20;     // how far THROUGH the trigger the limit sits, in dollars.
                        // Matches REGULAR_LIMIT_OFFSET in fl_shared.py. A stop
                        // limit priced AT the trigger routinely does not fill.
$entrySlip  = 0.15;     // marketable-limit offset for the entry. Matches
                        // place_entry() in fl_trading_agent.py.
$riskDollars = 0;       // 0 = use montage Share as-is.
                        // Set to e.g. 28 to size by risk instead (see below).

// ---- read state ------------------------------------------------------------
// ATR comes off the chart, not the montage — the montage has no ATR property.
$c = GetWindowObj("flChart1m");
$m = GetWindowObj("flMontage");
if (isObject($c) == 0) { MsgBox("ABORT: no window named flChart1m"); return; }
if (isObject($m) == 0) { MsgBox("ABORT: no window named flMontage"); return; }

$atr = $c.GetStudyVal("atr");
$sym = $m.GetTicker();
$px  = $m.ASK;            // buying, so reference the offer

// ---- guards ----------------------------------------------------------------
// This is the hotkey equivalent of live invariant I-1: never submit an entry
// without a real ATR. A near-zero ATR produces a stop that rounds onto the
// entry price — the exact defect that made R explode to 1e12 in the backtest.
if ($atr == 0) { MsgBox("ABORT: no ATR - check the study is named atr"); return; }
if ($px  == 0) { MsgBox("ABORT: no price on montage"); return; }
if ($sym == "") { MsgBox("ABORT: no symbol on montage"); return; }

$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) { MsgBox("ABORT: stop distance " + $stopDist + " too tight"); return; }

// ---- sizing ----------------------------------------------------------------
$qty = $m.Share;
if ($riskDollars > 0) {
  // Round precision 100 = round DOWN to even lots (das-hotkeys-guide p.26)
  $qty = Round($riskDollars / $stopDist, 100);
  if ($qty < 1) { MsgBox("ABORT: risk " + $riskDollars + " buys 0 shares at " + $stopDist); return; }
}

// ---- prices ----------------------------------------------------------------
$entry   = Round($px + $entrySlip, 2);          // marketable limit
$trigger = Round($px - $stopDist, 2);           // stop fires BELOW
$limit   = Round($trigger - $limitSlip, 2);     // limit sits BELOW the trigger

// ---- confirm ---------------------------------------------------------------
// Delete this block once you trust it. Until then, look before you fire.
MsgBox("LONG " + $qty + " " + $sym + "\n" +
       "entry  " + $entry + "\n" +
       "stop   " + $trigger + " / lmt " + $limit + "\n" +
       "risk   " + $stopDist + "  (" + $stopMult + " x ATR " + Round($atr,3) + ")" + "\n" +
       "$risk  " + Round($qty * $stopDist, 2));

// ---- send ------------------------------------------------------------------
NewOrderObj("B " + $qty + " " + $sym + " L " + $entry + " D+").Send();
Wait(1100);                                     // one Send() per second
NewOrderObj("S " + $qty + " " + $sym + " SLP " + $trigger + " " + $limit + " D+").Send();

MsgLog("LONG ", $sym, " qty=", $qty, " entry=", $entry, " stop=", $trigger, "/", $limit);


// ============================================================================
// BLOCK B — SHORT:  short, then rest a BUY stop 1.5x ATR above the fill
// Mirror image. Every sign flips; the argument ORDER never does.
// ============================================================================

$stopMult   = 1.5;
$limitSlip  = 0.20;
$entrySlip  = 0.15;
$riskDollars = 0;

$c = GetWindowObj("flChart1m");
$m = GetWindowObj("flMontage");
if (isObject($c) == 0) { MsgBox("ABORT: no window named flChart1m"); return; }
if (isObject($m) == 0) { MsgBox("ABORT: no window named flMontage"); return; }

$atr = $c.GetStudyVal("atr");
$sym = $m.GetTicker();
$px  = $m.BID;            // shorting, so reference the bid

if ($atr == 0) { MsgBox("ABORT: no ATR - check the study is named atr"); return; }
if ($px  == 0) { MsgBox("ABORT: no price on montage"); return; }
if ($sym == "") { MsgBox("ABORT: no symbol on montage"); return; }

$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) { MsgBox("ABORT: stop distance " + $stopDist + " too tight"); return; }

$qty = $m.Share;
if ($riskDollars > 0) {
  $qty = Round($riskDollars / $stopDist, 100);
  if ($qty < 1) { MsgBox("ABORT: risk " + $riskDollars + " buys 0 shares at " + $stopDist); return; }
}

$entry   = Round($px - $entrySlip, 2);          // marketable limit, downside
$trigger = Round($px + $stopDist, 2);           // stop fires ABOVE
$limit   = Round($trigger + $limitSlip, 2);     // limit sits ABOVE the trigger

MsgBox("SHORT " + $qty + " " + $sym + "\n" +
       "entry  " + $entry + "\n" +
       "stop   " + $trigger + " / lmt " + $limit + "\n" +
       "risk   " + $stopDist + "  (" + $stopMult + " x ATR " + Round($atr,3) + ")" + "\n" +
       "$risk  " + Round($qty * $stopDist, 2));

// SS = short. DAS converts Sell vs Short appropriately, so the COVER leg is a
// plain B — you do not compute whether it is a buy-to-cover.
NewOrderObj("SS " + $qty + " " + $sym + " L " + $entry + " D+").Send();
Wait(1100);
NewOrderObj("B " + $qty + " " + $sym + " SLP " + $trigger + " " + $limit + " D+").Send();

MsgLog("SHORT ", $sym, " qty=", $qty, " entry=", $entry, " stop=", $trigger, "/", $limit);


// ============================================================================
// REFERENCE
//
// Short form field order:   Side Share Symbol Route OrderType OtherPrice Price TIF
//   Side        B | BUY        S | SELL        SS | SHRT | SHORT
//   OrderType   L limit   M market   SL stop-limit   SLP stop-limit pre/post
//               SM stop-market   TL trailing   RG range   RGM range-market
//   TIF         D day    D+ extended    GTC    GTC+    IOC    FOC
//
// Stop-limit args are ALWAYS  <trigger> <limit>  in that order, both sides.
//
// Route: STOP route is used by default for stop orders. To force a direct route
// that supports stops, insert it before the order type:
//   NewOrderObj("S 100 " + $sym + " CPSORS SLP " + $trigger + " " + $limit + " D+")
//
// Omitted fields fall back to Setup > Order Templates > Default. The manual
// recommends filling everything explicitly — these scripts do, except route.
//
// TESTING ORDER
//   1. SIM account. Set $riskDollars = 0 and SHARE = 1 on the montage.
//   2. Fire BLOCK A. Confirm in the Orders window that the SLP order RESTS.
//   3. Only then raise size, and only then consider a live account.
// ============================================================================
