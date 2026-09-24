// ============================================================================
// 21-fl-short.das  —  Fashionably Late SHORT entry with a 1.5 x ATR stop-limit
// ============================================================================
// Mirror of 20-fl-long.das. Same globals ($FL_SYM, $FL_QTY, $FL_ATR), same
// driver, same no-MsgBox rule. Stop sits ABOVE the entry.
// ============================================================================

$stopMult  = 1.5;
$limitSlip = 0.20;
$entrySlip = 0.15;

if (isObject($FL_ATR) == 1) { MsgLog("FL SHORT refused: FL_ATR is an object"); return; }
if ($FL_ATR <= 0)            { MsgLog("FL SHORT refused: no ATR (I-1)"); return; }
if ($FL_QTY < 1)             { MsgLog("FL SHORT refused: qty ", $FL_QTY); return; }
if ($FL_SYM == "")           { MsgLog("FL SHORT refused: no symbol"); return; }

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgLog("FL SHORT refused: no montage1"); return; }

$m.SYMBOL = $FL_SYM;
Wait(700);
$px = $m.BID;
if ($px == 0) { MsgLog("FL SHORT refused: no BID for ", $FL_SYM); return; }

$stopDist = Round($stopMult * $FL_ATR, 2);
if ($stopDist < 0.02) { MsgLog("FL SHORT refused: stop too tight ", $stopDist); return; }

$negStop = 0 - $stopDist;
$negSlip = 0 - $limitSlip;
$entry   = Round($px - $entrySlip, 2);        // BID - slip
$trigger = Round($px - $negStop, 2);          // BID + stopDist
$limit   = Round($trigger - $negSlip, 2);     // trigger + limitSlip

$oe = "SS " + $FL_QTY;
$oe = $oe + " " + $FL_SYM;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
MsgLog("FL ENTRY [", $oe, "] atr=", $FL_ATR, " stopDist=", $stopDist);
NewOrderObj($oe).Send();

Wait(1100);
$pos = $m.POS;
$sz  = Abs($pos);
if ($sz < 1) {
  MsgLog("FL NOSTOP ", $FL_SYM, " unfilled POS=", $pos);
  return;
}

$os = "B " + $sz;
$os = $os + " " + $FL_SYM;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";
MsgLog("FL STOP [", $os, "]");
NewOrderObj($os).Send();
MsgLog("FL DONE SHORT ", $FL_SYM, " ", $sz, " entry~", $entry, " stop ", $trigger);
