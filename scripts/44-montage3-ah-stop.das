// ==========================================================
// 44-montage3-ah-stop.das   after hours: one LimitP stop for the position
// Built into the no-key hotkey m3.ahstop by tools/gen_htk.py
// (scripts/htk/montage3.json); the second-row montage3 button runs
// ExecHotkey("m3.ahstop");
//
// WHY. The 1R 2R 3R button (script 43) leaves three range orders. A range
// order is a regular-hours order as far as is known; the LimitP stop is the
// pre/post-market type. At the 16:00 ET close the operator presses this to
// swap whatever script 43 left for ONE LimitP stop covering the whole
// remaining position. No targets rest after hours: DAS has no OCO for
// order objects (properties OCO, Trigger, TriggerOrder do not exist, probed
// 2026-11-21), and three stops beside three unlinked targets would leave
// the stops larger than the position after the first target fills.
//
// WHAT ONE PRESS DOES
//   1. Refuses unless montage3 holds a position whose side and stop price
//      script 41 recorded, and no other m3 button is still running.
//   2. Cancels every working order on the symbol (through the account).
//   3. Sends ONE LimitP stop for the whole position.
//   4. Waits 1.1 s and reads the order object it holds. DAS fills in the
//      order id once an order is accepted [V replay 2026-11-21: the id on
//      the held object matched the trade log each time]. No id: it sends
//      once more; still none: a box says NO STOP.
//   Between 2 and 3 the position has no stop for about half a second.
//
// WHY NOT "new stop first". Tried 2026-11-21 (replay): the new stop was
// accepted, but Cancel() on the range-order objects script 43 kept
// cancelled nothing, and GetOrderObj() finds no order at all, so there was
// no way to remove only the range orders. The stop and the range orders
// then rested together, twice the position, until CANCEL was pressed.
//
// WHY THE BUSY FLAG. That press also came while script 43 was still
// between its 2R and 3R sends: the two scripts interleaved. Scripts 43
// and 44 now set $M3_BUSY while they run and refuse while it is set. A
// script that dies part-way leaves it set: PING clears it.
//
// [V replay 2026-11-21 16:35-16:38 ET, both sides, run over the CMD API]
// three range orders cancelled, one LimitP stop accepted within a second,
// its order id read back; FLATTEN then cancelled it and closed the
// position. UNTESTED [I]: live paper, and anything after hours.
// ==========================================================
$limitSlip = 0.20;

$m = GetWindowObj("montage3");
if (isObject($m) == 0) { MsgLog("AHSTOP refused: no montage3"); MsgBox("no montage3"); return; }
$sym  = $m.GetTicker();
$pos  = $m.POS;
$acct = $m.Account;
if ($sym == "")  { MsgLog("AHSTOP refused: no symbol"); MsgBox("no symbol"); return; }
if ($acct == "") { MsgLog("AHSTOP refused: no account"); MsgBox("no account on montage3"); return; }
if ($pos < 1)    { MsgLog("AHSTOP refused: ", $sym, " POS ", $pos); MsgBox("no position - " + $sym); return; }
if ($M3_SYM != $sym) { MsgLog("AHSTOP REFUSED ", $sym, ": side and stop not recorded"); MsgBox("no recorded entry - " + $sym); return; }

$stop = $M3_STOP;
$dir = 0;
if ($M3_SIDE == "L") { $dir = 1; }
if ($M3_SIDE == "S") { $dir = 2; }
if ($dir == 0)  { MsgLog("AHSTOP REFUSED ", $sym, ": side not recorded"); MsgBox("no recorded side - " + $sym); return; }
if ($stop == 0) { MsgLog("AHSTOP REFUSED ", $sym, ": stop not recorded"); MsgBox("no recorded stop - " + $sym); return; }

$side = "S";
$limit = Round($stop - $limitSlip, 2);
if ($dir == 2) {
  $side = "B";
  $negSlip = 0 - $limitSlip;
  $limit = Round($stop - $negSlip, 2);
}
$os = $side + " " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $stop;
$os = $os + " " + $limit;
$os = $os + " D+";

if ($M3_BUSY == 1) { MsgLog("AHSTOP refused: another m3 button is still running"); MsgBox("busy - wait, or PING to clear"); return; }
$M3_BUSY = 1;

MsgLog("AHSTOP ", $sym, " POS ", $pos, ": cancelling all, then one LimitP stop at ", $stop);
GetAccountObj($acct).CancelOrder("BUY|SELL", $sym);
Wait(600);
if ($m.POS != $pos) { $M3_BUSY = 0; MsgLog("AHSTOP STOPPED ", $sym, ": POS changed to ", $m.POS, ", NO STOP resting"); MsgBox("AH STOP stopped - CHECK STOP " + $sym); return; }

$M3_OS = NewOrderObj($os);
$M3_OS.account = $acct;
$M3_OS.Send();
MsgLog("AHSTOP send attempted [", $os, "]");
Wait(1100);
if ($M3_OS.oid == 0) {
  MsgLog("AHSTOP no order id, sending once more");
  $M3_OS = NewOrderObj($os);
  $M3_OS.account = $acct;
  $M3_OS.Send();
  Wait(1100);
}
$M3_BUSY = 0;
if ($M3_OS.oid == 0) {
  MsgLog("AHSTOP NOT ACCEPTED ", $sym, ": NO STOP resting for ", $pos, ". CHECK ORDERS");
  MsgBox("NO STOP - " + $sym + " - AH STOP was not accepted");
  return;
}
MsgLog("AHSTOP done ", $sym, ": one LimitP stop for ", $pos, " at ", $stop, ", oid ", $M3_OS.oid, " (check Orders: exactly one order)");
