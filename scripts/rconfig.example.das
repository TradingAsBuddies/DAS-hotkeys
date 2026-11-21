// ==========================================================
// rconfig.example.das   the shape of the per-account R globals
//
// R is the money risk unit for one account. It follows account size and
// is not typed into any button script: scripts 40 and 41 read these
// globals and size a position so that a stop-out loses at most 1R.
//
// The real file is scripts/local/baf-rconfig.das (gitignored: it holds
// account IDs and R). tools/baf_rconfig.py writes it from the private
// R-CONFIG table; paste it at the TOP of
//   Setup > Hotkey > Scripts > Desktop Load Script
// so DAS sets the globals whenever the desktop loads. Re-run the tool and
// paste again when R changes.
//
// Three slots are always written. An unused slot is "none" with R 0,
// because a DAS variable assigned "" stays unregistered. R 0 makes the
// buttons refuse, so these placeholders are safe to load as they are.
// ==========================================================
$BAF_ACCT1 = "LIVE_ACCOUNT_ID";   // LIVE
$BAF_R1 = 0;
$BAF_ACCT2 = "SIM_ACCOUNT_ID";    // SIM
$BAF_R2 = 0;
$BAF_ACCT3 = "none";
$BAF_R3 = 0;
MsgLog("BAF R-CONFIG loaded");
