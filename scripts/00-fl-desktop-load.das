// ============================================================================
// 00-fl-desktop-load.das  —  Fashionably Late desktop bootstrap
// Paste into: Setup > Hotkey > Scripts > Desktop Load Script
// Runs once on DAS startup. No key binding.
// ============================================================================
//
// PREREQUISITE: Setup > Other Configuration > "Hotkey Advanced Script" must be
// ON. Without it every $variable below is a syntax error.
// ============================================================================
//
// WHAT LIVES HERE vs WHAT LIVES ON THE CHART
//
// Globals ($NAME) are shared by EVERY window. The hot buttons guide p.13 warns
// explicitly that two chart windows will overwrite each other's globals mid-
// script. So globals here hold OPERATOR SETTINGS only — things that are
// deliberately the same everywhere.
//
// Per-chart state (the gap, the coil flag, the cross side) lives on each chart
// window's own `data` object. See 02-fl-chart-update.das.
// ============================================================================

// ---- Tolerance: ATR-relative ----------------------------------------------
// The convergence band is half an ATR by default, computed per chart from an
// ATR study. This scales across the watchlist the way your stops already do —
// a $60 name and a $600 name get proportionate bands from one setting.
//
// Adjust live with F2/F3 (see 04-fl-hotkeys.das).
$FL_TOL_ATR = 0.5;

// Hard floor in dollars. Guards against an ATR study that has not warmed up
// yet returning something near zero, which would make every gap look converged.
$FL_TOL_MIN = 0.05;

// ---- FL trigger ------------------------------------------------------------
// Volume confirmation multiple. From fl_monitor_spec.md: vol > 1.5x 20-bar avg.
$FL_VOL_MULT = 1.5;

// Entry gate. FL takes nothing before 09:45 ET.
// GetSecond() returns seconds since midnight, platform-local.
// 09:45 local = 35100. Adjust if your DAS clock is not ET.
$FL_GATE_SEC = 35100;

// ---- Study names -----------------------------------------------------------
// These MUST match the Name field in Chart > Study Config exactly.
// GetStudyVal() resolves by this string; a typo returns 0 silently.
$FL_STUDY_EMA9  = "ema9";
$FL_STUDY_SMA34 = "sma34";
$FL_STUDY_ATR   = "atr";
$FL_STUDY_VWAP  = "vwap";     // still charted for context; no longer the trigger

// ---- Chart color settings files -------------------------------------------
// See 02-fl-chart-update.das. Save these two from the chart's right-click menu
// (Save Screen Setting) with your normal and your coil color schemes.
$FL_CST_OFF = "flCoilOff.cst";
$FL_CST_ON  = "flCoilOn.cst";

// Set to 1 only after you have verified .cst swapping actually changes what you
// want it to change on your build. Off by default. See 05-fl-cst-test.das.
$FL_USE_CST = 0;

// ---- Operator ---------------------------------------------------------------
$FL_ARMED = 1;    // 0 mutes all spoken alerts

MsgBox("FL desktop loaded." + "\n" +
       "tol = " + $FL_TOL_ATR + " x ATR" + "\n" +
       "cst swap = " + $FL_USE_CST + "\n" +
       "armed = " + $FL_ARMED);
