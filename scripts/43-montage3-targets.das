// ==========================================================
// 43-montage3-targets.das   scale out in thirds at 1R, 2R, 3R
// Built into the no-key hotkey m3.targets by tools/gen_htk.py
// (scripts/htk/montage3.json); the second-row montage3 button runs
// ExecHotkey("m3.targets");
//
// WHAT ONE PRESS DOES
//   1. Refuses unless montage3 holds 3 or more shares of a symbol whose
//      side and stop price script 41 recorded ($M3_SYM, $M3_SIDE,
//      $M3_STOP). The montage POS is unsigned, so a position opened any
//      other way has no known side and is refused.
//   2. R (per share) and the entry price are the ones script 41 recorded
//      at the fill ($M3_R, $M3_ENTRY).
//   3. Cancels every working order on the symbol (the single full-size
//      stop), then sends THREE range orders, one third of the position
//      each, the remainder on the last:
//        target 1R / stop,  target 2R / stop,  target 3R / stop.
//      A range order is one order with both prices. The STOP price goes
//      first, then the target, on both sides: the guide examples are
//      "B 100 TSLA RG 300.23 270.58" and "S 100 TSLA RG 270.58 300.23"
//      [D adv guide p.28]. Its sentence "for buy orders the lower price
//      should go first" is wrong: on 2026-11-21 (replay) "B 1 <sym> RG
//      <target> <stop>" raised the dialog "low price is higher than high
//      price" and Send Order error [V]. So each third carries its own stop, and a
//      filled target takes its share of the stop with it. Three plain
//      limit targets beside one full-size stop would leave that stop too
//      large after the first target fills.
//   4. Reads the order id DAS writes onto each order object once it accepts
//      the order. A missing id means that third has no stop: it says so in
//      the log and in a box. A refused order also raises a DAS dialog that
//      holds the script until it is dismissed.
//
// Between the cancel and the last send (about 3.5 s; DAS allows one order
// a second) part of the position has no stop. No MsgBox after the cancel.
//
// [V replay 2026-11-21, montage locked, both sides] the single LimitP stop
// was cancelled and three "Range <stop> <target>" orders were accepted one
// second apart with no route in the string; with no targets hit, all three
// later stopped out together and left the position flat. NOT yet seen: a
// target filling and leaving the other two; live paper; range orders
// outside regular hours (script 44 swaps them for a LimitP stop).
// It sets $M3_BUSY while it runs: a second m3 button pressed part-way
// interleaved with it on 2026-11-21. PING clears a stuck flag.
// If DAS opens an order dialog after a press, cancel it: the order string
// was refused.
// ==========================================================

$m = GetWindowObj("montage3");
if (isObject($m) == 0) { MsgLog("TARGETS refused: no montage3"); MsgBox("no montage3"); return; }
$sym  = $m.GetTicker();
$pos  = $m.POS;
$avg  = $m.AvgCost;
$acct = $m.Account;
if ($sym == "")  { MsgLog("TARGETS refused: no symbol"); MsgBox("no symbol"); return; }
if ($acct == "") { MsgLog("TARGETS refused: no account"); MsgBox("no account on montage3"); return; }
if ($pos < 3)    { MsgLog("TARGETS refused: ", $sym, " POS ", $pos, ", need 3 or more"); MsgBox("need 3+ shares - " + $sym); return; }
if ($avg == 0)   { MsgLog("TARGETS refused: no average cost"); MsgBox("no average cost"); return; }
if ($M3_SYM != $sym) { MsgLog("TARGETS REFUSED ", $sym, ": side and stop not recorded"); MsgBox("no recorded entry - " + $sym); return; }

// The recorded side belongs to ONE position. If that one was closed (a stop
// hit, a hand close) and another opened some other way, the average cost
// differs from the one script 41 recorded, and acting on the old side
// could double the position instead of closing it. Refuse.
$d = $m.AvgCost - $M3_ENTRY;
if ($M3_ENTRY == 0) { $d = 1; }
$same = 1;
if ($d > 0.01) { $same = 0; }
if ($d < -0.01) { $same = 0; }
if ($same == 0) { MsgLog("TARGETS REFUSED ", $sym, ": average cost ", $m.AvgCost, " is not the recorded entry ", $M3_ENTRY); MsgBox("not the recorded position - " + $sym); return; }

$stop = $M3_STOP;
$dir = 0;
if ($M3_SIDE == "L") { $dir = 1; }
if ($M3_SIDE == "S") { $dir = 2; }
if ($dir == 0)  { MsgLog("TARGETS REFUSED ", $sym, ": side not recorded"); MsgBox("no recorded side - " + $sym); return; }
if ($stop == 0) { MsgLog("TARGETS REFUSED ", $sym, ": stop not recorded"); MsgBox("no recorded stop - " + $sym); return; }

// R per share and the entry price are the ones script 41 recorded at the
// fill, so targets do not move if the stop or the average cost changes
$r = $M3_R;
if ($M3_ENTRY > 0) { $avg = $M3_ENTRY; }
if ($r < 0.02) { MsgLog("TARGETS REFUSED ", $sym, ": R not recorded"); MsgBox("no recorded R - " + $sym); return; }

// one third, rounded down; the remainder rides on the 3R order
$q = 0;
while ((($q + 10) * 3) <= $pos) {
  $q = $q + 10;
}
while ((($q + 1) * 3) <= $pos) {
  $q = $q + 1;
}
$q3 = $pos - $q - $q;

$r2 = $r + $r;
$r3 = $r2 + $r;
$t1 = Round($avg + $r, 2);
$t2 = Round($avg + $r2, 2);
$t3 = Round($avg + $r3, 2);
$side = "S";
if ($dir == 2) {
  $t1 = Round($avg - $r, 2);
  $t2 = Round($avg - $r2, 2);
  $t3 = Round($avg - $r3, 2);
  $side = "B";
}

if ($M3_BUSY == 1) { MsgLog("TARGETS refused: another m3 button is still running"); MsgBox("busy - wait, or PING to clear"); return; }
$M3_BUSY = 1;
// A stop order placed at a price the market is already through triggers at
// once and can leave its limit resting unfilled (seen 2026-11-21 in replay).
$thru = 0;
if ($dir == 1) { if ($m.BID <= $stop) { $thru = 1; } }
if ($dir == 2) { if ($m.ASK >= $stop) { $thru = 1; } }
if ($thru == 1) { $M3_BUSY = 0; MsgLog("TARGETS REFUSED ", $sym, ": price is already through the stop ", $stop, ", use FLATTEN"); MsgBox("price is through the stop - FLATTEN " + $sym); return; }
MsgLog("TARGETS ", $sym, " POS ", $pos, " cost ", $avg, " stop ", $stop, " R ", $r, ": cancelling, then 3 range orders");
GetAccountObj($acct).CancelOrder("BUY|SELL", $sym);
Wait(1100);
if ($m.POS != $pos) { $M3_BUSY = 0; MsgLog("TARGETS STOPPED ", $sym, ": POS changed to ", $m.POS, ", NO STOP resting"); MsgBox("TARGETS stopped - CHECK STOP " + $sym); return; }

// stop price first, then the target, on both sides (see the header)
$o1 = $side + " " + $q;
$o1 = $o1 + " " + $sym;
$o1 = $o1 + " RG " + $stop;
$o1 = $o1 + " " + $t1;
$o1 = $o1 + " D+";
$M3_OA = NewOrderObj($o1);
$M3_OA.account = $acct;
$M3_OA.Send();
MsgLog("TARGETS 1R send attempted [", $o1, "]");
Wait(1100);

$o2 = $side + " " + $q;
$o2 = $o2 + " " + $sym;
$o2 = $o2 + " RG " + $stop;
$o2 = $o2 + " " + $t2;
$o2 = $o2 + " D+";
$M3_OB = NewOrderObj($o2);
$M3_OB.account = $acct;
$M3_OB.Send();
MsgLog("TARGETS 2R send attempted [", $o2, "]");
Wait(1100);

$o3 = $side + " " + $q3;
$o3 = $o3 + " " + $sym;
$o3 = $o3 + " RG " + $stop;
$o3 = $o3 + " " + $t3;
$o3 = $o3 + " D+";
$M3_OC = NewOrderObj($o3);
$M3_OC.account = $acct;
$M3_OC.Send();
MsgLog("TARGETS 3R send attempted [", $o3, "]");

// DAS fills in the order id on each object once it accepts the order
Wait(1100);
$bad = 0;
if ($M3_OA.oid == 0) { $bad = $bad + 1; }
if ($M3_OB.oid == 0) { $bad = $bad + 1; }
if ($M3_OC.oid == 0) { $bad = $bad + 1; }
MsgLog("TARGETS order ids: 1R ", $M3_OA.oid, ", 2R ", $M3_OB.oid, ", 3R ", $M3_OC.oid);
if ($bad > 0) {
  $M3_BUSY = 0;
  MsgLog("TARGETS INCOMPLETE ", $sym, ": ", $bad, " of 3 range orders not accepted, part of the position has NO STOP");
  MsgBox("CHECK ORDERS - " + $sym + " - range order not accepted");
  return;
}
$M3_BUSY = 0;
MsgLog("TARGETS sent for ", $sym, ": ", $q, " + ", $q, " + ", $q3, " (check Orders: 3 range orders)");
