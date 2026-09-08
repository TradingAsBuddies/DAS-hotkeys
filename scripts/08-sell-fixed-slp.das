// ==========================================================
// 08-sell-fixed-slp.das   SHORT, 11c SLP stop
// One hotkey. Montage window must be named  montage1
// Mirror of 07. Signs flip, argument ORDER never does.
// ==========================================================
//
// LINES ARE KEPT SHORT ON PURPOSE. See the header of 07 --
// a 71-char order line lost 28 characters from its middle in
// transit and became the nonexistent function $sSend().
// Every order string here is built in steps and PRINTED
// before sending, so a mangled paste is caught by eye rather
// than sent as a malformed order.
// ==========================================================

// ---- inputs ----------------------------------------------
$stopDist    = 0.11;
$limitSlip   = 0.05;
$entrySlip   = 0.15;
$riskDollars = 0;

// ---- montage ---------------------------------------------
$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }

$sym = $m.GetTicker();
$px  = $m.BID;
$qty = $m.Share;

if ($sym == "") { MsgBox("no symbol"); return; }
if ($px == 0)   { MsgBox("no BID"); return; }

if ($riskDollars > 0) {
  $qty = Round($riskDollars / $stopDist, 100);
}
if ($qty < 1) { MsgBox("qty is " + $qty); return; }

// ---- prices: subtraction only ----------------------------
// `+` threw ScriptError:100 Invalid parameter inside Round()
// on 2026-09-08 12:44. Negate first, subtract always.
$negStop = 0 - $stopDist;
$negSlip = 0 - $limitSlip;

$entry   = Round($px - $entrySlip, 2);
$trigger = Round($px - $negStop, 2);
$limit   = Round($trigger - $negSlip, 2);

// ---- build entry string ----------------------------------
$oe = "SS " + $qty;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";

MsgBox("ENTRY [" + $oe + "]");

NewOrderObj($oe).Send();
Wait(1100);

// ---- arm cover only against a real position --------------
// Guards on MAGNITUDE. The 07 long logged "Positio:5"; what
// POS reports for a short is still unobserved. Abs() is
// correct under either convention and still makes a naked
// long unreachable.
$pos = $m.POS;
$sz  = Abs($pos);

if ($sz < 1) {
  MsgBox("NO STOP. Unfilled, POS=" + $pos);
  MsgLog("SHORT ", $sym, " unfilled, no stop");
  return;
}

// ---- build stop string -----------------------------------
$os = "B " + $sz;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";

MsgBox("STOP [" + $os + "]");

NewOrderObj($os).Send();
MsgLog("SHORT ", $sym, " ", $sz, " stop ", $trigger);


// ==========================================================
// On DELL Bid 527.66 this builds:
//   ENTRY [SS 5 DELL L 527.51 D+]
//   STOP  [B 5 DELL SLP 527.77 527.82 D+]
//
// If either box shows a string missing a chunk, the paste was
// truncated -- do not press OK, fix the script.
// ==========================================================
