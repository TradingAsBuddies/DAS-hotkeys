// ============================================================================
// 02-fl-chart-update.das  —  9-EMA / 34-SMA coil detector + color switching
// Paste into: flChart1m > right-click > Chart Script
// Runs automatically about once per second while the chart updates.
// ============================================================================
//
// ─────────────────────────────────────────────────────────────────────────────
// COLOR: THREE MECHANISMS, RANKED
//
// You asked me to dig into the advanced hotkey material for ways to change
// color. I found two beyond the hot button. Ranked by how much they change and
// how confident I am they work:
//
//  1. HOT BUTTON — getCustButObj(n).BkColor / .FgColor
//     Fully documented with a working example (hot buttons guide p.9).
//     Changes a button, not the bars. Always on below.
//
//  2. CHART SETTINGS SWAP — LoadSetting <file>.cst          <- THE REAL ANSWER
//     `LoadSetting` is a scriptable chart hotkey command:
//        "LoadSetting  Load .cst file. For example, LoadSetting ChartSetting.cst"
//        — das-hotkeys-guide.pdf p.16
//     And .cst files are produced by the chart's own right-click menu:
//        "Save Screen Setting - Save a chart configuration as a .cst file"
//        — das-trader-pro-user-manual.pdf p.918
//     So: save two chart configurations with different color schemes, then
//     swap between them from script. This DOES repaint the chart.
//
//     UNCONFIRMED: whether .cst captures STUDY colors (your price bars) or only
//     screen colors (background, grid, labels). The manual sentence sits under
//     "Set Screen Colors" but says "chart configuration", which is broader.
//     Run 05-fl-cst-test.das to settle it on your build. Gated behind
//     $FL_USE_CST, which ships as 0.
//
//  3. SwitchTheme DAS_DARK / DAS_Default
//     Scriptable (advanced hotkey guide p.8) but platform-wide. Too blunt for
//     a per-chart signal. Not used here; noted so you know it exists.
//
//  Still true: there is NO command that sets a study's color directly.
// ─────────────────────────────────────────────────────────────────────────────
//
// ─────────────────────────────────────────────────────────────────────────────
// WHY THIS USES `data` AND NOT GLOBALS
//
// This is a correction to what I gave you first. The hot buttons guide p.13:
//
//   "there is a possibility that TSLA window updates the global variable $vwap.
//    Before it can set $vwapDisplay with $vwap, MSFT window updates $vwap with
//    MSFT's vwap value... DAS recommends using the Data property"
//
// My first version kept $FL_COIL / $FL_GAP as globals. With flChart1m and
// flChart5m both running — let alone several symbols — they would overwrite
// each other and you would get the 5-minute chart's coil state on the 1-minute
// button. Per-chart state now lives on this window's own `data` object.
// ─────────────────────────────────────────────────────────────────────────────
//
// SETUP REQUIRED
//
// 1. Chart > Study Config. Add and NAME exactly:
//       ema9    Moving Average, EMA, period 9
//       sma34   Moving Average, SMA, period 34
//       atr     ATR (period 14)
//       vwap    VWAP
//
// 2. Text-type hot button named exactly  FLCOIL
//
// 3. 00-fl-desktop-load.das must have run.
// ============================================================================

// Per-chart storage. Created once, then reused every update.
if (isObject(data) == 0) { data = NewUserObj(); }

// ---- Ticker-change reset ----------------------------------------------------
// ADDED 2026-09-05 after the technique in https://youtu.be/j8Z36LVZ40s
//
// This was a real defect in my first version. Swap the chart from XLE to SNOW
// and every piece of carried state — coil flag, cross side, prev values — was
// still XLE's. You would have gotten a phantom cross on the first update after
// a ticker switch, because prev came from one symbol and current from another.
//
// The `settle` counter is the video's fix for a second problem: the studies do
// not repopulate the instant the symbol changes. Reading GetStudyVal() too
// early returns the old symbol's values or zeros. Wait a few updates.
if (isObject(data.sym) == 0) { data.sym = ""; }

if (data.sym == GetTicker()) {
  data.settle = data.settle + 1;
} else {
  data.sym    = GetTicker();
  data.settle = 0;
  data.coil   = 0;
  data.coilPrev = 0;
  data.side   = 0;
  data.sidePrev = 0;
  data.gap    = 0;
  MsgLog("FL reset for ", data.sym);
}

// Give the studies time to repopulate after a symbol change.
if (data.settle < 3) {
  GetCustButObj("FLCOIL").BkColor = Color(60, 60, 60);
  GetCustButObj("FLCOIL").FgColor = Color(160, 160, 160);
  GetCustButObj("FLCOIL").Text    = "settling...";
  return;
}

data.e9  = GetStudyVal($FL_STUDY_EMA9);
data.s34 = GetStudyVal($FL_STUDY_SMA34);
data.atr = GetStudyVal($FL_STUDY_ATR);

// ---- Guards ----------------------------------------------------------------
// A misnamed or unwarmed study returns 0. A zero on either MA leg would make
// the gap read as a perfect convergence, pinning the button on all session.
if (data.e9 == 0) {
  GetCustButObj("FLCOIL").BkColor = Color(60, 60, 60);
  GetCustButObj("FLCOIL").FgColor = Color(160, 160, 160);
  GetCustButObj("FLCOIL").Text    = "MA: no data";
  return;
}
if (data.s34 == 0) {
  GetCustButObj("FLCOIL").BkColor = Color(60, 60, 60);
  GetCustButObj("FLCOIL").FgColor = Color(160, 160, 160);
  GetCustButObj("FLCOIL").Text    = "MA: no data";
  return;
}

// ---- ATR-relative tolerance -------------------------------------------------
data.tol = data.atr * $FL_TOL_ATR;
if (data.tol < $FL_TOL_MIN) { data.tol = $FL_TOL_MIN; }

data.gap = Abs(data.e9 - data.s34);

// ---- State ------------------------------------------------------------------
data.coilPrev = data.coil;

if (data.gap <= data.tol) {
  data.coil = 1;
} else {
  data.coil = 0;
}

// ---- 1. Hot button ----------------------------------------------------------
if (data.coil == 1) {
  GetCustButObj("FLCOIL").BkColor = Color(255, 176, 0);
  GetCustButObj("FLCOIL").FgColor = Color(20, 20, 20);
  GetCustButObj("FLCOIL").Text    = "COIL  " + Round(data.gap, 2) +
                                    " / " + Round(data.tol, 2);
} else {
  GetCustButObj("FLCOIL").BkColor = Color(40, 40, 40);
  GetCustButObj("FLCOIL").FgColor = Color(180, 180, 180);
  GetCustButObj("FLCOIL").Text    = "gap   " + Round(data.gap, 2) +
                                    " / " + Round(data.tol, 2);
}

// ---- 2. Chart color swap, on transition only --------------------------------
// Only fires on an edge. Reloading a .cst every second would fight the chart's
// own redraw and is not something to do 23,400 times a session.
if ($FL_USE_CST == 1) {
  if (data.coil == 1) {
    if (data.coilPrev == 0) { LoadSetting $FL_CST_ON; }
  }
  if (data.coil == 0) {
    if (data.coilPrev == 1) { LoadSetting $FL_CST_OFF; }
  }
}

// ---- Optional: daily 200-EMA proximity filter --------------------------------
// From the same video. GetStudyVal() can be called on ANOTHER chart window's
// object, so the 1-minute chart can read the daily chart's studies:
//
//   $d = GetWindowObj("flChartD");
//   data.d200 = $d.GetStudyVal("dailyEMA200");
//
// The trade case: you enter long, it runs, then dies into the daily 200-EMA
// sitting just overhead. Knowing that level is nearby is worth more than the
// coil signal on its own.
//
// Requires a daily chart named flChartD with a study named dailyEMA200.
// Commented out until you add that window — GetWindowObj on a missing name
// will error every update.
//
// $flD = GetWindowObj("flChartD");
// if (isObject($flD) == 1) {
//   data.d200 = $flD.GetStudyVal("dailyEMA200");
//   data.d200dist = Abs(GetChartLv1("Last") - data.d200);
//   if (data.d200dist < data.atr) {
//     GetCustButObj("FLCOIL").Text = "COIL  near D200";
//   }
// }

// ---- 3. Audible, on transition into coil only -------------------------------
if (data.coil == 1) {
  if (data.coilPrev == 0) {
    if ($FL_ARMED == 1) { Speak("Coil"); }
  }
}
