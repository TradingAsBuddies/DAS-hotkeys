// ==========================================================
// 07-buy-fixed-slp.das   BUY, 11c SLP stop
// One hotkey. Montage window must be named  montage1
// ==========================================================
//
// VERIFIED on SIM TR4425, POET, 2026-09-08 07:26:06
//   Execute,Buy,POET,5,7.98      filled at the offer
//   Accept,Sell,POET,5,7.87,SLP:7.87 7.82
//   realized risk 7.98-7.87 = 0.11 exactly
//
// LINES ARE KEPT SHORT ON PURPOSE.
// On 2026-09-08 13:29 a 71-char order line reached DAS with
// 28 characters missing from its middle:
//   sent: NewOrderObj("SS " + $qty + " " + $sym + " L " ...
//   got:  NewOrderObj("SS " + $qty + " " + $sSend();
//   -> ScriptError:1 Function $sSend not exist!
// Long concatenated lines do not survive reliably. Every
// order string below is assembled in short steps and PRINTED
// before it is sent, so a mangled paste is visible instead of
// being sent as a malformed order.
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
$px  = $m.ASK;
$qty = $m.Share;

if ($sym == "") { MsgBox("no symbol"); return; }
if ($px == 0)   { MsgBox("no ASK"); return; }

if ($riskDollars > 0) {
  $qty = Round($riskDollars / $stopDist, 100);
}
if ($qty < 1) { MsgBox("qty is " + $qty); return; }

// ---- prices: subtraction only ----------------------------
// `+` threw ScriptError:100 Invalid parameter inside Round()
// on 2026-09-08 12:44. Negating first avoids the question.
$negSlip = 0 - $entrySlip;

$entry   = Round($px - $negSlip, 2);
$trigger = Round($px - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

// ---- build entry string ----------------------------------
$oe = "B " + $qty;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";

MsgBox("ENTRY [" + $oe + "]");

NewOrderObj($oe).Send();
Wait(1100);

// ---- arm stop only against a real position ---------------
$pos = $m.POS;
if ($pos < 1) {
  MsgBox("NO STOP. Unfilled, POS=" + $pos);
  MsgLog("BUY ", $sym, " unfilled, no stop");
  return;
}

// ---- build stop string -----------------------------------
$os = "S " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";

MsgBox("STOP [" + $os + "]");

NewOrderObj($os).Send();
MsgLog("BUY ", $sym, " ", $pos, " stop ", $trigger);


// ==========================================================
// Once you trust it, delete the two MsgBox lines. Keep the
// step-by-step string building -- that is what makes a
// truncated paste fail loudly instead of quietly.
// ==========================================================
