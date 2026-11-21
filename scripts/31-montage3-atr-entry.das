// ==========================================================
// 31-montage3-atr-entry.das   limit entry + 1 x ATR(14) SLP stop
// Block A = LONG.  Block B = SHORT.  Built into no-key hotkeys
// m3.long_1atr / m3.short_1atr by tools/gen_htk.py
// (scripts/htk/montage3.json); each montage3 button runs one
// line: ExecHotkey("m3.long_1atr"); or ExecHotkey("m3.short_1atr");
//
// From 06-entry-with-slp-stop.das (Kestrel session, 2026-11-19).
// Reworked 2026-11-21 after a replay session with the operator:
//   - No MsgBox once an order is out. The old STOP confirmation box left
//     a filled position without a stop for 68 s. A box now appears only
//     on a refusal (nothing sent) or when a stop could not be trusted.
//   - Entry is a limit 0.05 through the touch (ASK + 0.05 / BID - 0.05),
//     the operator choice. It was 0.15.
//   - The stop follows the fill by itself, as 30-bracket-at-fill.das:
//     poll the position up to 10 s, cancel whatever is still working on
//     the symbol (only the entry can be: the button refuses unless flat),
//     re-read the position, send the SLP stop for exactly that size, then
//     re-read once more and log NOSTOP MISMATCH if it changed.
//   - Unfilled after the poll: the entry is cancelled, nothing rests.
//   - Orders carry the montage account and, for the entry, the montage
//     route. A string with no route took route and type from the order
//     template ("SMAT", a stop type) [V 2026-11-21, object fields logged].
//     The stop has no route: the guide says STOP route is the default.
//   - After the stop is sent the script reads the order id DAS writes onto
//     the order object it holds. No id means not accepted: it says NO STOP.
//     [V replay 2026-11-21: the id matched the trade log every time.
//     GetOrderObj() found no order by any filter, and Status stays "N/A".]
//   - A new entry clears $M3_OA/B/C, the range-order objects script 33
//     keeps, so script 34 never acts on a previous trade.
//   - $M3_SYM / $M3_SIDE / $M3_STOP record the side and stop sent, for
//     FLATTEN (script 32) and TARGETS (script 33): the montage POS is
//     unsigned and a resting stop cannot be read back.
// Study name "ATR(14)" on montage3_chart1; a missing study reads 0.
// SIZE. qty is the most whole shares for which
//   qty x (stop distance + entry slip + stop-limit slip) <= 1R,
// where R is the money risk unit for the montage account. There is one R
// per account (SIM and LIVE differ): the globals $BAF_ACCT1..3 / $BAF_R1..3
// that tools/baf_rconfig.py writes from the private R-CONFIG table into
// scripts/local/baf-rconfig.das, loaded by the Desktop Load Script. R is
// never typed here. No R for the account, or under one share: it refuses.
// The montage Share box is no longer used. $stopMult = 1.0.
// At the fill it records $M3_ENTRY (average cost) and $M3_R (the stop
// distance per share) so script 33 sets targets from the R taken at entry.
// [V replay 2026-11-21 14:58-15:15 ET, montage locked] one press each:
// SHORT went out as "SHORT <sym> 5 REB25 Limit", filled the same second, the
// stop followed 1 s later; LONG the same with a sell stop below. Earlier
// that day entries with no route, or with the montage on route MARKET,
// went out as "SMAT Trailer 0.3" and took 3-10 s: that was the string,
// not replay. Live paper in regular hours is still to do.
// ==========================================================

// ==========================================================
// BLOCK A - LONG
// ==========================================================
$stopMult  = 1.0;
$limitSlip = 0.20;
$entrySlip = 0.05;

$c = GetWindowObj("montage3_chart1");
$m = GetWindowObj("montage3");
if (isObject($c) == 0) { MsgBox("no montage3_chart1"); return; }
if (isObject($m) == 0) { MsgBox("no montage3"); return; }

$atr  = $c.GetStudyVal("ATR(14)");
$sym  = $m.GetTicker();
$px   = $m.ASK;
$rt   = $m.Route;
$acct = $m.Account;

if ($atr == 0)   { MsgLog("LONG refused: no ATR(14)"); MsgBox("no ATR(14) - check study"); return; }
if ($sym == "")  { MsgLog("LONG refused: no symbol"); MsgBox("no symbol"); return; }
if ($px == 0)    { MsgLog("LONG refused: no ASK"); MsgBox("no ASK"); return; }
if ($rt == "")   { MsgLog("LONG refused: no route"); MsgBox("no route on montage3"); return; }
if ($acct == "") { MsgLog("LONG refused: no account"); MsgBox("no account on montage3"); return; }
if ($rt == "MARKET") { MsgLog("LONG refused: route MARKET"); MsgBox("montage3 route is MARKET - pick a limit route"); return; }
if ($m.POS != 0) { MsgLog("LONG refused: ", $sym, " POS ", $m.POS, ", not flat"); MsgBox("not flat - " + $sym); return; }

$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) { MsgLog("LONG refused: stop too tight"); MsgBox("stop too tight"); return; }

// ---- R for this account, in money (from baf-rconfig.das) ----
$r = 0;
if ($acct == $BAF_ACCT1) { $r = $BAF_R1; }
if ($acct == $BAF_ACCT2) { $r = $BAF_R2; }
if ($acct == $BAF_ACCT3) { $r = $BAF_R3; }
if ($r <= 0) { MsgLog("LONG refused: no R for the montage3 account (R-CONFIG not loaded?)"); MsgBox("no R for this account - load R-CONFIG"); return; }

// ---- size: the most shares that lose no more than 1R at the stop limit ----
$riskPer = $stopDist + $entrySlip;
$riskPer = $riskPer + $limitSlip;
$qty = 0;
while ((($qty + 10) * $riskPer) <= $r) {
  $qty = $qty + 10;
}
while ((($qty + 1) * $riskPer) <= $r) {
  $qty = $qty + 1;
}
if ($qty < 1) { MsgLog("LONG refused: 1R buys 0 shares at stop distance ", $stopDist); MsgBox("1R is under one share"); return; }
$bp = GetAccountObj($acct).BP;
if ($qty * $px > $bp) { MsgLog("LONG refused: ", $qty, " shares is over buying power"); MsgBox("over buying power"); return; }

$entry   = Round($px + $entrySlip, 2);
$trigger = Round($px - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

// ---- entry: no MsgBox from here until the stop is out ----
$oe = "B " + $qty;
$oe = $oe + " " + $sym;
$oe = $oe + " " + $rt;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
$M3_SYM = $sym;
$M3_SIDE = "L";
$M3_STOP = $trigger;
$M3_BUSY = 0;
$M3_OA = 0;
$M3_OB = 0;
$M3_OC = 0;
MsgLog("LONG ENTRY SENT [", $oe, "] stop will be ", $trigger);
$o = NewOrderObj($oe);
$o.account = $acct;
$o.Send();

// ---- wait for the fill, up to 10 s -----------------------
$i = 0;
while ($i < 20) {
  Wait(500);
  if ($m.GetTicker() != $sym) {
    $m.SYMBOL = $sym;
    Wait(700);
  }
  if ($m.POS >= $qty) { $i = 20; }
  $i = $i + 1;
}

// ---- cancel what is left of the entry, then read the size --
GetAccountObj($acct).CancelOrder("BUY|SELL", $sym);
Wait(1100);
if ($m.GetTicker() != $sym) {
  $m.SYMBOL = $sym;
  Wait(700);
}
$pos = $m.POS;
if ($pos < 1) {
  MsgLog("LONG unfilled ", $sym, ": entry cancelled, no stop needed");
  return;
}

$M3_ENTRY = $m.AvgCost;
$M3_R = $stopDist;
// ---- stop on the filled quantity -------------------------
$os = "S " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";
$o = NewOrderObj($os);
$o.account = $acct;
$o.Send();
MsgLog("LONG STOP SENT [", $os, "]");

// ---- a fill after the read leaves shares without a stop --
Wait(1100);
if ($m.GetTicker() != $sym) {
  $m.SYMBOL = $sym;
  Wait(700);
}
if ($m.POS != $pos) {
  MsgLog("LONG NOSTOP MISMATCH ", $sym, " POS ", $m.POS, " stop for ", $pos);
  MsgBox("CHECK STOP - " + $sym);
  return;
}
// DAS fills in the order id on the object once it accepts the order
if ($o.oid == 0) {
  MsgLog("LONG NOSTOP NOT ACCEPTED ", $sym, ": no order id for the stop, ", $pos, " shares unprotected");
  MsgBox("NO STOP - " + $sym + " - stop was not accepted");
  return;
}
MsgLog("LONG DONE ", $sym, " ", $pos, " of ", $qty, " stop ", $trigger, " oid ", $o.oid);

// ==========================================================
// BLOCK B - SHORT
// ==========================================================
$stopMult  = 1.0;
$limitSlip = 0.20;
$entrySlip = 0.05;

$c = GetWindowObj("montage3_chart1");
$m = GetWindowObj("montage3");
if (isObject($c) == 0) { MsgBox("no montage3_chart1"); return; }
if (isObject($m) == 0) { MsgBox("no montage3"); return; }

$atr  = $c.GetStudyVal("ATR(14)");
$sym  = $m.GetTicker();
$px   = $m.BID;
$rt   = $m.Route;
$acct = $m.Account;

if ($atr == 0)   { MsgLog("SHORT refused: no ATR(14)"); MsgBox("no ATR(14) - check study"); return; }
if ($sym == "")  { MsgLog("SHORT refused: no symbol"); MsgBox("no symbol"); return; }
if ($px == 0)    { MsgLog("SHORT refused: no BID"); MsgBox("no BID"); return; }
if ($rt == "")   { MsgLog("SHORT refused: no route"); MsgBox("no route on montage3"); return; }
if ($acct == "") { MsgLog("SHORT refused: no account"); MsgBox("no account on montage3"); return; }
if ($rt == "MARKET") { MsgLog("SHORT refused: route MARKET"); MsgBox("montage3 route is MARKET - pick a limit route"); return; }
if ($m.POS != 0) { MsgLog("SHORT refused: ", $sym, " POS ", $m.POS, ", not flat"); MsgBox("not flat - " + $sym); return; }

$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) { MsgLog("SHORT refused: stop too tight"); MsgBox("stop too tight"); return; }

// ---- R for this account, in money (from baf-rconfig.das) ----
$r = 0;
if ($acct == $BAF_ACCT1) { $r = $BAF_R1; }
if ($acct == $BAF_ACCT2) { $r = $BAF_R2; }
if ($acct == $BAF_ACCT3) { $r = $BAF_R3; }
if ($r <= 0) { MsgLog("SHORT refused: no R for the montage3 account (R-CONFIG not loaded?)"); MsgBox("no R for this account - load R-CONFIG"); return; }

// ---- size: the most shares that lose no more than 1R at the stop limit ----
$riskPer = $stopDist + $entrySlip;
$riskPer = $riskPer + $limitSlip;
$qty = 0;
while ((($qty + 10) * $riskPer) <= $r) {
  $qty = $qty + 10;
}
while ((($qty + 1) * $riskPer) <= $r) {
  $qty = $qty + 1;
}
if ($qty < 1) { MsgLog("SHORT refused: 1R buys 0 shares at stop distance ", $stopDist); MsgBox("1R is under one share"); return; }
$bp = GetAccountObj($acct).BP;
if ($qty * $px > $bp) { MsgLog("SHORT refused: ", $qty, " shares is over buying power"); MsgBox("over buying power"); return; }

$negStop = 0 - $stopDist;
$negSlip = 0 - $limitSlip;
$entry   = Round($px - $entrySlip, 2);
$trigger = Round($px - $negStop, 2);
$limit   = Round($trigger - $negSlip, 2);

// ---- entry: no MsgBox from here until the stop is out ----
$oe = "SS " + $qty;
$oe = $oe + " " + $sym;
$oe = $oe + " " + $rt;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
$M3_SYM = $sym;
$M3_SIDE = "S";
$M3_STOP = $trigger;
$M3_BUSY = 0;
$M3_OA = 0;
$M3_OB = 0;
$M3_OC = 0;
MsgLog("SHORT ENTRY SENT [", $oe, "] stop will be ", $trigger);
$o = NewOrderObj($oe);
$o.account = $acct;
$o.Send();

// ---- wait for the fill, up to 10 s -----------------------
$i = 0;
while ($i < 20) {
  Wait(500);
  if ($m.GetTicker() != $sym) {
    $m.SYMBOL = $sym;
    Wait(700);
  }
  if ($m.POS >= $qty) { $i = 20; }
  $i = $i + 1;
}

// ---- cancel what is left of the entry, then read the size --
GetAccountObj($acct).CancelOrder("BUY|SELL", $sym);
Wait(1100);
if ($m.GetTicker() != $sym) {
  $m.SYMBOL = $sym;
  Wait(700);
}
$pos = $m.POS;
if ($pos < 1) {
  MsgLog("SHORT unfilled ", $sym, ": entry cancelled, no stop needed");
  return;
}

$M3_ENTRY = $m.AvgCost;
$M3_R = $stopDist;
// ---- stop on the filled quantity -------------------------
$os = "B " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";
$o = NewOrderObj($os);
$o.account = $acct;
$o.Send();
MsgLog("SHORT STOP SENT [", $os, "]");

// ---- a fill after the read leaves shares without a stop --
Wait(1100);
if ($m.GetTicker() != $sym) {
  $m.SYMBOL = $sym;
  Wait(700);
}
if ($m.POS != $pos) {
  MsgLog("SHORT NOSTOP MISMATCH ", $sym, " POS ", $m.POS, " stop for ", $pos);
  MsgBox("CHECK STOP - " + $sym);
  return;
}
// DAS fills in the order id on the object once it accepts the order
if ($o.oid == 0) {
  MsgLog("SHORT NOSTOP NOT ACCEPTED ", $sym, ": no order id for the stop, ", $pos, " shares unprotected");
  MsgBox("NO STOP - " + $sym + " - stop was not accepted");
  return;
}
MsgLog("SHORT DONE ", $sym, " ", $pos, " of ", $qty, " stop ", $trigger, " oid ", $o.oid);
