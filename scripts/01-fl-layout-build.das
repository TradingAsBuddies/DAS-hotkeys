// ============================================================================
// 01-fl-layout-build.das  —  build and position the Fashionably Late desktop
// Bind to a hotkey you will press ONCE, then File > Save Desktop.
// ============================================================================
//
// HARD CONSTRAINT, stated ~24 times in das-hotkeys-guide.pdf:
//   "WPos and WSize can only be used with windows that pop out."
// SetPopOut Y must come BEFORE any WPos/WSize or the window will not move.
//
// Coordinates below assume a 2560x1440 primary monitor with a second monitor
// to the right starting at x=2560. Change the numbers, not the structure.
//
// After running this, right-click each window's title bar and name it exactly
// as listed in the NAME comment. Then File > Save Desktop, or every name is
// lost on restart and the Desktop Load Script breaks.
// ============================================================================

// ---- Row 1: execution ------------------------------------------------------

// NAME: flMontage    — order entry, Level 2, the window hotkeys act on
NewWindow Montage;
SetPopOut Y;
WPos 0 0;
WSize 520 900;

// NAME: flTimeSales  — tape, sits directly right of the montage
NewWindow TimeSale;
SetPopOut Y;
WPos 528 0;
WSize 300 900;

// ---- Row 1 continued: the signal chart -------------------------------------

// NAME: flChart1m    — PRIMARY. 1-minute. Carries ema9 / sma34 / vwap studies.
// This is the window 02-fl-chart-update.das attaches to.
NewWindow Chart;
SetPopOut Y;
WPos 836 0;
WSize 1100 900;

// ---- Row 1 far right: context ----------------------------------------------

// NAME: flChart5m    — 5-minute context. Same studies, no update script.
NewWindow Chart;
SetPopOut Y;
WPos 1944 0;
WSize 616 900;

// ---- Row 2: watchlist and account ------------------------------------------

// NAME: flWatch      — Market Viewer. The FL candidate list.
NewWindow MarketView;
SetPopOut Y;
WPos 0 908;
WSize 1100 500;

// NAME: flPositions  — open positions
NewWindow Position;
SetPopOut Y;
WPos 1108 908;
WSize 700 500;

// NAME: flAlerts     — alert window; FL cross alerts land here
NewWindow Alert;
SetPopOut Y;
WPos 1816 908;
WSize 744 500;

// ---- Chrome ----------------------------------------------------------------
ShowLinkColor Yes;    // makes montage->chart link groups visible at a glance

MsgBox("Layout built. Now: name each window per the comments, then File > Save Desktop.");
