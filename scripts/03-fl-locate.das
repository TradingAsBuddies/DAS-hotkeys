// ============================================================================
// 03-fl-locate.das  —  Fashionably Late trigger: 9-EMA x 34-SMA cross
// Paste into: flChart1m > Chart Script, BELOW the contents of 02.
// ============================================================================
//
// ─────────────────────────────────────────────────────────────────────────────
// DEFINITION — updated 2026-09-05 on David's instruction
//
// FL is now the 9-EMA x 34-SMA cross. This replaces the 9-EMA x VWAP cross that
// both of these still describe:
//
//   ~/falcon/dashboard/fl_monitor_spec.md          (spec — updated, see note)
//   ~/.claude/skills/_retired-2026-07-14/Trading/PlaybookSetups.md   (retired)
//
// ** THE PYTHON STACK STILL IMPLEMENTS THE OLD DEFINITION. **
// fl_shared.py computes ema9 and vwap and compares them; there is no 34-SMA in
// it. Until that code changes, this chart script and fl_monitor.py are watching
// for two different events on the same tickers. Do not treat agreement between
// them as confirmation — they cannot agree.
//
// Retained from the old definition, unchanged:
//   - volume confirmation, vol > 1.5x 20-bar average
//   - no entry before 09:45 ET
// ─────────────────────────────────────────────────────────────────────────────
//
// Relationship to 02: the coil is the precursor, this is the event. The MAs
// compress (02 goes amber), then one crosses the other (this fires). A cross
// with no preceding coil is a wide-gap whipsaw and generally worse.
//
// SETUP: Text hot button named exactly  FLSIG
// ============================================================================

// `data` was created in 02, which runs first in the same Chart Script.
// Recreate defensively in case this block is bound to a hotkey on its own.
if (isObject(data) == 0) { data = NewUserObj(); }

if (data.e9 == 0)  { return; }
if (data.s34 == 0) { return; }

// ---- Cross detection --------------------------------------------------------
// Sign of (ema9 - sma34) this update vs last. A sign change is the cross.
// Stored on `data`, so each chart window tracks its own side independently.

data.sidePrev = data.side;

if (data.e9 > data.s34) {
  data.side = 1;
} else {
  data.side = -1;
}

data.cross = 0;
if (data.side == 1) {
  if (data.sidePrev == -1) { data.cross = 1; }     // cross UP   -> long
}
if (data.side == -1) {
  if (data.sidePrev == 1) { data.cross = -1; }     // cross DOWN -> short
}

// ---- Confirmation: volume on the cross bar ---------------------------------
// No rolling average is exposed, so this walks back 20 completed bars.
// 20 iterations, well inside the documented 200-loop cap.
//
// TWO UNVERIFIED ASSUMPTIONS — settle both with F8 before trusting this:
//   1. Bar property name. The manuals show $bar.Hi and $bar.Lo (hot buttons
//      guide p.13) but never volume. If it is not "Volume", fix both refs.
//   2. Computed bar index. The manuals only show a literal GetBar(-5), never
//      an expression. If GetBar(0 - $i) returns nothing, unroll the loop.

data.volsum = 0;
$fl_i       = 2;
while ($fl_i < 22) {
  data.volsum = data.volsum + GetBar(0 - $fl_i).Volume;
  $fl_i       = $fl_i + 1;
}
data.volavg = data.volsum / 20;
data.volnow = GetBar(-1).Volume;

data.volok = 0;
if (data.volavg > 0) {
  if (data.volnow > data.volavg * $FL_VOL_MULT) { data.volok = 1; }
}

// ---- Time gate --------------------------------------------------------------
data.gateok = 0;
if (GetSecond() >= $FL_GATE_SEC) { data.gateok = 1; }

// ---- Verdict ----------------------------------------------------------------
if (data.cross == 0) {
  GetCustButObj("FLSIG").BkColor = Color(40, 40, 40);
  GetCustButObj("FLSIG").FgColor = Color(180, 180, 180);
  GetCustButObj("FLSIG").Text    = "FL  --";
  return;
}

if (data.gateok == 0) {
  GetCustButObj("FLSIG").BkColor = Color(70, 70, 70);
  GetCustButObj("FLSIG").FgColor = Color(150, 150, 150);
  GetCustButObj("FLSIG").Text    = "FL  early";
  return;
}

if (data.volok == 0) {
  // Cross fired, volume did not confirm. Per the playbook this is noise.
  GetCustButObj("FLSIG").BkColor = Color(90, 70, 0);
  GetCustButObj("FLSIG").FgColor = Color(220, 220, 220);
  GetCustButObj("FLSIG").Text    = "FL  unconfirmed";
  return;
}

if (data.cross == 1) {
  GetCustButObj("FLSIG").BkColor = Color(0, 160, 60);
  GetCustButObj("FLSIG").FgColor = Color(255, 255, 255);
  GetCustButObj("FLSIG").Text    = "FL LONG";
  if ($FL_ARMED == 1) { Speak("F L long"); }
}

if (data.cross == -1) {
  GetCustButObj("FLSIG").BkColor = Color(200, 40, 40);
  GetCustButObj("FLSIG").FgColor = Color(255, 255, 255);
  GetCustButObj("FLSIG").Text    = "FL SHORT";
  if ($FL_ARMED == 1) { Speak("F L short"); }
}

// NOTE: signals only. Sends no orders. FL execution lives in
// ~/falcon/dashboard/fl_trading_agent.py against SIM TR4425, whose I-1
// invariant forbids entry without a computed ATR. Keep it that way.
