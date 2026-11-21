// m3.ping: proves which build of the hotkey file DAS is running.
// tools/gen_htk.py replaces the build token with the build time (US Eastern).
// It logs that time and writes the hour and minute on the PING button, so a reload that did
// not take shows at a glance. It also clears $M3_BUSY, the flag scripts 43
// and 44 set while they run, in case one died part-way.
$M3_BUSY = 0;
MsgLog("htk ping ok, build @BUILD@ (busy flag cleared)");
$m = GetWindowObj("montage3");
if (isObject($m) == 1) {
  $b = $m.GetCustButObj("m3_ping");
  if (isObject($b) == 1) { $b.text = "PING @BUILDHM@"; }
}
