// ==========================================================
// 42-montage-exits.das   exits for a locked montage
// Block A = CANCEL (this symbol, both sides).  Block B = FLATTEN.
// Built into no-key hotkeys m3.cancel / m3.flatten by tools/gen_htk.py
// (scripts/htk/montage3.json); the montage3 panel buttons run them with
// ExecHotkey.
//
// 2026-11-21 (replay, montage locked): the first version used the montage
// own commands (CXL ALLSYMB; Route=Market; Share=Pos; Send=Reverse). They
// ran, logged success, and did nothing: no cancel, no order. Route=Market
// also raised "Properity Market not exist". So exits use only what got
// through that day: the account object for cancels (as 22-fl-flatten.das)
// and an order object for the close (as script 41 sends its orders).
//
// [V replay 2026-11-21 15:15 ET, montage locked] CANCEL cancelled a resting
// stop; FLATTEN covered a short with B and closed a long with S, each as
// a "REB25 Limit" filled the same second, and logged FLAT. With no side
// recorded it refused. Live paper in regular hours is still to do.
//
// The montage .POS is unsigned on this build (22-fl-flatten.das), so
// FLATTEN cannot tell long from short by itself. Script 41 records the side
// it opened in $M3_SIDE / $M3_SYM. FLATTEN refuses when that record does
// not match the montage symbol; then use the Panic hotkey.
// Before any m3 entry this session, reading $M3_SYM logs one
// "variable not exist" script error and FLATTEN refuses. That is expected.
//
// The close is a limit 0.15 through the spread on the montage route (any
// hour). When the montage route is MARKET or STOP, which cannot carry a
// limit, it is a market order (regular hours only; UNTESTED [I]). Market
// orders are for FLATTEN only: entries are always limits. No MsgBox: an
// exit must never wait for a click.
// Every log line states what was sent, not that it worked.
// [V replay 2026-11-22 01:00-01:04 ET, API and button] with the default
// account different from the montage account: the old close was prepared
// on the default account and never accepted; with .account set it was
// accepted and filled on the montage account the same second.
// UNTESTED [I]: the market-order path on route MARKET or STOP.
// ==========================================================


// ==========================================================
// BLOCK A - CANCEL
// ==========================================================
$m = GetWindowObj("montage3");
if (isObject($m) == 0) { MsgLog("EXIT cancel refused: no montage3"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgLog("EXIT cancel refused: no symbol"); return; }
$acc = GetAccountObj($m.Account);
if (isObject($acc) == 0) { MsgLog("EXIT cancel refused: no account object"); return; }
$acc.CancelOrder("BUY|SELL", $sym);
MsgLog("EXIT cancel sent for ", $sym, " (check Orders)");


// ==========================================================
// BLOCK B - FLATTEN
// ==========================================================
$closeSlip = 0.15;

$m = GetWindowObj("montage3");
if (isObject($m) == 0) { MsgLog("EXIT flatten refused: no montage3"); return; }
$sym = $m.GetTicker();
$rt  = $m.Route;
$pos = $m.POS;
if ($sym == "") { MsgLog("EXIT flatten refused: no symbol"); return; }
if ($rt == "")  { MsgLog("EXIT flatten refused: no route"); return; }
if ($pos < 1)   { MsgLog("EXIT flatten ", $sym, ": POS ", $pos, ", nothing to close"); return; }
if ($M3_SYM != $sym) { MsgLog("EXIT flatten REFUSED ", $sym, ": side not recorded, use Panic"); return; }

// The recorded side belongs to ONE position. If that one was closed (a stop
// hit, a hand close) and another opened some other way, the average cost
// differs from the one script 41 recorded, and acting on the old side
// could double the position instead of closing it. Refuse.
$d = $m.AvgCost - $M3_ENTRY;
if ($M3_ENTRY == 0) { $d = 1; }
$same = 1;
if ($d > 0.01) { $same = 0; }
if ($d < -0.01) { $same = 0; }
if ($same == 0) { MsgLog("EXIT flatten REFUSED ", $sym, ": average cost ", $m.AvgCost, " is not the recorded entry ", $M3_ENTRY, ", use Panic"); return; }

$side = "X";
if ($M3_SIDE == "S") { $side = "B"; }
if ($M3_SIDE == "L") { $side = "S"; }
if ($side == "X") { MsgLog("EXIT flatten REFUSED ", $sym, ": side not recorded, use Panic"); return; }

// cancel first, so a resting stop cannot fill on top of the close
$acc = GetAccountObj($m.Account);
if (isObject($acc) == 1) { $acc.CancelOrder("BUY|SELL", $sym); }
Wait(1100);

$px = Round($m.BID - $closeSlip, 2);
if ($side == "B") {
  $negSlip = 0 - $closeSlip;
  $px = Round($m.ASK - $negSlip, 2);
}
$o = $side + " " + $pos;
$o = $o + " " + $sym;
// 2026-11-21: with the montage on route MARKET, "... MARKET L <px> D+"
// was refused (Send Order error) after the stop was already cancelled.
// 2026-11-22: after a restart the montage came back on route STOP, which
// cannot carry a limit either. On those two routes FLATTEN sends a market
// order so it still closes (operator, 2026-11-22: a market order is right
// for FLATTEN; entries stay limits). Any other route takes the limit.
$mkt = 0;
if ($rt == "MARKET") { $mkt = 1; }
if ($rt == "STOP") { $mkt = 1; }
if ($mkt == 1) {
  $o = $o + " MARKET M D+";
}
if ($mkt == 0) {
  $o = $o + " " + $rt;
  $o = $o + " L " + $px;
  $o = $o + " D+";
}
MsgLog("EXIT flatten sending [", $o, "]");
// 2026-11-22: this order used to go out with no account set. That worked
// while the default account matched the montage. After a desktop restore the
// default differed: the close was never accepted, twice, AFTER the stop had
// been cancelled. The order now names the montage account, as entries do.
$oc = NewOrderObj($o);
$oc.account = $m.Account;
$oc.Send();
// 2026-11-21: a 1.5 s check logged "POS now 5" one second before the fill.
// Poll up to 10 s, then say plainly whether it closed.
$i = 0;
while ($i < 20) {
  Wait(500);
  if ($m.POS < 1) { $i = 20; }
  $i = $i + 1;
}
if ($m.POS < 1) {
  MsgLog("EXIT flatten ", $sym, " FLAT");
  return;
}
MsgLog("EXIT flatten ", $sym, " NOT CLOSED after 10 s, POS ", $m.POS, ", NO STOP resting");
