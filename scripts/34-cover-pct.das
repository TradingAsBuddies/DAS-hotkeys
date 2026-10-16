// ==========================================================
// 34-cover-pct.das   cover 100% / 50% / 25% at ASK or BID
// The green % buttons: buy back part of a SHORT.
// Row 2 (aggressive) pays the ASK, row 3 (passive) the BID.
// Percentages are of the position, so they are unchanged.
//
// CAUTION: a partial cover leaves the existing buy stop at
// the FULL original size. If it triggers it buys more than
// you are short and leaves you long. Resize the stop after
// a partial cover.
//
// The grey 10% ASK / 10% BID buttons are not here: their
// side could not be read from the colours.
//
// Montage buttons: right-click the montage button bar >
// Edit (hot buttons guide p.3-4), paste ONE block per
// button. Advanced scripting must be ON.
//
// Recreated from the button LABELS on the GENK montage
// (screenshot, 2026-10-16) at one tenth the size. The
// original button scripts were not visible; behaviour
// below is inferred from the labels, not copied.
//
// These run on whatever account the montage is set to. The
// screenshot montage was on a LIVE account, not the TR4425
// paper account. Test every block on TR4425 first.
//
// NOT YET VERIFIED ON SIM.
// ==========================================================

// ==========================================================
// 100% ASK  (cover)
// ==========================================================

$pct = 1;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }

// Cover only. A long or flat montage refuses, so this can
// never add to a long. If DAS reports shorts as POSITIVE
// (unobserved, see 08), every press refuses: safe, and the
// message says why.
$pos = $m.POS;
if ($pos >= 0) { MsgBox("not short, POS=" + $pos); return; }
$sz = 0 - $pos;

$raw = $sz * $pct;
if ($raw > 20000) { MsgBox("size over 20000"); return; }

// ---- whole shares: DAS has no floor() ------------------
// Round(x, 100) rounds down to round lots (adv guide p.7),
// too coarse at this size. Count up in 100s, 10s, 1s; each
// loop stays far under the 200-iteration cap.
$q = 0;
$n = $q + 100;
while ($n <= $raw) { $q = $n; $n = $q + 100; }
$n = $q + 10;
while ($n <= $raw) { $q = $n; $n = $q + 10; }
$n = $q + 1;
while ($n <= $raw) { $q = $n; $n = $q + 1; }
if ($q < 1) { $q = 1; }

$px = $m.ASK;
if ($px == 0) { MsgBox("no ASK"); return; }

$oc = "B " + $q;
$oc = $oc + " " + $sym;
$oc = $oc + " L " + $px;
$oc = $oc + " D+";
MsgLog("COVER 100% ASK [", $oc, "] of ", $sz);
NewOrderObj($oc).Send();


// ==========================================================
// 50% ASK  (cover)
// ==========================================================

$pct = 0.5;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }

// Cover only. A long or flat montage refuses, so this can
// never add to a long. If DAS reports shorts as POSITIVE
// (unobserved, see 08), every press refuses: safe, and the
// message says why.
$pos = $m.POS;
if ($pos >= 0) { MsgBox("not short, POS=" + $pos); return; }
$sz = 0 - $pos;

$raw = $sz * $pct;
if ($raw > 20000) { MsgBox("size over 20000"); return; }

// ---- whole shares: DAS has no floor() ------------------
// Round(x, 100) rounds down to round lots (adv guide p.7),
// too coarse at this size. Count up in 100s, 10s, 1s; each
// loop stays far under the 200-iteration cap.
$q = 0;
$n = $q + 100;
while ($n <= $raw) { $q = $n; $n = $q + 100; }
$n = $q + 10;
while ($n <= $raw) { $q = $n; $n = $q + 10; }
$n = $q + 1;
while ($n <= $raw) { $q = $n; $n = $q + 1; }
if ($q < 1) { $q = 1; }

$px = $m.ASK;
if ($px == 0) { MsgBox("no ASK"); return; }

$oc = "B " + $q;
$oc = $oc + " " + $sym;
$oc = $oc + " L " + $px;
$oc = $oc + " D+";
MsgLog("COVER 50% ASK [", $oc, "] of ", $sz);
NewOrderObj($oc).Send();


// ==========================================================
// 25% ASK  (cover)
// ==========================================================

$pct = 0.25;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }

// Cover only. A long or flat montage refuses, so this can
// never add to a long. If DAS reports shorts as POSITIVE
// (unobserved, see 08), every press refuses: safe, and the
// message says why.
$pos = $m.POS;
if ($pos >= 0) { MsgBox("not short, POS=" + $pos); return; }
$sz = 0 - $pos;

$raw = $sz * $pct;
if ($raw > 20000) { MsgBox("size over 20000"); return; }

// ---- whole shares: DAS has no floor() ------------------
// Round(x, 100) rounds down to round lots (adv guide p.7),
// too coarse at this size. Count up in 100s, 10s, 1s; each
// loop stays far under the 200-iteration cap.
$q = 0;
$n = $q + 100;
while ($n <= $raw) { $q = $n; $n = $q + 100; }
$n = $q + 10;
while ($n <= $raw) { $q = $n; $n = $q + 10; }
$n = $q + 1;
while ($n <= $raw) { $q = $n; $n = $q + 1; }
if ($q < 1) { $q = 1; }

$px = $m.ASK;
if ($px == 0) { MsgBox("no ASK"); return; }

$oc = "B " + $q;
$oc = $oc + " " + $sym;
$oc = $oc + " L " + $px;
$oc = $oc + " D+";
MsgLog("COVER 25% ASK [", $oc, "] of ", $sz);
NewOrderObj($oc).Send();


// ==========================================================
// 100% BID  (cover)
// ==========================================================

$pct = 1;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }

// Cover only. A long or flat montage refuses, so this can
// never add to a long. If DAS reports shorts as POSITIVE
// (unobserved, see 08), every press refuses: safe, and the
// message says why.
$pos = $m.POS;
if ($pos >= 0) { MsgBox("not short, POS=" + $pos); return; }
$sz = 0 - $pos;

$raw = $sz * $pct;
if ($raw > 20000) { MsgBox("size over 20000"); return; }

// ---- whole shares: DAS has no floor() ------------------
// Round(x, 100) rounds down to round lots (adv guide p.7),
// too coarse at this size. Count up in 100s, 10s, 1s; each
// loop stays far under the 200-iteration cap.
$q = 0;
$n = $q + 100;
while ($n <= $raw) { $q = $n; $n = $q + 100; }
$n = $q + 10;
while ($n <= $raw) { $q = $n; $n = $q + 10; }
$n = $q + 1;
while ($n <= $raw) { $q = $n; $n = $q + 1; }
if ($q < 1) { $q = 1; }

$px = $m.BID;
if ($px == 0) { MsgBox("no BID"); return; }

$oc = "B " + $q;
$oc = $oc + " " + $sym;
$oc = $oc + " L " + $px;
$oc = $oc + " D+";
MsgLog("COVER 100% BID [", $oc, "] of ", $sz);
NewOrderObj($oc).Send();


// ==========================================================
// 50% BID  (cover)
// ==========================================================

$pct = 0.5;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }

// Cover only. A long or flat montage refuses, so this can
// never add to a long. If DAS reports shorts as POSITIVE
// (unobserved, see 08), every press refuses: safe, and the
// message says why.
$pos = $m.POS;
if ($pos >= 0) { MsgBox("not short, POS=" + $pos); return; }
$sz = 0 - $pos;

$raw = $sz * $pct;
if ($raw > 20000) { MsgBox("size over 20000"); return; }

// ---- whole shares: DAS has no floor() ------------------
// Round(x, 100) rounds down to round lots (adv guide p.7),
// too coarse at this size. Count up in 100s, 10s, 1s; each
// loop stays far under the 200-iteration cap.
$q = 0;
$n = $q + 100;
while ($n <= $raw) { $q = $n; $n = $q + 100; }
$n = $q + 10;
while ($n <= $raw) { $q = $n; $n = $q + 10; }
$n = $q + 1;
while ($n <= $raw) { $q = $n; $n = $q + 1; }
if ($q < 1) { $q = 1; }

$px = $m.BID;
if ($px == 0) { MsgBox("no BID"); return; }

$oc = "B " + $q;
$oc = $oc + " " + $sym;
$oc = $oc + " L " + $px;
$oc = $oc + " D+";
MsgLog("COVER 50% BID [", $oc, "] of ", $sz);
NewOrderObj($oc).Send();


// ==========================================================
// 25% BID  (cover)
// ==========================================================

$pct = 0.25;

$m = GetWindowObj("montage1");
if (isObject($m) == 0) { MsgBox("no montage1"); return; }
$sym = $m.GetTicker();
if ($sym == "") { MsgBox("no symbol"); return; }

// Cover only. A long or flat montage refuses, so this can
// never add to a long. If DAS reports shorts as POSITIVE
// (unobserved, see 08), every press refuses: safe, and the
// message says why.
$pos = $m.POS;
if ($pos >= 0) { MsgBox("not short, POS=" + $pos); return; }
$sz = 0 - $pos;

$raw = $sz * $pct;
if ($raw > 20000) { MsgBox("size over 20000"); return; }

// ---- whole shares: DAS has no floor() ------------------
// Round(x, 100) rounds down to round lots (adv guide p.7),
// too coarse at this size. Count up in 100s, 10s, 1s; each
// loop stays far under the 200-iteration cap.
$q = 0;
$n = $q + 100;
while ($n <= $raw) { $q = $n; $n = $q + 100; }
$n = $q + 10;
while ($n <= $raw) { $q = $n; $n = $q + 10; }
$n = $q + 1;
while ($n <= $raw) { $q = $n; $n = $q + 1; }
if ($q < 1) { $q = 1; }

$px = $m.BID;
if ($px == 0) { MsgBox("no BID"); return; }

$oc = "B " + $q;
$oc = $oc + " " + $sym;
$oc = $oc + " L " + $px;
$oc = $oc + " D+";
MsgLog("COVER 25% BID [", $oc, "] of ", $sz);
NewOrderObj($oc).Send();

