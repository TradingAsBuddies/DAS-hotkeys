// ============================================================================
// 05-fl-cst-test.das  —  does .cst swapping actually repaint your price bars?
// Run this ONCE, by hand, before setting $FL_USE_CST = 1.
// ============================================================================
//
// THE QUESTION
//
// `LoadSetting <file>.cst` is a documented, scriptable chart command. What the
// manuals do NOT say is how much a .cst captures:
//
//   das-trader-pro-user-manual.pdf p.918, under the chart right-click menu:
//     "Set Screen Colors - Allows adjustment of background, grid, and label
//      colors. Load Screen Setting - Load a previously saved .cst file.
//      Save Screen Setting - Save a chart configuration as a .cst file."
//
// "Set Screen Colors" lists three things, none of them study colors. But
// "Save a chart configuration" is a much broader phrase. The manual is
// genuinely ambiguous and I am not going to guess which reading is right.
//
// Three possible outcomes. Find out which one you get:
//
//   A. .cst carries STUDY colors    -> real bar recoloring. Best case.
//   B. .cst carries SCREEN colors only -> background/grid flip. Still a strong
//      visual signal, arguably better than recolored bars for peripheral vision.
//   C. .cst does not reload live, or resets the chart -> abandon this path,
//      keep the hot button.
//
// ============================================================================
//
// PROCEDURE
//
// 1. Open flChart1m with your normal setup: ema9, sma34, atr, vwap studies.
//
// 2. Right-click chart > Save Screen Setting.
//    Save as:  flCoilOff.cst
//    Note where DAS puts it. You need the same folder for both files.
//
// 3. Change the colors you care about. Do BOTH so you can tell A from B:
//       - Chart > Study Config > select your price/candle study > change color
//       - Right-click > Set Screen Colors > change the background
//
// 4. Right-click chart > Save Screen Setting.
//    Save as:  flCoilOn.cst
//
// 5. Restore the chart to its normal look (or just load flCoilOff.cst by hand).
//
// 6. Bind the two blocks below to two hotkeys. Press them alternately while
//    watching the chart. Write down what changes:
//
//       background changed?   Y / N
//       grid or labels?       Y / N
//       PRICE BAR COLOR?      Y / N   <- this is the one that matters
//       studies reset/vanish? Y / N
//       chart reloaded data?  Y / N   <- if yes, this path is too disruptive
//
// 7. If PRICE BAR COLOR = Y, set $FL_USE_CST = 1 in 00-fl-desktop-load.das.
//    If only background changed, decide whether that reads well enough for you
//    at a glance. It may well be better than bar color.
//    If the chart reloads data or drops studies, leave $FL_USE_CST = 0.
//
// A NOTE ON PATHS
// The manual's example is a bare filename: LoadSetting ChartSetting.cst
// It does not document whether that resolves relative to the DAS install dir,
// the user config dir, or the working directory. If a bare name does nothing,
// try the full path DAS showed you in step 2.
// ============================================================================


// ---- HOTKEY A : load the "coil on" scheme ----------------------------------
LoadSetting flCoilOn.cst;
MsgBox("loaded flCoilOn.cst");


// ---- HOTKEY B : load the "coil off" scheme ---------------------------------
LoadSetting flCoilOff.cst;
MsgBox("loaded flCoilOff.cst");


// ---- HOTKEY C : fallback, whole-platform theme swap ------------------------
// Documented at advanced hotkey guide p.8: "SwitchTheme  Swap DAS theme
// i.e. SwitchTheme DAS_DARK". Platform-wide, not per-chart, so it is a poor
// fit for a per-symbol signal. Included only so you can see what it does.
//
// SwitchTheme DAS_DARK;
// SwitchTheme DAS_Default;
