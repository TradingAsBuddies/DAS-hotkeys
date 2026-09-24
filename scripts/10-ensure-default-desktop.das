// ============================================================================
// 10-ensure-default-desktop.das  —  make sure the default desktop carries
//                                    a montage named montage1 and a chart
//                                    named hidden_chart1
// ============================================================================
//
// THREE BLOCKS. Bind each to its own hotkey.
//
//   HOTKEY A — ENSURE.  Creates and names each window only if no window of
//              that name exists, then (re)parks hidden_chart1 off-screen.
//              Safe to press again.
//   HOTKEY B — VERIFY.  Read-only. Dumps both window objects and the real
//              geometry of the hidden chart.
//   HOTKEY C — SHOW.    One line. Brings every off-screen window, including
//              hidden_chart1, to the centre of the screen so you can work on
//              it. Press A afterwards to park it again.
//
// AFTER PRESSING A:  File > Save Desktop.
//   "Give Montage window a name and then save desktop so restarting DAS
//    will keep montage name"                — das-advanced-hotkey-guide.pdf p.35
//
// PREREQUISITE: Setup > Other Configuration > "Hotkey Advanced Script" ON.
//
// Rationale, what DAS means by "hidden", the full procedure, and the
// unverified assumptions live in docs/DEFAULT-DESKTOP.md. Read that first.
//
// COMMANDS USED, WITH CITATIONS
//   NewWindow Montage|Chart   das-advanced-hotkey-guide.pdf p.8
//   GetWindowObj()            "grab the most recently created window"   p.13
//   $w.name = "..."           p.13 —  $myMontage.name = "montageWindow";
//   $w.SYMBOL = "..."         p.13 (montage); chart write VERIFIED on build 2026-09-20
//   GetWindowObj("name")      das-hotkeys-guide.pdf p.26
//   isObject($w)              "verify the object is valid or not"        p.26
//   FocusWindow name          das-hotkeys-guide.pdf p.21
//   SetPopOut Y               das-hotkeys-guide.pdf p.21
//   WPos X Y / WSize W H      p.20 — "can only be used with windows that pop out"
//   TitleBar N, GetRect       das-advanced-hotkey-guide.pdf p.9
//   ShowObject()              das-advanced-hotkey-guide.pdf p.14
//   GetWindowTitle()          das-advanced-hotkey-guide.pdf p.11
//   MsgBox / MsgLog           das-hotkeys-guide.pdf p.25
//   Wait(ms)                  das-hotkeys-guide.pdf p.27 — for async operations
//
// Geometry is written as literals on purpose. Every manual example passes
// literals to WPos/WSize/Symbol; whether they expand $variables is not
// documented, and 06/07/08 string-build their commands for the same reason.
// ============================================================================


// ---- HOTKEY A : ENSURE ------------------------------------------------------

$DD_CREATED = "";

// ---- montage1 ---------------------------------------------------------------
// An existing montage1 is left exactly where it is.
// VERIFIED on build 2026-09-20 (David, HOTKEY B on a fresh desktop): GetWindowObj
// on a missing name returns a non-object, isObject == 0, no script error. The
// guards here and in 06/07/08 are sound.
$dd_m = GetWindowObj("montage1");
if (isObject($dd_m) == 0) {
  NewWindow Montage;
  // FIRST-RUN FAILURE 2026-09-20: without the Wait, GetWindowObj() came back
  // empty and the script died with "ScriptError:100 Missing Object" at the
  // .name line, leaving an unnamed montage behind. NewWindow is asynchronous;
  // the hotkeys guide p.27 says Wait() exists for exactly that.
  Wait(500);
  $dd_m = GetWindowObj();
  if (isObject($dd_m) == 0) {
    MsgBox("Created a montage but could not grab it to name it." + "\n" +
           "Right-click its title bar > Name = montage1, then press again.");
    return;
  }
  $dd_m.name = "montage1";
  SetPopOut Y;
  WPos 0 0;
  WSize 520 900;
  $dd_m.SYMBOL = "SPY";
  $DD_CREATED = $DD_CREATED + "montage1 ";
}

// ---- hidden_chart1 ----------------------------------------------------------
$dd_c = GetWindowObj("hidden_chart1");
if (isObject($dd_c) == 0) {
  NewWindow Chart;
  Wait(500);
  $dd_c = GetWindowObj();
  if (isObject($dd_c) == 0) {
    MsgBox("Created a chart but could not grab it to name it." + "\n" +
           "Right-click its title bar > Name = hidden_chart1, then press again.");
    return;
  }
  $dd_c.name = "hidden_chart1";
  // Seed a symbol so studies have bars. Montage .SYMBOL is documented (p.13);
  // the same property on a chart object is not. If the chart stays blank,
  // set its symbol by hand once and Save Desktop.
  $dd_sym = $dd_m.SYMBOL;
  if ($dd_sym == "") { $dd_sym = "SPY"; }
  $dd_c.SYMBOL = $dd_sym;
  $DD_CREATED = $DD_CREATED + "hidden_chart1 ";
}

// (Re)park the hidden chart EVERY press, created or not, so that after
// ShowAllHiddenWindows a second press puts it back.
// "Hidden windows include ... pop out windows that are out of the monitor
//  display area."                                   — das-hotkeys-guide.pdf p.21
// MEASURED on build 2026-09-20, GetRect after this block ran WPos then WSize:
//   6162,10063,6297,10125  = left,top,right,bottom
// X was clamped from 10000 to 6162 (virtual desktop edge); Y held at 10063, so
// the window is fully below every monitor: hidden. But the size collapsed to
// 135x62 instead of 800x600. WSize now runs BEFORE WPos so the window is sized
// while still on-screen. Re-run HOTKEY B; the rect should read ~800 wide.
FocusWindow hidden_chart1;
SetPopOut Y;
WSize 800 600;
WPos 10000 10000;
TitleBar N;

// Give focus back to the montage so the next unqualified hotkey acts there.
FocusWindow montage1;

// ---- Report -----------------------------------------------------------------
if ($DD_CREATED == "") {
  MsgLog("10-ensure: montage1 and hidden_chart1 present; hidden_chart1 re-parked");
} else {
  MsgBox("Created: " + $DD_CREATED + "\n\n" +
         "NOW: File > Save Desktop, or these names are lost on restart." + "\n" +
         "THEN: add studies to hidden_chart1 (ShowAllHiddenWindows to reach it)," + "\n" +
         "      press this hotkey again to re-park it, and Save Desktop again.");
}


// ---- HOTKEY B : VERIFY ------------------------------------------------------
// Read-only. On a fresh desktop, run BEFORE A: if you get a script error and
// no log line at all, GetWindowObj throws on a missing name and the isObject
// guards in A and in 00 need rework. After A: confirms both exist and where
// the chart really is.

$dd_vm = GetWindowObj("montage1");
$dd_vc = GetWindowObj("hidden_chart1");

MsgLog("10-verify: isObject(montage1) = ", isObject($dd_vm));
MsgLog("10-verify: isObject(hidden_chart1) = ", isObject($dd_vc));

// If GetWindowObj("missing") ever falls back to "the most recently created
// window" (the no-arg behaviour, adv guide p.13), isObject would return 1 for
// a window that is NOT montage1 and HOTKEY A would never create anything.
// The title and name lines below expose that: they must say montage1.
if (isObject($dd_vm) == 1) {
  MsgLog("10-verify: montage1 title = ", $dd_vm.GetWindowTitle());
  MsgLog("10-verify: montage1 name  = ", $dd_vm.name);
  $dd_vm.ShowObject();
}

if (isObject($dd_vc) == 1) {
  MsgLog("10-verify: hidden_chart1 title = ", $dd_vc.GetWindowTitle());
  MsgLog("10-verify: hidden_chart1 name  = ", $dd_vc.name);
  FocusWindow hidden_chart1;
  GetRect;
  FocusWindow montage1;
  MsgBox("hidden_chart1 exists. GetRect popup = left,top,right,bottom." + "\n" +
         "Off-screen = hidden. On-screen = Windows clamped it; edit the" + "\n" +
         "WPos 10000 10000 line in HOTKEY A and press A again.");
} else {
  MsgBox("hidden_chart1 NOT found. Run HOTKEY A, then File > Save Desktop.");
}


// ---- HOTKEY C : SHOW --------------------------------------------------------
// "Move all hidden windows to the center of the screen. Hidden windows include
//  ... pop out windows that are out of the monitor display area."
//                                                    — das-hotkeys-guide.pdf p.21
// Keep this one bound permanently; it is how you reach hidden_chart1 to add or
// change studies. HOTKEY A re-parks it.
ShowAllHiddenWindows;
