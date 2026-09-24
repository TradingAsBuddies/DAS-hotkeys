// ============================================================================
// 22-fl-flatten.das  —  close ONE symbol's position on the PAPER account
// ============================================================================
// Injected once per open symbol by tools/fl_forward_test.py at the EOD gate,
// after it sets:
//   $FL_SYM   the symbol
// It reads the live position from montage1 and sends the opposite side as a
// limit through the spread, then re-checks. Works at any hour.
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

if ($FL_SYM == "") { MsgLog("FL CLOSE refused: no symbol"); return; }
$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgLog("FL CLOSE refused: no montage1"); return; }

$m.SYMBOL = $FL_SYM;
Wait(700);
$pos = $m.POS;
if ($pos == 0) { MsgLog("FL CLOSE ", $FL_SYM, " already flat"); return; }

// cancel this symbol's resting orders first (the stop), so the close cannot
// double up with a stop fill
$acc = GetAccountObj("TR4425");
if (isObject($acc) == 1) { $acc.CancelOrder("BUY|SELL", $FL_SYM); }
Wait(1100);

if ($pos > 0) {
  $px = Round($m.BID - $closeSlip, 2);
  $o  = "S " + $pos;
  $o  = $o + " " + $FL_SYM;
  $o  = $o + " L " + $px;
  $o  = $o + " D+";
} else {
  $sz = Abs($pos);
  $negSlip = 0 - $closeSlip;
  $px = Round($m.ASK - $negSlip, 2);
  $o  = "B " + $sz;
  $o  = $o + " " + $FL_SYM;
  $o  = $o + " L " + $px;
  $o  = $o + " D+";
}
MsgLog("FL CLOSE [", $o, "] from POS=", $pos);
NewOrderObj($o).Send();
Wait(1500);
MsgLog("FL CLOSE ", $FL_SYM, " POS now ", $m.POS);
