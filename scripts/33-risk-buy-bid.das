// ==========================================================
// 33-risk-buy-bid.das   R$7 BID / R$15 BID / R$10 LOAD
// Originals: R$70 BID / R$150 BID / R$100 LOAD.
// Shares = risk dollars / (1.5 x ATR), ATR from the atr
// study on flChart1m, which must show the montage symbol.
// The stop sits 1.5 x ATR below the fill, so a stop-out
// loses the stated dollars plus slippage.
// BID buys are passive: after ~5 s anything unfilled is
// CANCELLED so it can never fill later without a stop.
//
// Montage buttons: right-click the montage button bar >
// Edit (hot buttons guide p.3-4), paste ONE block per
// button. Advanced scripting must be ON.
//
// Recreated from the button LABELS on the GENK montage
// (screenshot, 2026-10-16) at one tenth the size. The
// original button scripts were not visible; behaviour
// below is inferred from the labels, not copied.
//
// These run on whatever account the montage is set to. The
// screenshot montage was on a LIVE account, not the TR4425
// paper account. Test every block on TR4425 first.
//
// NOT YET VERIFIED ON SIM.
// ==========================================================

// ==========================================================
// R$7 BID
// ==========================================================

// ---- inputs ----------------------------------------------
$risk        = 7;
$stopMult    = 1.5;
$limitSlip   = 0.05;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }
// Flat only: a stop sized to POS would also cover shares
// already held, and their own stop would then double up.
$pos0 = $m.POS;
if ($pos0 != 0) { MsgBox("not flat, POS=" + $pos0); return; }

$c = GetWindowObj("flChart1m");
if (isObject($c) == 0) { MsgBox("no flChart1m"); return; }
$ct = $c.GetTicker();
if ($ct != $sym) { MsgBox("chart not on " + $sym); return; }
$atr = $c.GetStudyVal("atr");
if ($atr <= 0) { MsgBox("no ATR - check study"); return; }
$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) { MsgBox("stop too tight"); return; }

$raw = $risk / $stopDist;
if ($raw > 20000) { MsgBox("size over 20000"); return; }

// ---- whole shares: DAS has no floor() ------------------
// Round(x, 100) rounds down to round lots (adv guide p.7),
// too coarse at this size. Count up in 100s, 10s, 1s; each
// loop stays far under the 200-iteration cap.
$q = 0;
$n = $q + 100;
while ($n <= $raw) { $q = $n; $n = $q + 100; }
$n = $q + 10;
while ($n <= $raw) { $q = $n; $n = $q + 10; }
$n = $q + 1;
while ($n <= $raw) { $q = $n; $n = $q + 1; }
if ($q < 1) { MsgBox("R$7 BID: under 1 share"); return; }

$px = $m.BID;
if ($px == 0) { MsgBox("no BID"); return; }
$entry = $px;

// ---- entry ---------------------------------------------
// From here on there is no MsgBox: a modal while shares are
// unprotected is the one place a dialog can cost money.
$oe = "B " + $q;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
MsgLog("R$7 BID ENTRY [", $oe, "]");
NewOrderObj($oe).Send();

// ---- wait for a fill, up to ~5 s ------------------------
// Wait(1100) first keeps the next Send() over the one-per-
// second limit. Then poll every 500 ms.
Wait(1100);
$pos = $m.POS;
$i = 0;
while ($i < 8) {
  if ($pos < $q) {
    Wait(500);
    $pos = $m.POS;
  }
  $i = $i + 1;
}

// ---- cancel whatever did not fill -----------------------
// Unfilled shares left working would fill later with no
// stop. CXL CLOSEST LONG cancels the buy nearest the bid
// (hotkeys guide p.13); the flat-only guard above means no
// other protective buy exists on this symbol.
if ($pos < $q) {
  FocusWindow montage1;
  CXL CLOSEST LONG;
  Wait(500);
  $pos = $m.POS;
}
if ($pos < 1) {
  MsgLog("R$7 BID NOSTOP ", $sym, " unfilled, cancelled");
  return;
}

// ---- anchor: stop from the FILL, not the BID -----------
// Same mechanism as 07: Price=AvgCost (hotkeys guide p.5).
// A buy cannot fill above its limit, so <= 0 or above
// $entry is not a fill: fall back to the BID anchor.
FocusWindow montage1;
Price=AvgCost;
$fill = $m.Price;

$anchor = $fill;
$fb = 0;
if ($fill <= 0)     { $fb = 1; }
if ($fill > $entry) { $fb = 1; }
if ($fb == 1) {
  $anchor = $px;
  MsgLog("R$7 BID FALLBACK BID, fill=", $fill);
}

$trigger = Round($anchor - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

// ---- stop -----------------------------------------------
$os = "S " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";
MsgLog("R$7 BID STOP [", $os, "]");
NewOrderObj($os).Send();
MsgLog("R$7 BID DONE ", $sym, " ", $pos, " fill ", $fill);
MsgLog("R$7 BID stop ", $trigger);


// ==========================================================
// R$15 BID
// ==========================================================

// ---- inputs ----------------------------------------------
$risk        = 15;
$stopMult    = 1.5;
$limitSlip   = 0.05;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }
// Flat only: a stop sized to POS would also cover shares
// already held, and their own stop would then double up.
$pos0 = $m.POS;
if ($pos0 != 0) { MsgBox("not flat, POS=" + $pos0); return; }

$c = GetWindowObj("flChart1m");
if (isObject($c) == 0) { MsgBox("no flChart1m"); return; }
$ct = $c.GetTicker();
if ($ct != $sym) { MsgBox("chart not on " + $sym); return; }
$atr = $c.GetStudyVal("atr");
if ($atr <= 0) { MsgBox("no ATR - check study"); return; }
$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) { MsgBox("stop too tight"); return; }

$raw = $risk / $stopDist;
if ($raw > 20000) { MsgBox("size over 20000"); return; }

// ---- whole shares: DAS has no floor() ------------------
// Round(x, 100) rounds down to round lots (adv guide p.7),
// too coarse at this size. Count up in 100s, 10s, 1s; each
// loop stays far under the 200-iteration cap.
$q = 0;
$n = $q + 100;
while ($n <= $raw) { $q = $n; $n = $q + 100; }
$n = $q + 10;
while ($n <= $raw) { $q = $n; $n = $q + 10; }
$n = $q + 1;
while ($n <= $raw) { $q = $n; $n = $q + 1; }
if ($q < 1) { MsgBox("R$15 BID: under 1 share"); return; }

$px = $m.BID;
if ($px == 0) { MsgBox("no BID"); return; }
$entry = $px;

// ---- entry ---------------------------------------------
// From here on there is no MsgBox: a modal while shares are
// unprotected is the one place a dialog can cost money.
$oe = "B " + $q;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
MsgLog("R$15 BID ENTRY [", $oe, "]");
NewOrderObj($oe).Send();

// ---- wait for a fill, up to ~5 s ------------------------
// Wait(1100) first keeps the next Send() over the one-per-
// second limit. Then poll every 500 ms.
Wait(1100);
$pos = $m.POS;
$i = 0;
while ($i < 8) {
  if ($pos < $q) {
    Wait(500);
    $pos = $m.POS;
  }
  $i = $i + 1;
}

// ---- cancel whatever did not fill -----------------------
// Unfilled shares left working would fill later with no
// stop. CXL CLOSEST LONG cancels the buy nearest the bid
// (hotkeys guide p.13); the flat-only guard above means no
// other protective buy exists on this symbol.
if ($pos < $q) {
  FocusWindow montage1;
  CXL CLOSEST LONG;
  Wait(500);
  $pos = $m.POS;
}
if ($pos < 1) {
  MsgLog("R$15 BID NOSTOP ", $sym, " unfilled, cancelled");
  return;
}

// ---- anchor: stop from the FILL, not the BID -----------
// Same mechanism as 07: Price=AvgCost (hotkeys guide p.5).
// A buy cannot fill above its limit, so <= 0 or above
// $entry is not a fill: fall back to the BID anchor.
FocusWindow montage1;
Price=AvgCost;
$fill = $m.Price;

$anchor = $fill;
$fb = 0;
if ($fill <= 0)     { $fb = 1; }
if ($fill > $entry) { $fb = 1; }
if ($fb == 1) {
  $anchor = $px;
  MsgLog("R$15 BID FALLBACK BID, fill=", $fill);
}

$trigger = Round($anchor - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

// ---- stop -----------------------------------------------
$os = "S " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";
MsgLog("R$15 BID STOP [", $os, "]");
NewOrderObj($os).Send();
MsgLog("R$15 BID DONE ", $sym, " ", $pos, " fill ", $fill);
MsgLog("R$15 BID stop ", $trigger);


// ==========================================================
// R$10 LOAD
// ==========================================================

// Loads the share box only. Sends nothing.
$risk        = 10;
$stopMult    = 1.5;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }

$c = GetWindowObj("flChart1m");
if (isObject($c) == 0) { MsgBox("no flChart1m"); return; }
$ct = $c.GetTicker();
if ($ct != $sym) { MsgBox("chart not on " + $sym); return; }
$atr = $c.GetStudyVal("atr");
if ($atr <= 0) { MsgBox("no ATR - check study"); return; }
$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) { MsgBox("stop too tight"); return; }

$raw = $risk / $stopDist;
if ($raw > 20000) { MsgBox("size over 20000"); return; }

// ---- whole shares: DAS has no floor() ------------------
// Round(x, 100) rounds down to round lots (adv guide p.7),
// too coarse at this size. Count up in 100s, 10s, 1s; each
// loop stays far under the 200-iteration cap.
$q = 0;
$n = $q + 100;
while ($n <= $raw) { $q = $n; $n = $q + 100; }
$n = $q + 10;
while ($n <= $raw) { $q = $n; $n = $q + 10; }
$n = $q + 1;
while ($n <= $raw) { $q = $n; $n = $q + 1; }
if ($q < 1) { MsgBox("R$10 LOAD: under 1 share"); return; }

$m.Share = $q;
MsgLog("R$10 LOAD ", $sym, " ", $q, " sh, stop ", $stopDist);

