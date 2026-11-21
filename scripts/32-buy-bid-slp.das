// ==========================================================
// 32-buy-bid-slp.das   Buy BID 10 / Buy BID 50
// Originals: Buy BID 100 / Buy BID 500.
// Buy at the BID (passive), then an 11c SLP stop
// anchored to the fill. A passive bid often does not
// fill: after ~5 s the unfilled part is CANCELLED so it
// can never fill later without a stop.
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
// Buy BID 10
// ==========================================================

// ---- inputs ----------------------------------------------
$q           = 10;
$stopDist    = 0.11;
$limitSlip   = 0.05;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }
// Flat only: a stop sized to POS would also cover shares
// already held, and their own stop would then double up.
$pos0 = $m.POS;
if ($pos0 != 0) { MsgBox("not flat, POS=" + $pos0); return; }

$px = $m.BID;
if ($px == 0) { MsgBox("no BID"); return; }
$entry   = $px;

// ---- entry ---------------------------------------------
// From here on there is no MsgBox: a modal while shares are
// unprotected is the one place a dialog can cost money.
$oe = "B " + $q;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
MsgLog("BUY BID 10 ENTRY [", $oe, "]");
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
  MsgLog("BUY BID 10 NOSTOP ", $sym, " unfilled, cancelled");
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
  MsgLog("BUY BID 10 FALLBACK BID, fill=", $fill);
}

$trigger = Round($anchor - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

// ---- stop -----------------------------------------------
$os = "S " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";
MsgLog("BUY BID 10 STOP [", $os, "]");
NewOrderObj($os).Send();
MsgLog("BUY BID 10 DONE ", $sym, " ", $pos, " fill ", $fill);
MsgLog("BUY BID 10 stop ", $trigger);


// ==========================================================
// Buy BID 50
// ==========================================================

// ---- inputs ----------------------------------------------
$q           = 50;
$stopDist    = 0.11;
$limitSlip   = 0.05;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }
// Flat only: a stop sized to POS would also cover shares
// already held, and their own stop would then double up.
$pos0 = $m.POS;
if ($pos0 != 0) { MsgBox("not flat, POS=" + $pos0); return; }

$px = $m.BID;
if ($px == 0) { MsgBox("no BID"); return; }
$entry   = $px;

// ---- entry ---------------------------------------------
// From here on there is no MsgBox: a modal while shares are
// unprotected is the one place a dialog can cost money.
$oe = "B " + $q;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
MsgLog("BUY BID 50 ENTRY [", $oe, "]");
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
  MsgLog("BUY BID 50 NOSTOP ", $sym, " unfilled, cancelled");
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
  MsgLog("BUY BID 50 FALLBACK BID, fill=", $fill);
}

$trigger = Round($anchor - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

// ---- stop -----------------------------------------------
$os = "S " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";
MsgLog("BUY BID 50 STOP [", $os, "]");
NewOrderObj($os).Send();
MsgLog("BUY BID 50 DONE ", $sym, " ", $pos, " fill ", $fill);
MsgLog("BUY BID 50 stop ", $trigger);

