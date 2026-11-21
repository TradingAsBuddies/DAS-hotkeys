// ==========================================================
// 06-entry-with-slp-stop.das   ATR-sized SLP stop
// Block A = LONG.  Block B = SHORT.  Bind each separately.
// Montage must be named  montage1
// Chart with an "atr" study must be named  flChart1m
// ==========================================================
//
// Same verified pattern as 07/08, with the stop distance
// taken from ATR instead of a fixed 11 cents. Use 07/08 when
// you have chosen the stop by structure; use this when you
// want it to scale with the name's volatility.
//
// Both defects that bit the earlier version are fixed here:
//
//  1. NAKED POSITION. A bare `S` with no long under it is not
//     a stop, it is a short (hotkeys guide p.11: "There is no
//     SHORT command, use SELL"). Both blocks now gate the
//     protective leg on montage POS.
//
//  2. LONG LINES. A 71-char order line reached DAS with 28
//     characters missing from its middle on 2026-09-08 and
//     became the nonexistent function $sSend(). Order strings
//     are built in short steps and printed before sending.
//
//  3. QUOTE ANCHOR. The stop was computed from ASK/BID at the
//     keypress, so a fill at the entry limit widened the risk
//     by $entrySlip. It now anchors to the position average
//     cost (same mechanism as 07/08). NOT YET VERIFIED ON SIM.
// ==========================================================


// ==========================================================
// BLOCK A - LONG
// ==========================================================

$stopMult    = 1.5;
$limitSlip   = 0.20;
$entrySlip   = 0.15;
$riskDollars = 0;

$c = GetWindowObj("flChart1m");
$m = GetWindowObj("montage1");
if (isObject($c) == 0) { MsgBox("no flChart1m"); return; }
if (isObject($m) == 0) { MsgBox("no montage1"); return; }

$atr = $c.GetStudyVal("atr");
$sym = $m.GetTicker();
$px  = $m.ASK;
$qty = $m.Share;

if ($atr == 0)  { MsgBox("no ATR - check study"); return; }
if ($sym == "") { MsgBox("no symbol"); return; }
if ($px == 0)   { MsgBox("no ASK"); return; }

$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) { MsgBox("stop too tight"); return; }

if ($riskDollars > 0) {
  $qty = Round($riskDollars / $stopDist, 100);
}
if ($qty < 1) { MsgBox("qty is " + $qty); return; }

// subtraction only - `+` threw ScriptError:100 in Round()
$negSlip = 0 - $entrySlip;

$entry   = Round($px - $negSlip, 2);

$oe = "B " + $qty;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";

MsgBox("ENTRY [" + $oe + "]");

NewOrderObj($oe).Send();
Wait(1100);

$pos = $m.POS;
if ($pos < 1) {
  MsgBox("NO STOP. Unfilled, POS=" + $pos);
  MsgLog("BUY ", $sym, " unfilled, no stop");
  return;
}

// ---- anchor: stop from the FILL, not the ASK -------------
// Same mechanism as 07: Price=AvgCost (hotkeys guide p.5)
// writes the position average cost into the montage Price
// box. A long cannot fill above its limit, so <= 0 or above
// $entry is not a fill: fall back to the ASK anchor.
FocusWindow montage1;
Price=AvgCost;
$fill = $m.Price;

$anchor = $fill;
$fb = 0;
if ($fill <= 0)     { $fb = 1; }
if ($fill > $entry) { $fb = 1; }
if ($fb == 1) {
  $anchor = $px;
  MsgLog("BUY ", $sym, " FALLBACK ASK, fill=", $fill);
}

$trigger = Round($anchor - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

$os = "S " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";

MsgBox("STOP [" + $os + "] fill " + $fill);

NewOrderObj($os).Send();
MsgLog("BUY ", $sym, " ", $pos, " fill ", $fill);
MsgLog("BUY ", $sym, " stop ", $trigger);


// ==========================================================
// BLOCK B - SHORT
// ==========================================================

$stopMult    = 1.5;
$limitSlip   = 0.20;
$entrySlip   = 0.15;
$riskDollars = 0;

$c = GetWindowObj("flChart1m");
$m = GetWindowObj("montage1");
if (isObject($c) == 0) { MsgBox("no flChart1m"); return; }
if (isObject($m) == 0) { MsgBox("no montage1"); return; }

$atr = $c.GetStudyVal("atr");
$sym = $m.GetTicker();
$px  = $m.BID;
$qty = $m.Share;

if ($atr == 0)  { MsgBox("no ATR - check study"); return; }
if ($sym == "") { MsgBox("no symbol"); return; }
if ($px == 0)   { MsgBox("no BID"); return; }

$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) { MsgBox("stop too tight"); return; }

if ($riskDollars > 0) {
  $qty = Round($riskDollars / $stopDist, 100);
}
if ($qty < 1) { MsgBox("qty is " + $qty); return; }

$negStop = 0 - $stopDist;
$negSlip = 0 - $limitSlip;

$entry   = Round($px - $entrySlip, 2);

$oe = "SS " + $qty;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";

MsgBox("ENTRY [" + $oe + "]");

NewOrderObj($oe).Send();
Wait(1100);

$pos = $m.POS;
$sz  = Abs($pos);
if ($sz < 1) {
  MsgBox("NO STOP. Unfilled, POS=" + $pos);
  MsgLog("SHORT ", $sym, " unfilled, no stop");
  return;
}

// ---- anchor: stop from the FILL, not the BID -------------
// Same mechanism as 08. A short cannot fill below its limit,
// so <= 0 or below $entry is not a fill: fall back to BID.
FocusWindow montage1;
Price=AvgCost;
$fill = $m.Price;

$anchor = $fill;
$fb = 0;
if ($fill <= 0)     { $fb = 1; }
if ($fill < $entry) { $fb = 1; }
if ($fb == 1) {
  $anchor = $px;
  MsgLog("SHORT ", $sym, " FALLBACK BID, fill=", $fill);
}

$trigger = Round($anchor - $negStop, 2);
$limit   = Round($trigger - $negSlip, 2);

$os = "B " + $sz;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";

MsgBox("STOP [" + $os + "] fill " + $fill);

NewOrderObj($os).Send();
MsgLog("SHORT ", $sym, " ", $sz, " fill ", $fill);
MsgLog("SHORT ", $sym, " stop ", $trigger);
