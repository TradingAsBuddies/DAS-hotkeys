// ==========================================================
// 36-short-bid-range.das   SHORT at BID-8c on REB25L, then
// a RANGE cover: market stop 50c over the fill, limit
// target 1.50 under it (3R)
// One hotkey. Montage window must be named  montage1
// Advanced scripting must be ON.
// Short-side mirror of 35. Prices flip sides; the order of
// the two range prices (stop first) does not.
// ==========================================================
//
// Classic equivalent:
//   ROUTE=REB25L;Price=Bid-0.08;TIF=DAY+;SHORT=Send;
//   TriggerOrder=RT:STOP STOPTYPE:RANGE
//     STOPPRICE:AvgCost2+.50 PX:AvgCost2-1.50
//     ACT:BUY QTY:POS TIF:DAY+
//
// As in 35: flat only, unfilled remainder cancelled after
// ~5 s, exit anchored on Price=AvgCost (not AvgCost2).
//
// RANGE ORDER SYNTAX IS UNVERIFIED -- read before use.
// Advanced hotkey guide p.28 buy example puts the HIGH
// price first:
//   NewOrderObj("B 100 TSLA RGM 300.23 270.58 D+")
// but the text above it says the LOWER price goes first on
// buys. This script follows the example, which for a
// short cover puts the stop first:
//   B <size> <sym> RGM <stop> <target> D+
// If DAS reads it the other way, the target leg becomes a
// buy limit ABOVE the market and fills at once, covering
// at a loss. The first run on TR4425 must confirm, in the
// order window, that the stop is 0.50 over the fill and
// the target 1.50 under it.
//
// POS sign for a short is still unobserved (see 08); every
// size check uses Abs().
//
// Market stop leg: expect it to be refused outside regular
// hours. Use a LIMITP stop (08) pre/post market.
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
$px  = $m.BID;
$qty = $m.Share;

if ($sym == "") { MsgBox("no symbol"); return; }
if ($px == 0)   { MsgBox("no BID"); return; }
if ($qty < 1)   { MsgBox("qty is " + $qty); return; }

// Flat only: see 35.
$pos0 = $m.POS;
if ($pos0 != 0) { MsgBox("not flat, POS=" + $pos0); return; }

// ---- prices: subtraction only ----------------------------
// `+` threw ScriptError:100 inside Round() (see 07).
$entry   = Round($px - $entrySlip, 2);

// ---- entry -----------------------------------------------
$oe = "SS " + $qty;
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
$sz = Abs($m.POS);
$i = 0;
while ($i < 8) {
  if ($sz < $qty) {
    Wait(500);
    $sz = Abs($m.POS);
  }
  $i = $i + 1;
}

// ---- cancel whatever did not fill ------------------------
// CXL CLOSEST SHORT (hotkeys guide p.13); the flat-only
// guard means no other short on this symbol.
if ($sz < $qty) {
  FocusWindow montage1;
  CXL CLOSEST SHORT;
  Wait(500);
  $sz = Abs($m.POS);
}
if ($sz < 1) {
  MsgLog("SRANGE NOSTOP ", $sym, " unfilled, cancelled");
  return;
}

// ---- anchor: exit from the FILL, not the BID -------------
// Same mechanism as 08. A short cannot fill below its
// limit, so <= 0 or below $entry is not a fill: fall back
// to the BID.
FocusWindow montage1;
Price=AvgCost;
$fill = $m.Price;

$anchor = $fill;
$fb = 0;
if ($fill <= 0)     { $fb = 1; }
if ($fill < $entry) { $fb = 1; }
if ($fb == 1) {
  $anchor = $px;
  MsgLog("SRANGE ", $sym, " FALLBACK BID, fill=", $fill);
}

$negStop = 0 - $stopDist;
$stop    = Round($anchor - $negStop, 2);
$target  = Round($anchor - $targetDist, 2);

// ---- range cover -----------------------------------------
// Order of the two prices: see header.
$os = "B " + $sz;
$os = $os + " " + $sym;
$os = $os + " RGM " + $stop;
$os = $os + " " + $target;
$os = $os + " D+";

MsgLog("SRANGE ", $sym, " EXIT [", $os, "]");
NewOrderObj($os).Send();
MsgLog("SRANGE ", $sym, " ", $sz, " fill ", $fill);
MsgLog("SRANGE ", $sym, " stop ", $stop, " tgt ", $target);


// ==========================================================
// Once you trust it, delete the ENTRY MsgBox. Keep the
// step-by-step string building -- that is what makes a
// truncated paste fail loudly instead of quietly.
// ==========================================================
