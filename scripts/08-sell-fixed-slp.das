// ============================================================================
// 08-sell-fixed-slp.das  —  SHORT with a fixed 11-cent Stop-Limit-P
// One hotkey. Run from the MONTAGE window.
// Mirror of 07-buy-fixed-slp.das. Every sign flips; argument ORDER never does.
// ============================================================================
//
// SELL here means SELL SHORT — opening a new short, matching how 06 Block B is
// written. If you meant "flatten a long I already hold", that is a different
// order and it is at the bottom of this file under VARIANTS.
//
// ─────────────────────────────────────────────────────────────────────────────
// THE SHORT SIDE HAS ONE EXTRA WAY TO FAIL
//
// Everything from 07 applies — worst case is 0.11 + $limitSlip, not 0.11 — and
// on the short side there are two more:
//
//   1. LOCATE. No borrow, no fill, and the SLP stop still goes out. You end up
//      with a resting buy stop and no position for it to cover. Check the
//      locate before firing, or use LeftLocateQuery / FillLocate.
//
//   2. UNBOUNDED UPSIDE. A stop-LIMIT on a short caps the price you will pay to
//      cover. If it gaps through your limit you are still short into the move.
//      That is the same mechanic as a long, but the tail is worse on this side:
//      a long can only go to zero, a short cannot. On a halt-and-resume or a
//      squeeze, SM (stop-market) is the safer instrument even though it fills at
//      an unknown price.
//
// Default $limitSlip stays 0.05, same reasoning as 07: a 0.20 slip against an
// 11-cent stop makes the real risk 0.31 and quietly triples what you signed up
// for. Consider going wider on the short side than you would on a long.
// ─────────────────────────────────────────────────────────────────────────────
//
// PREREQUISITE: SLP is not enabled by default — the broker must turn it on
// (das-advanced-hotkey-guide.pdf p.27). If it rejects, use SL, same arguments.
// ============================================================================

// ---- inputs ----------------------------------------------------------------
$stopDist   = 0.11;     // fixed stop distance, dollars
$limitSlip  = 0.05;     // how far through the trigger the limit sits
$entrySlip  = 0.15;     // marketable-limit offset on the entry
$riskDollars = 0;       // 0 = use the montage Share field.
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
$px  = $m.BID;             // shorting, so reference the bid
$qty = $m.Share;

if ($sym == "") { MsgBox("ABORT: no symbol on montage"); return; }
if ($px  == 0)  { MsgBox("ABORT: no BID on montage"); return; }

// ---- sizing ----------------------------------------------------------------
if ($riskDollars > 0) {
  // precision 100 = round DOWN to even lots (das-hotkeys-guide.pdf p.26)
  $qty = Round($riskDollars / $stopDist, 100);
  if ($qty < 1) { MsgBox("ABORT: risk " + $riskDollars + " buys 0 shares"); return; }
}

if ($qty < 1) { MsgBox("ABORT: montage Share is " + $qty); return; }

// ---- prices ----------------------------------------------------------------
$entry   = Round($px - $entrySlip, 2);       // marketable limit, downside
$trigger = Round($px + $stopDist, 2);        // 11 cents ABOVE
$limit   = Round($trigger + $limitSlip, 2);  // limit sits ABOVE the trigger

// ---- confirm ---------------------------------------------------------------
$maxLoss = Round($qty * ($stopDist + $limitSlip), 2);

MsgBox("SHORT " + $qty + " " + $sym + "\n" +
       "entry   " + $entry + "\n" +
       "stop    " + $trigger + "  (+" + $stopDist + ")" + "\n" +
       "limit   " + $limit + "\n" +
       "risk    " + Round($qty * $stopDist, 2) + " at trigger" + "\n" +
       "worst   " + $maxLoss + " at limit");

// ---- send ------------------------------------------------------------------
// SS = short. DAS converts Sell vs Short appropriately, so the COVER leg is a
// plain B — you do not work out whether it is a buy-to-cover.
NewOrderObj("SS " + $qty + " " + $sym + " L " + $entry + " D+").Send();
Wait(1100);                                  // one Send() per second, always
NewOrderObj("B " + $qty + " " + $sym + " SLP " + $trigger + " " + $limit + " D+").Send();

MsgLog("SHORT ", $sym, " qty=", $qty, " entry=", $entry, " stop=", $trigger, "/", $limit);


// ============================================================================
// VARIANTS — swap the second Send() line
//
// Stop-market. Always covers, price not guaranteed. Preferred into a squeeze:
//   NewOrderObj("B " + $qty + " " + $sym + " SM " + $trigger + " D+").Send();
//
// Regular hours only, if SLP is not enabled:
//   NewOrderObj("B " + $qty + " " + $sym + " SL " + $trigger + " " + $limit + " DAY").Send();
//
// ── If you meant SELL TO CLOSE a long you already hold ──────────────────────
// Not this script. That is a single order, no protective leg, and the size
// should come from the position rather than the Share box:
//
//   $qty = POS;                                   // montage position property
//   NewOrderObj("S " + $qty + " " + $sym + " L " + Round(BID - 0.15, 2) + " D+").Send();
//
// Cancel the resting stop first, or you will be left short by the size of the
// stop once it triggers against a position you no longer hold:
//   GetAccountObj($acct).CancelOrder("SELL", $sym, 0);
//
// ── Locate check before shorting ─────────────────────────────────────────────
//   LeftLocateQuery;    // how many shares are left to short on this symbol
//   FillLocate;         // populate Share from the first short-locate window
// ============================================================================
