// ============================================================================
// 07-buy-fixed-slp.das  —  BUY 11c stop.  Cannot open a short.
// One hotkey. Window must be named  montage1
// ============================================================================
//
// ─────────────────────────────────────────────────────────────────────────────
// WHAT WENT WRONG ON 2026-09-08
//
//   Accept,Shrt,POET,5,7.9,REB25,TR4425,,SLP:7.9 8.01,Oid:7652
//
// A BUY script that opened a 5-share SHORT. Three defects compounded:
//
// 1. MINE, and the dangerous one. The protective leg was a bare `S`:
//        NewOrderObj("S " + $qty + " " + $sym + " SLP ...").Send();
//    From das-hotkeys-guide.pdf p.11: "There is no SHORT command, use SELL".
//    From das-advanced-hotkey-guide.pdf p.26: "our system converts Sell and
//    Short appropriately". So `S` with NO LONG POSITION UNDER IT is not a stop.
//    It is a short. If the entry does not fill, the stop leg opens a naked one.
//
// 2. Bare ASK in the price lines:
//        $entry = Round(ASK + 0.15, 2);
//    Bare property names bind to the FOCUSED window, not to $m. When focus is
//    not the montage they return nothing, and the entry limit becomes garbage
//    that rests unfilled — which is precisely what lets defect 1 fire.
//
// 3. The SLP string was missing its limit price:
//        "SLP " + $trigger + " " + " D+"     ->   "SLP 7.9  D+"
//    SLP takes TWO prices, <trigger> <limit>. One was supplied.
//
// All three are fixed below. The guard on line "if ($pos < 1)" is the one that
// makes a naked short unreachable — it is the important line in this file.
// ─────────────────────────────────────────────────────────────────────────────

// ---- inputs ----------------------------------------------------------------
$stopDist    = 0.11;    // stop distance in dollars
$limitSlip   = 0.05;    // stop's limit sits this far through the trigger.
                        // Real worst case = $stopDist + $limitSlip = 0.16.
$entrySlip   = 0.15;    // marketable-limit offset on the entry
$riskDollars = 0;       // 0 = use the montage Share box. 28 -> 200sh at 0.11.

// ---- read state — ALWAYS through $m, never bare ------------------------------
$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("ABORT: no window named montage1"); return; }

$sym = $m.GetTicker();
$px  = $m.ASK;
$qty = $m.Share;

if ($sym == "") { MsgBox("ABORT: no symbol on montage"); return; }
if ($px  == 0)  { MsgBox("ABORT: no ASK on montage"); return; }

if ($riskDollars > 0) { $qty = Round($riskDollars / $stopDist, 100); }
if ($qty < 1) { MsgBox("ABORT: qty is " + $qty); return; }

// ---- prices — $px, not ASK ---------------------------------------------------
$entry   = Round($px + $entrySlip, 2);
$trigger = Round($px - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

// ---- send entry --------------------------------------------------------------
NewOrderObj("B " + $qty + " " + $sym + " L " + $entry + " D+").Send();
Wait(1100);                                  // one Send() per second

// ---- ARM THE STOP ONLY AGAINST A REAL POSITION -------------------------------
// This is the guard. POS is the montage's position property. If the entry has
// not filled, POS is 0 and we send nothing — better to sit unprotected and know
// it than to open a short you did not ask for.
//
// Note the stop is sized to $pos, NOT $qty, so a PARTIAL fill gets a stop for
// the shares actually held rather than an over-sized one that shorts the
// difference.
$pos = $m.POS;

if ($pos < 1) {
  MsgBox("NO STOP SENT" + "\n" +
         "entry has not filled (POS=" + $pos + ")" + "\n\n" +
         "You are UNPROTECTED. Either cancel the entry," + "\n" +
         "or run the ARM STOP hotkey once it fills.");
  MsgLog("BUY ", $sym, " entry sent, unfilled after 1.1s - no stop armed");
  return;
}

NewOrderObj("S " + $pos + " " + $sym + " SLP " + $trigger + " " + $limit + " D+").Send();
MsgLog("BUY ", $sym, " qty=", $pos, " entry=", $entry, " stop=", $trigger, "/", $limit);


// ============================================================================
// COMPANION HOTKEY — ARM STOP
// Bind separately. Run it after a delayed fill, when the script above bailed
// with "NO STOP SENT". Safe to press twice; it refuses when flat.
//
//   $m = GetWindowObj("montage1");
//   $pos = $m.POS;
//   if ($pos < 1) { MsgBox("Flat - nothing to protect"); return; }
//   $sym = $m.GetTicker();
//   $trigger = Round($m.LAST - 0.11, 2);
//   $limit   = Round($trigger - 0.05, 2);
//   NewOrderObj("S " + $pos + " " + $sym + " SLP " + $trigger + " " + $limit + " D+").Send();
//
// ============================================================================
// THE BETTER FIX, once you can test it
//
// TriggerOrder attaches the stop to the entry so it is armed BY THE FILL, not
// by a timer. das-hotkeys-guide.pdf p.7: "Trigger order will be sent to market
// when primary order fully filled." No timing window, no POS check, no chance
// of a detached leg:
//
//   $m.Price = $entry;
//   $m.Share = $qty;
//   $t = "TriggerOrder=RT:STOP STOPTYPE:LIMIT PX:" + $limit +
//        " STOPPRICE:" + $trigger + " ACT:SELL QTY:" + $qty + " TIF:DAY+;";
//   Exec($t);
//   BUY;
//
// Unresolved: whether TriggerOrder accepts interpolated variables directly or
// needs the Exec() wrapper shown here, and whether STOPTYPE takes LIMITP (the
// doc lists LIMIT/MARKET/Trailing/Range for this field, and LimitP only for the
// standalone StopType= command). Test in SIM with 1 share and read the
// TradeLog before trusting it.
//
// ============================================================================
// TEST SEQUENCE — SIM, Share = 1
//   1. Fire it. TradeLog must show side `Buy`. If you ever see `Shrt`, stop.
//   2. Unfilled entry -> you get "NO STOP SENT" and NO second order. Correct.
//   3. Filled entry   -> one Buy, then one Sell SLP with TWO prices.
// ============================================================================
