// ==========================================================
// 35-buy-ask-range.das   BUY at ASK+8c on REB25L, then a
// RANGE exit: market stop 50c under the fill, limit
// target 1.50 over it (3R)
// One hotkey. Montage window must be named  montage1
// Advanced scripting must be ON.
// ==========================================================
//
// Advanced rewrite of this classic hotkey:
//   ROUTE=REB25L;Price=Ask+0.08;TIF=DAY+;BUY=Send;
//   TriggerOrder=RT:STOP STOPTYPE:RANGE
//     STOPPRICE:AvgCost2-.50 PX:AvgCost2+1.50
//     ACT:SELL QTY:POS TIF:DAY+
// which itself replaced a STOPTYPE:LIMITP stop (-.50/-.59).
//
// Differences from the classic version:
// - Flat only. QTY:POS would size the exit to shares
//   already held, doubling up on their own stop.
// - TriggerOrder waits for a FULL fill. This waits ~5 s,
//   cancels any unfilled remainder, and arms the range
//   on whatever did fill.
// - Anchors on Price=AvgCost (hotkeys guide p.5).
//   AvgCost2 is not in the manuals in docs/text, so it is
//   not used here.
//
// RANGE ORDER SYNTAX IS UNVERIFIED -- read before use.
// Advanced hotkey guide p.28: RGM = range market order.
// Its examples put the LOW price first on a sell:
//   NewOrderObj("S 100 TSLA RGM 270.58 300.23 D+")
// but the text above them says the HIGHER price goes
// first on sells. This script follows the examples:
//   S <pos> <sym> RGM <stop> <target> D+
// If DAS reads it the other way, the target leg becomes
// a sell limit BELOW the market and fills at once, closing
// the position at a loss. The first run on TR4425 must
// confirm, in the order window, that the stop is 0.50
// under the fill and the target 1.50 over it.
//
// Market stop leg: expect it to be refused outside regular
// hours. Use a LIMITP stop (07) pre/post market.
//
// NOT YET VERIFIED ON SIM.
// ==========================================================

// ---- inputs ----------------------------------------------
$stopDist    = 0.50;
$targetDist  = 1.50;
$entrySlip   = 0.08;
$route       = "REB25L";

// ---- montage ---------------------------------------------
$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }

$sym = $m.GetTicker();
$px  = $m.ASK;
$qty = $m.Share;

if ($sym == "") { MsgBox("no symbol"); return; }
if ($px == 0)   { MsgBox("no ASK"); return; }
if ($qty < 1)   { MsgBox("qty is " + $qty); return; }

// Flat only: see header.
$pos0 = $m.POS;
if ($pos0 != 0) { MsgBox("not flat, POS=" + $pos0); return; }

// ---- prices: subtraction only ----------------------------
// `+` threw ScriptError:100 inside Round() (see 07).
$negSlip = 0 - $entrySlip;
$entry   = Round($px - $negSlip, 2);

// ---- entry -----------------------------------------------
$oe = "B " + $qty;
$oe = $oe + " " + $sym;
$oe = $oe + " " + $route;
$oe = $oe + " L " + $entry;
$oe = $oe + " D+";

MsgBox("ENTRY [" + $oe + "]");

NewOrderObj($oe).Send();

// ---- wait for a fill, up to ~5 s -------------------------
// Wait(1100) first keeps the next Send() over the one-per-
// second limit. No MsgBox from here until the exit is
// armed: a modal while shares are unprotected costs money.
Wait(1100);
$pos = $m.POS;
$i = 0;
while ($i < 8) {
  if ($pos < $qty) {
    Wait(500);
    $pos = $m.POS;
  }
  $i = $i + 1;
}

// ---- cancel whatever did not fill ------------------------
// Same as 32: CXL CLOSEST LONG (hotkeys guide p.13); the
// flat-only guard means no other buy on this symbol.
if ($pos < $qty) {
  FocusWindow montage1;
  CXL CLOSEST LONG;
  Wait(500);
  $pos = $m.POS;
}
if ($pos < 1) {
  MsgLog("RANGE NOSTOP ", $sym, " unfilled, cancelled");
  return;
}

// ---- anchor: exit from the FILL, not the ASK -------------
// Same mechanism as 07. A buy cannot fill above its limit,
// so <= 0 or above $entry is not a fill: fall back to ASK.
FocusWindow montage1;
Price=AvgCost;
$fill = $m.Price;

$anchor = $fill;
$fb = 0;
if ($fill <= 0)     { $fb = 1; }
if ($fill > $entry) { $fb = 1; }
if ($fb == 1) {
  $anchor = $px;
  MsgLog("RANGE ", $sym, " FALLBACK ASK, fill=", $fill);
}

$stop    = Round($anchor - $stopDist, 2);
$negTgt  = 0 - $targetDist;
$target  = Round($anchor - $negTgt, 2);

// ---- range exit ------------------------------------------
// Order of the two prices: see header.
$os = "S " + $pos;
$os = $os + " " + $sym;
$os = $os + " RGM " + $stop;
$os = $os + " " + $target;
$os = $os + " D+";

MsgLog("RANGE ", $sym, " EXIT [", $os, "]");
NewOrderObj($os).Send();
MsgLog("RANGE ", $sym, " ", $pos, " fill ", $fill);
MsgLog("RANGE ", $sym, " stop ", $stop, " tgt ", $target);


// ==========================================================
// Once you trust it, delete the ENTRY MsgBox. Keep the
// step-by-step string building -- that is what makes a
// truncated paste fail loudly instead of quietly.
// ==========================================================
