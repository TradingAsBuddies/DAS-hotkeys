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

// ---- read state - ALWAYS through $m, never bare ------------------------------
$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("ABORT: no window named montage1"); return; }

$sym = $m.GetTicker();
$px  = $m.BID;
$qty = $m.Share;

if ($sym == "") { MsgBox("ABORT: no symbol on montage"); return; }
if ($px  == 0)  { MsgBox("ABORT: no BID on montage"); return; }

if ($riskDollars > 0) { $qty = Round($riskDollars / $stopDist, 100); }
if ($qty < 1) { MsgBox("ABORT: qty is " + $qty); return; }

// ---- prices - $px, not BID ---------------------------------------------------
$entry   = Round($px - $entrySlip, 2);       // marketable limit, downside
$trigger = Round($px + $stopDist, 2);        // stop fires 11c ABOVE
$limit   = Round($trigger + $limitSlip, 2);  // accept fills up to here

MsgBox("SHORT " + $qty + " " + $sym + "\n" +
       "entry   " + $entry + "\n" +
       "stop    " + $trigger + "  (+" + $stopDist + ")" + "\n" +
       "limit   " + $limit + "\n" +
       "worst   " + Round($qty * ($stopDist + $limitSlip), 2) + " if filled at limit");

// ---- send entry --------------------------------------------------------------
NewOrderObj("SS " + $qty + " " + $sym + " L " + $entry + " D+").Send();
Wait(1100);                                  // one Send() per second

// ---- ARM THE COVER ONLY AGAINST A REAL POSITION ------------------------------
// Mirror of the guard in 07, and the same class of bug it prevents: a bare `B`
// cover fired with nothing short under it does not fail safe -- it opens a LONG.
//
// SIGN CONVENTION IS UNVERIFIED. The 07 fill logged "Positio:5" for a 5-share
// LONG. What POS reports for a SHORT -- -5, or 5 -- has not been observed. So
// this guards on MAGNITUDE, which is correct under either convention: if you
// are flat, nothing is sent. Tighten it to `if ($pos > -1)` only after you have
// confirmed POS goes negative on a short.
$pos = $m.POS;
$sz  = Abs($pos);

if ($sz < 1) {
  MsgBox("NO STOP SENT" + "\n" +
         "short has not filled (POS=" + $pos + ")" + "\n\n" +
         "You are UNPROTECTED. Cancel the entry, or run" + "\n" +
         "the ARM COVER hotkey once it fills.");
  MsgLog("SHORT ", $sym, " entry sent, unfilled after 1.1s - no stop armed");
  return;
}

NewOrderObj("B " + $sz + " " + $sym + " SLP " + $trigger + " " + $limit + " D+").Send();
MsgLog("SHORT ", $sym, " qty=", $sz, " entry=", $entry, " stop=", $trigger, "/", $limit);


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
//   NewOrderObj("S " + $qty + " " + $sym + " L " + Round($m.BID - 0.15, 2) + " D+").Send();
//
// Cancel the resting stop first, or you will be left short by the size of the
// stop once it triggers against a position you no longer hold:
//   GetAccountObj($acct).CancelOrder("SELL", $sym, 0);
//
// ── Locate check before shorting ─────────────────────────────────────────────
//   LeftLocateQuery;    // how many shares are left to short on this symbol
//   FillLocate;         // populate Share from the first short-locate window
// ============================================================================
