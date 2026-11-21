// ==========================================================
// 30-bracket-at-fill.das   entry + 1.5 x ATR stop on the
//                          FILLED quantity, sized to 1R
// Montage button.  Block A = LONG.  Block B = SHORT.
// Bind each block to its own button.
// Forum topic: bracket-at-fill (docs/HOTKEY-FORUM.md)
// ==========================================================
//
// WHY. On 2026-11-17 one account was bracketed 22 s after
// its fill and the other held no stop through a 2R move and
// an earnings print. This button makes the bracket part of
// the entry, on every account, so SIM practice is the same
// motion as LIVE.
//
// WHAT ONE PRESS DOES
//   1. Refuses unless: R is known for the montage account,
//      ATR > 0 on a chart showing the same symbol, a quote
//      exists, the montage is flat, and size >= 1 share.
//   2. Sizes: the largest whole qty with
//        qty x (1.5 x ATR + entrySlip + limitSlip) <= 1R,
//      so a fill anywhere up to the entry limit and a stop
//      fill anywhere down to the stop limit still risk 1R.
//   3. Logs PENDING-STOP, then sends a marketable limit
//      (ASK + slip / BID - slip), DAY+, on the montage
//      account. From here on no MsgBox until the stop is out.
//   4. Polls the position for up to 5 s, putting the montage
//      back on the symbol first if the trader changed it.
//   5. Cancels every working order on that symbol and
//      account (only the entry can exist: step 1 required
//      flat), then re-reads the position.
//   6. Sends an SLP stop for exactly that position.
//   7. Re-reads the position 1.1 s later. A change means a
//      fill arrived after the read: logs NOSTOP MISMATCH and
//      raises a MsgBox when $bafPopup is 1.
//   No position after step 5: logs "unfilled", sends nothing.
//
// SETUP (once per montage that carries the buttons)
//   a. The montage is named in $bafMontage below.
//   b. A chart of the SAME symbol, on 5-minute bars with an
//      ATR(14) study, is named in $bafChart below. The ATR
//      basis is PREFERENCES MIN_STOP_ATR: 1.5 x ATR on the
//      session 5-minute bars.
//   c. R per account is NOT typed here. Run
//        python3 tools/baf_rconfig.py
//      which reads the PREFERENCES R-CONFIG table and writes
//      scripts/local/baf-rconfig.das (gitignored: it holds
//      account IDs). Paste it at the TOP of
//      Setup > Hotkey > Scripts > Desktop Load Script, ahead
//      of any return. Re-run it whenever R-CONFIG changes.
//   d. $bafPopup = 1 shows refusals in a MsgBox. Set it to 0
//      before injecting through the CMD API: a modal freezes
//      the API.
//
// ACCOUNT. The short-form order takes its account from the
// DEFAULT ORDER TEMPLATE, not from the montage (advanced
// hotkey guide p.25). Both orders here set .account from the
// montage before Send (p.28: Send after account is set).
//
// SIZE. Round() documents precision 1-6, 100 and 101 only
// (advanced hotkey guide, Round), so the whole-share count
// is found by counting up in 10s then 1s, under the
// 200-iteration while cap: at most 2,000 shares.
//
// UNVERIFIED (the operator SIM test settles these)
//   U1  $m.Account returns the montage account string.
//   U2  $m.POS is the montage account position (not the sum
//       of every account on that symbol).
//   U3  .account set on a short-form order object is honored.
//       TEST: press on a montage whose account is NOT the
//       order-template default, then check the order account.
//   U4  CancelOrder("BUY|SELL", sym) cancels a working SS
//       entry as well as a B entry.
//   U5  Setting $m.SYMBOL back mid-script is harmless.
//   U6  The stop is accepted. Nothing here reads order status:
//       watch the stop rest in the orders window.
// VERIFIED patterns reused: SLP stop form and POS gating
// (07, SIM 2026-09-08), GetStudyVal("atr") (06), short
// order lines (07 header), $m.SYMBOL re-pin and
// CancelOrder("BUY|SELL", sym) (22, ran on SIM 2026-09-25).
//
// RISK NOT REMOVED. SLP is a stop-LIMIT: a gap through the
// limit leaves the position open. It is used because it
// works outside core hours. A script error after step 3
// leaves PENDING-STOP as the last BAF line in the log: treat
// that as an unprotected position.
// ==========================================================


// ==========================================================
// BLOCK A - LONG
// ==========================================================

$bafMontage = "montage1";
$bafChart   = "chart5m";
$bafPopup   = 1;

$stopMult  = 1.5;
$entrySlip = 0.15;
$limitSlip = 0.20;

$m = GetWindowObj($bafMontage);
$c = GetWindowObj($bafChart);
if (isObject($m) == 0) {
  MsgLog("BAF refused: no montage ", $bafMontage);
  if ($bafPopup == 1) { MsgBox("BAF: no montage"); }
  return;
}
if (isObject($c) == 0) {
  MsgLog("BAF refused: no chart ", $bafChart);
  if ($bafPopup == 1) { MsgBox("BAF: no ATR chart"); }
  return;
}

$sym  = $m.GetTicker();
$acct = $m.Account;
$px   = $m.ASK;
$atr  = $c.GetStudyVal("atr");

if ($sym == "") {
  MsgLog("BAF refused: no symbol");
  if ($bafPopup == 1) { MsgBox("BAF: no symbol"); }
  return;
}
if ($c.GetTicker() != $sym) {
  MsgLog("BAF refused: chart is ", $c.GetTicker());
  if ($bafPopup == 1) { MsgBox("BAF: chart symbol differs"); }
  return;
}
if ($atr <= 0) {
  MsgLog("BAF refused: no ATR for ", $sym);
  if ($bafPopup == 1) { MsgBox("BAF: no ATR, no entry"); }
  return;
}
if ($px <= 0) {
  MsgLog("BAF refused: no ASK for ", $sym);
  if ($bafPopup == 1) { MsgBox("BAF: no ASK"); }
  return;
}
if ($m.POS != 0) {
  MsgLog("BAF refused: ", $sym, " already has POS ", $m.POS);
  if ($bafPopup == 1) { MsgBox("BAF: not flat"); }
  return;
}

// ---- R for this account (from baf-rconfig.das) ----------
$r = 0;
if ($acct == $BAF_ACCT1) { $r = $BAF_R1; }
if ($acct == $BAF_ACCT2) { $r = $BAF_R2; }
if ($acct == $BAF_ACCT3) { $r = $BAF_R3; }
if ($r <= 0) {
  MsgLog("BAF refused: no R for montage account");
  if ($bafPopup == 1) { MsgBox("BAF: no R for this account"); }
  return;
}

// ---- size ------------------------------------------------
$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) {
  MsgLog("BAF refused: stop too tight ", $stopDist);
  if ($bafPopup == 1) { MsgBox("BAF: stop too tight"); }
  return;
}
$riskPer = $stopDist + $entrySlip;
$riskPer = $riskPer + $limitSlip;
$qty = 0;
while ((($qty + 10) * $riskPer) <= $r) {
  $qty = $qty + 10;
}
while ((($qty + 1) * $riskPer) <= $r) {
  $qty = $qty + 1;
}
if ($qty < 1) {
  MsgLog("BAF refused: 1R buys 0 shares at stop ", $stopDist);
  if ($bafPopup == 1) { MsgBox("BAF: 1R is under one share"); }
  return;
}

$bp = GetAccountObj($acct).BP;
if ($qty * $px > $bp) {
  MsgLog("BAF refused: size over buying power");
  if ($bafPopup == 1) { MsgBox("BAF: over buying power"); }
  return;
}

// subtraction only: `+` threw ScriptError:100 in Round() (06)
$negSlip = 0 - $entrySlip;
$entry   = Round($px - $negSlip, 2);
$trigger = Round($px - $stopDist, 2);
$limit   = Round($trigger - $limitSlip, 2);

// ---- entry -----------------------------------------------
$oe = "B " + $qty;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
MsgLog("BAF PENDING-STOP ", $sym, " [", $oe, "]");

$o = NewOrderObj($oe);
$o.account = $acct;
$o.Send();

// ---- wait for the fill (no modal from here to the stop) --
$i = 0;
while ($i < 10) {
  Wait(500);
  if ($m.GetTicker() != $sym) {
    $m.SYMBOL = $sym;
    Wait(700);
  }
  if ($m.POS >= $qty) { $i = 10; }
  $i = $i + 1;
}

GetAccountObj($acct).CancelOrder("BUY|SELL", $sym);
Wait(1100);
if ($m.GetTicker() != $sym) {
  $m.SYMBOL = $sym;
  Wait(700);
}

$pos = $m.POS;
if ($pos < 1) {
  MsgLog("BAF unfilled ", $sym, ": entry cancelled");
  return;
}

// ---- stop on the filled quantity -------------------------
$os = "S " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";

$o = NewOrderObj($os);
$o.account = $acct;
$o.Send();
MsgLog("BAF STOP SENT [", $os, "]");

// ---- a fill after the read leaves shares without a stop --
Wait(1100);
if ($m.GetTicker() != $sym) {
  $m.SYMBOL = $sym;
  Wait(700);
}
if ($m.POS != $pos) {
  MsgLog("BAF NOSTOP MISMATCH ", $sym, " POS ", $m.POS);
  if ($bafPopup == 1) { MsgBox("BAF: CHECK STOP"); }
  return;
}
MsgLog("BAF DONE LONG ", $sym, " ", $pos, " of ", $qty);
return;


// ==========================================================
// BLOCK B - SHORT
// ==========================================================

$bafMontage = "montage1";
$bafChart   = "chart5m";
$bafPopup   = 1;

$stopMult  = 1.5;
$entrySlip = 0.15;
$limitSlip = 0.20;

$m = GetWindowObj($bafMontage);
$c = GetWindowObj($bafChart);
if (isObject($m) == 0) {
  MsgLog("BAF refused: no montage ", $bafMontage);
  if ($bafPopup == 1) { MsgBox("BAF: no montage"); }
  return;
}
if (isObject($c) == 0) {
  MsgLog("BAF refused: no chart ", $bafChart);
  if ($bafPopup == 1) { MsgBox("BAF: no ATR chart"); }
  return;
}

$sym  = $m.GetTicker();
$acct = $m.Account;
$px   = $m.BID;
$atr  = $c.GetStudyVal("atr");

if ($sym == "") {
  MsgLog("BAF refused: no symbol");
  if ($bafPopup == 1) { MsgBox("BAF: no symbol"); }
  return;
}
if ($c.GetTicker() != $sym) {
  MsgLog("BAF refused: chart is ", $c.GetTicker());
  if ($bafPopup == 1) { MsgBox("BAF: chart symbol differs"); }
  return;
}
if ($atr <= 0) {
  MsgLog("BAF refused: no ATR for ", $sym);
  if ($bafPopup == 1) { MsgBox("BAF: no ATR, no entry"); }
  return;
}
if ($px <= 0) {
  MsgLog("BAF refused: no BID for ", $sym);
  if ($bafPopup == 1) { MsgBox("BAF: no BID"); }
  return;
}
if ($m.POS != 0) {
  MsgLog("BAF refused: ", $sym, " already has POS ", $m.POS);
  if ($bafPopup == 1) { MsgBox("BAF: not flat"); }
  return;
}

$r = 0;
if ($acct == $BAF_ACCT1) { $r = $BAF_R1; }
if ($acct == $BAF_ACCT2) { $r = $BAF_R2; }
if ($acct == $BAF_ACCT3) { $r = $BAF_R3; }
if ($r <= 0) {
  MsgLog("BAF refused: no R for montage account");
  if ($bafPopup == 1) { MsgBox("BAF: no R for this account"); }
  return;
}

$stopDist = Round($stopMult * $atr, 2);
if ($stopDist < 0.02) {
  MsgLog("BAF refused: stop too tight ", $stopDist);
  if ($bafPopup == 1) { MsgBox("BAF: stop too tight"); }
  return;
}
$riskPer = $stopDist + $entrySlip;
$riskPer = $riskPer + $limitSlip;
$qty = 0;
while ((($qty + 10) * $riskPer) <= $r) {
  $qty = $qty + 10;
}
while ((($qty + 1) * $riskPer) <= $r) {
  $qty = $qty + 1;
}
if ($qty < 1) {
  MsgLog("BAF refused: 1R buys 0 shares at stop ", $stopDist);
  if ($bafPopup == 1) { MsgBox("BAF: 1R is under one share"); }
  return;
}

$bp = GetAccountObj($acct).BP;
if ($qty * $px > $bp) {
  MsgLog("BAF refused: size over buying power");
  if ($bafPopup == 1) { MsgBox("BAF: over buying power"); }
  return;
}

// short: entry below BID, trigger and limit above it
$negStop = 0 - $stopDist;
$negSlip = 0 - $limitSlip;
$entry   = Round($px - $entrySlip, 2);
$trigger = Round($px - $negStop, 2);
$limit   = Round($trigger - $negSlip, 2);

$oe = "SS " + $qty;
$oe = $oe + " " + $sym;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";
MsgLog("BAF PENDING-STOP ", $sym, " [", $oe, "]");

$o = NewOrderObj($oe);
$o.account = $acct;
$o.Send();

$i = 0;
while ($i < 10) {
  Wait(500);
  if ($m.GetTicker() != $sym) {
    $m.SYMBOL = $sym;
    Wait(700);
  }
  if ($m.POS >= $qty) { $i = 10; }
  $i = $i + 1;
}

GetAccountObj($acct).CancelOrder("BUY|SELL", $sym);
Wait(1100);
if ($m.GetTicker() != $sym) {
  $m.SYMBOL = $sym;
  Wait(700);
}

// .POS is unsigned on this build (22, 2026-09-25); the side
// is known here because this block only ever goes short.
$pos = $m.POS;
if ($pos < 1) {
  MsgLog("BAF unfilled ", $sym, ": entry cancelled");
  return;
}

$os = "B " + $pos;
$os = $os + " " + $sym;
$os = $os + " SLP " + $trigger;
$os = $os + " " + $limit;
$os = $os + " D+";

$o = NewOrderObj($os);
$o.account = $acct;
$o.Send();
MsgLog("BAF STOP SENT [", $os, "]");

Wait(1100);
if ($m.GetTicker() != $sym) {
  $m.SYMBOL = $sym;
  Wait(700);
}
if ($m.POS != $pos) {
  MsgLog("BAF NOSTOP MISMATCH ", $sym, " POS ", $m.POS);
  if ($bafPopup == 1) { MsgBox("BAF: CHECK STOP"); }
  return;
}
MsgLog("BAF DONE SHORT ", $sym, " ", $pos, " of ", $qty);
return;
