// ============================================================================
// 20-fl-long.das  —  Fashionably Late LONG entry with a 1.5 x ATR stop-limit
// ============================================================================
// Driven, not pressed. tools/fl_forward_test.py sets these globals over the
// CMD API (SCRIPT GLOBALSCRIPT) and then injects this file into montage1:
//
//   $FL_SYM   symbol to trade            (string)
//   $FL_QTY   shares                     (integer, already risk-sized)
//   $FL_ATR   ATR(14) from 1-minute bars (float, > 0)  — spec invariant I-1:
//             no entry without a computed ATR, no fallback constant.
//
// Can also be bound to a hotkey after setting the three globals by hand.
// No MsgBox anywhere: a modal freezes the CMD API (docs/CMD-API-TESTING.md).
// Pattern and Round() workarounds copied from 06/07, which executed on SIM.
// ============================================================================

$stopMult  = 1.5;    // stop distance in ATRs
$limitSlip = 0.20;   // stop-limit price below the trigger
$entrySlip = 0.15;   // pay up to ASK + this to get filled

if (isObject($FL_ATR) == 1) { MsgLog("FL LONG refused: FL_ATR is an object"); return; }
if ($FL_ATR <= 0)            { MsgLog("FL LONG refused: no ATR (I-1)"); return; }
if ($FL_QTY < 1)             { MsgLog("FL LONG refused: qty ", $FL_QTY); return; }
if ($FL_SYM == "")           { MsgLog("FL LONG refused: no symbol"); return; }

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgLog("FL LONG refused: no montage1"); return; }

$m.SYMBOL = $FL_SYM;
Wait(700);                                   // let the quote populate
$px = $m.ASK;
if ($px == 0) { MsgLog("FL LONG refused: no ASK for ", $FL_SYM); return; }

$stopDist = Round($stopMult * $FL_ATR, 2);
if ($stopDist < 0.02) { MsgLog("FL LONG refused: stop too tight ", $stopDist); return; }

$negSlip = 0 - $entrySlip;
$entry   = Round($px - $negSlip, 2);          // ASK + slip, via subtraction (see 04 F1)
$trigger = Round($px - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

$oe = "B " + $FL_QTY;
$oe = $oe + " " + $FL_SYM;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
MsgLog("FL ENTRY [", $oe, "] atr=", $FL_ATR, " stopDist=", $stopDist);
NewOrderObj($oe).Send();

Wait(1100);                                   // one Send() per second
$pos = $m.POS;
if ($pos < 1) {
  MsgLog("FL NOSTOP ", $FL_SYM, " unfilled POS=", $pos);
  return;
}

$os = "S " + $pos;
$os = $os + " " + $FL_SYM;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";
MsgLog("FL STOP [", $os, "]");
NewOrderObj($os).Send();
MsgLog("FL DONE LONG ", $FL_SYM, " ", $pos, " entry~", $entry, " stop ", $trigger);
