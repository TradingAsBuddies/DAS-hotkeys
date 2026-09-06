// ============================================================================
// 04-fl-hotkeys.das  —  operator controls for the FL desktop
// Each block is a SEPARATE hotkey. Setup > Hotkey > Add New Item, paste one
// block per entry, bind the key shown.
// ============================================================================

// ---- F2 : widen the coil band (ATR multiple +0.1) --------------------------
$FL_TOL_ATR = $FL_TOL_ATR + 0.1;
MsgBox("FL band = " + $FL_TOL_ATR + " x ATR");


// ---- F3 : tighten the coil band (ATR multiple -0.1) ------------------------
// Floor at 0.1 so the band never collapses to zero.
$FL_TOL_ATR = $FL_TOL_ATR - 0.1;
if ($FL_TOL_ATR < 0.1) { $FL_TOL_ATR = 0.1; }
MsgBox("FL band = " + $FL_TOL_ATR + " x ATR");


// ---- F4 : mute / unmute spoken alerts --------------------------------------
if ($FL_ARMED == 1) {
  $FL_ARMED = 0;
  MsgBox("FL alerts MUTED");
} else {
  $FL_ARMED = 1;
  MsgBox("FL alerts ARMED");
}


// ---- F5 : enable / disable the .cst color swap -----------------------------
// Leave OFF until 05-fl-cst-test.das has told you what .cst actually changes.
if ($FL_USE_CST == 1) {
  $FL_USE_CST = 0;
  MsgBox("chart color swap OFF");
} else {
  $FL_USE_CST = 1;
  MsgBox("chart color swap ON");
}


// ---- F6 : mark the coil band on the chart ----------------------------------
// Draws both MAs as horizontal lines so the band is visible after the fact.
//
// WARNING: RemoveAllTrendLines clears EVERY trendline on this symbol, global
// ones included. Deliberately commented out.
//
// BETTER APPROACH, from https://youtu.be/j8Z36LVZ40s — give each drawn line a
// NAME, then delete only that name before redrawing it. Self-cleaning, and it
// never touches your hand-drawn levels:
//
//     if (chart has trendline "FL_EMA9") { delete that trendline }
//     draw horizontal line at price, name it "FL_EMA9"
//
// The manuals confirm named trendlines exist — HideTrendlines "Toggle show/hide
// trend lines by name. Each trend line's name can be specified by user"
// (das-hotkeys-guide.pdf p.17) — but do NOT give the create/delete-by-name
// signature. The video demonstrates it working, so it exists on current builds.
// Pull the exact calls off the video and swap them in here; that is strictly
// better than what is below.
//
// RemoveAllTrendLines;
ConfigTrendLine HorzLine DotLine:FFB000:2;
DrawHorzLineWithPrice(GetStudyVal($FL_STUDY_EMA9), Color(255, 176, 0));
DrawHorzLineWithPrice(GetStudyVal($FL_STUDY_SMA34), Color(120, 120, 255));


// ---- F7 : snapshot this chart's FL state -----------------------------------
// Reads the chart-local data object, so it reports THIS window's state, not
// whichever chart happened to write a global last.
MsgBox("ema9  = " + Round(data.e9, 3) + "\n" +
       "sma34 = " + Round(data.s34, 3) + "\n" +
       "atr   = " + Round(data.atr, 3) + "\n" +
       "gap   = " + Round(data.gap, 3) + "\n" +
       "band  = " + Round(data.tol, 3) + "  (" + $FL_TOL_ATR + " x ATR)" + "\n" +
       "coil  = " + data.coil + "\n" +
       "side  = " + data.side);


// ---- F8 : discovery — dump bar object properties ---------------------------
// Run ONCE on flChart1m before trusting the volume gate in 03. Confirms
// whether a bar exposes "Volume" on your build.
$fl_b = GetBar(-1);
$fl_b.ShowObject();


// ---- F9 : discovery — dump this chart window's data object -----------------
// Shows every per-chart value 02 and 03 have stored.
data.ShowObject();


// ---- F10 : discovery — dump the chart window object ------------------------
$fl_c = GetWindowObj("flChart1m");
$fl_c.ShowObject();
