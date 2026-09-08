// ============================================================================
// 07-buy-fixed-slp.das  —  BUY with a fixed 11-cent Stop-Limit-P
// One hotkey. Run from the MONTAGE window.
// ============================================================================
//
// Fixed-distance sibling of 06-entry-with-slp-stop.das, which sizes the stop
// off ATR. Use this when you have already decided the stop level by structure
// (below a shelf, a VWAP reclaim, the low of the signal candle) and 11 cents is
// simply where it goes.
//
// ─────────────────────────────────────────────────────────────────────────────
// THE ONE DECISION THAT MATTERS HERE: $limitSlip
//
// A stop-LIMIT does not guarantee a fill. It guarantees a PRICE. Past the limit
// you are still holding.
//
//   trigger = entry - 0.11        the stop fires here
//   limit   = trigger - slip      you will accept fills down to here
//
// So your real worst case is 0.11 + slip, not 0.11.
//
//   slip 0.20  ->  worst case 0.31  = 2.8x the stop you asked for. Wrong.
//   slip 0.05  ->  worst case 0.16  = 1.45x. Reasonable on a liquid name.
//   slip 0.02  ->  worst case 0.13  but you will get left behind on a fast drop.
//
// 06 uses 0.20 because an ATR-sized stop is usually 50c-plus and 20c is noise
// against it. Against 11 cents it is not noise. Default here is 0.05.
//
// If never filling is the thing you actually fear, use SM (stop-market) instead
// of SLP: same argument slot, one price, always fills, price unknown.
// ─────────────────────────────────────────────────────────────────────────────
//
// PREREQUISITE: SLP is not enabled by default and needs your broker to turn it
// on for your account (das-advanced-hotkey-guide.pdf p.27). If it rejects, drop
// the P and use SL — identical arguments, regular hours only.
// ============================================================================

// ---- inputs ----------------------------------------------------------------
$stopDist   = 0.11;     // fixed stop distance, dollars
$limitSlip  = 0.05;     // how far through the trigger the limit sits. See above.
$entrySlip  = 0.15;     // marketable-limit offset on the entry
$riskDollars = 0;       // 0 = use the montage Share field.
                        // Set to your 1R and the size computes itself:
                        //   28 / 0.11 = 254 -> 200 shares after even-lot rounding
                        //   75 / 0.11 = 681 -> 600 shares

// ---- read state from the MONTAGE OBJECT ------------------------------------
// NOT bare `ASK` / `SHARE` / `SYMBOL`. Bare property names bind to whatever
// window happens to be FOCUSED when the hotkey fires, so they silently return
// nothing when focus is on a chart -- and `SYMBOL` is not a montage property at
// all (it belongs to the General Window Object; the montage list is BID ASK
// L2BID L2ASK ISBBID ISBASK LAST HI LO OPEN PCL POS Price Share SSARE TOGSSARE
// ROUTE DEFSHARE SHARECAP STOPTYPE STOPPRICE).
//
// The manual's own guidance, p.21: "In general, it may be better to use
// GetWindowObj() to manipulate the objects rather than FocusWindow."
//
// Requires the montage to be NAMED flMontage (right-click its title bar) and
// the desktop saved. See 01-fl-layout-build.das.
$m = GetWindowObj("flMontage");
if (isObject($m) == 0) { MsgBox("ABORT: no window named flMontage"); return; }

$sym = $m.GetTicker();
$px  = $m.ASK;             // buying, so reference the offer
$qty = $m.Share;

if ($sym == "") { MsgBox("ABORT: no symbol on montage"); return; }
if ($px  == 0)  { MsgBox("ABORT: no ASK on montage"); return; }

// ---- sizing ----------------------------------------------------------------
if ($riskDollars > 0) {
  // precision 100 = round DOWN to even lots (das-hotkeys-guide.pdf p.26)
  $qty = Round($riskDollars / $stopDist, 100);
  if ($qty < 1) { MsgBox("ABORT: risk " + $riskDollars + " buys 0 shares"); return; }
}

if ($qty < 1) { MsgBox("ABORT: montage Share is " + $qty); return; }

// ---- prices ----------------------------------------------------------------
$entry   = Round($px + $entrySlip, 2);
$trigger = Round($px - $stopDist, 2);        // 11 cents below
$limit   = Round($trigger - $limitSlip, 2);  // limit sits BELOW the trigger

// ---- confirm ---------------------------------------------------------------
// Delete once you trust it. $maxLoss is the number that actually matters:
// it is what you lose if the stop fills at the limit rather than the trigger.
$maxLoss = Round($qty * ($stopDist + $limitSlip), 2);

MsgBox("LONG " + $qty + " " + $sym + "\n" +
       "entry   " + $entry + "\n" +
       "stop    " + $trigger + "  (-" + $stopDist + ")" + "\n" +
       "limit   " + $limit + "\n" +
       "risk    " + Round($qty * $stopDist, 2) + " at trigger" + "\n" +
       "worst   " + $maxLoss + " at limit");

// ---- send ------------------------------------------------------------------
NewOrderObj("B " + $qty + " " + $sym + " L " + $entry + " D+").Send();
Wait(1100);                                  // one Send() per second, always
NewOrderObj("S " + $qty + " " + $sym + " SLP " + $trigger + " " + $limit + " D+").Send();

MsgLog("BUY ", $sym, " qty=", $qty, " entry=", $entry, " stop=", $trigger, "/", $limit);


// ============================================================================
// VARIANTS — swap the second Send() line
//
// Stop-market instead. Always fills, price not guaranteed. One price argument:
//   NewOrderObj("S " + $qty + " " + $sym + " SM " + $trigger + " D+").Send();
//
// Regular hours only, if SLP is not enabled on your account:
//   NewOrderObj("S " + $qty + " " + $sym + " SL " + $trigger + " " + $limit + " DAY").Send();
//
// Stop measured from the FILL rather than the offer. More correct, but the fill
// is not known at send time — you would place the entry, poll GetOrderObj() for
// the fill price, then send the stop. That is a second script, and it costs you
// the second between the two Send() calls with no protection on.
//
// Force a route that supports stops (STOP route is the default otherwise):
//   NewOrderObj("S " + $qty + " " + $sym + " CPSORS SLP " + $trigger + " " + $limit + " D+")
//
// SHORT version of this same script: see BLOCK B in 06-entry-with-slp-stop.das.
// Flip ASK->BID, B->SS, and both price offsets; argument order never changes.
// ============================================================================
