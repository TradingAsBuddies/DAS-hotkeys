// ============================================================================
// 22-fl-flatten.das  —  close ONE symbol's position on the PAPER account
// ============================================================================
// Injected once per open symbol by tools/fl_forward_test.py at the EOD gate,
// after it sets:
//   $FL_SYM    the symbol
//   $FL_SIDE   "S" to close a long, "B" to cover a short  (driver decides)
//   $FL_QTY    shares to close (unsigned)
// Sends a limit through the spread, then re-checks. Works at any hour.
//
// WHY NOT Panic: verified 2026-09-24 07:21 ET on TR4425 that
//   Panic ACCOUNT=TR4425  ->  "PANIC can only run in market hours!"
// so a premarket or after-hours flatten that relies on it leaves positions
// open with their stops already cancelled. Panic stays as an RTH fallback
// in the driver, never as the primary path.
//
// No MsgBox: a modal freezes the CMD API.
// ============================================================================

$closeSlip = 0.15;

// $FL_SIDE and $FL_QTY come from the driver, which reads the SIGNED position
// from the API (%POS Type 3 = short). The montage .POS property is unsigned
// on this build: on 2026-09-25 a 300-share short read as POS=300 and a
// sign-based close SOLD 300 more. Never derive the side from .POS.
if ($FL_SYM == "")  { MsgLog("FL CLOSE refused: no symbol"); return; }
if ($FL_QTY < 1)    { MsgLog("FL CLOSE refused: qty ", $FL_QTY); return; }
if ($FL_SIDE != "S") {
  if ($FL_SIDE != "B") { MsgLog("FL CLOSE refused: side must be S or B, got ", $FL_SIDE); return; }
}
$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgLog("FL CLOSE refused: no montage1"); return; }

$m.SYMBOL = $FL_SYM;
Wait(700);
if ($m.POS == 0) { MsgLog("FL CLOSE ", $FL_SYM, " already flat"); return; }

// cancel this symbol's resting orders first (the stop), so the close cannot
// double up with a stop fill
$acc = GetAccountObj("TR4425");
if (isObject($acc) == 1) { $acc.CancelOrder("BUY|SELL", $FL_SYM); }
Wait(1100);

if ($FL_SIDE == "S") {
  $px = Round($m.BID - $closeSlip, 2);
} else {
  $negSlip = 0 - $closeSlip;
  $px = Round($m.ASK - $negSlip, 2);
}
$o = $FL_SIDE + " " + $FL_QTY;
$o = $o + " " + $FL_SYM;
$o = $o + " L " + $px;
$o = $o + " D+";
MsgLog("FL CLOSE [", $o, "] montage POS=", $m.POS);
NewOrderObj($o).Send();
Wait(1500);
MsgLog("FL CLOSE ", $FL_SYM, " POS now ", $m.POS);
