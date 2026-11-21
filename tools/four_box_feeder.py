#!/usr/bin/env python3
"""Four-box readout: keep a DAS hot button showing the latest SPY box from Market Vision.

Forum topic `four-box-readout`. A DAS button cannot read a file, so this process reads
~/.claude/LifeOS/USER/TRADING/Vision/vision-log.jsonl (written by ~/.claude/Tools/market_vision.py)
and writes the result into a named button over the CMD API (docs/WISDOM.md, "Hot Buttons Are a
Display the CMD API Can Write"). It sends no order and the button runs no script.

    four_box_feeder.py --once              write the tile once, report, exit
    four_box_feeder.py                     rewrite every --every seconds until Ctrl-C
    four_box_feeder.py --once --dry-run    print the read and the DAS script; no socket

The tile shows the newest SPY box read from TODAY (exchange date), no older than --max-age
minutes. Anything else, including a premarket record (box null) or a producer UNAVAILABLE,
shows UNAVAILABLE. It never guesses and never carries a box forward from yesterday.

Setup: a Text-type hot button named `dash_box` (--button) on the window `montage1` (--window).
Run with DAS_DIR set to the running install so the harness reads the right log.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from das_script_test import DAS, LogCursor, NoConnection, dismiss_errors  # noqa: E402

LOG = Path.home() / ".claude/LifeOS/USER/TRADING/Vision/vision-log.jsonl"
ET = ZoneInfo("America/New_York")
BOXES = ("HSLW", "LSHW", "LSLW", "HSHW")
# background, text. Meanings from market_vision.py: HSLW trend up, LSHW trend down,
# LSLW chop (FL stands down), HSHW two-way, UNAVAILABLE triggers only.
COLORS = {"HSLW": ("Green", "White"), "LSHW": ("Red", "White"), "LSLW": ("Yellow", "Black"),
          "HSHW": ("Blue", "White"), "UNAVAILABLE": ("Gray", "White")}
OK_TAG = "DASH box ok"


def read_box(now: dt.datetime, max_age: dt.timedelta, path: Path = LOG) -> tuple[str, str]:
    """(box, label) for the tile. box is one of BOXES or UNAVAILABLE; label is the button text."""
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return "UNAVAILABLE", "BOX: UNAVAILABLE (no log)"
    today = now.astimezone(ET).date()
    for line in reversed(lines):
        try:
            rec = json.loads(line)
            ts = dt.datetime.fromisoformat(rec["ts"]).astimezone(ET)
        except (ValueError, KeyError, TypeError):
            continue
        if ts.date() != today:
            break
        box = rec.get("box")
        if box is None:
            continue                      # premarket record: no box read in it
        if box not in BOXES:
            return "UNAVAILABLE", f"SPY UNAVAILABLE {ts:%H:%M}"
        if now - ts > max_age:
            return "UNAVAILABLE", f"BOX STALE {ts:%H:%M}"
        label = f"SPY {box} {ts:%H:%M}"
        qqq = ((rec.get("box_detail") or {}).get("QQQ") or {}).get("box")
        if qqq and qqq != box:
            label += f" Q:{qqq}"
        return box, label
    return "UNAVAILABLE", "BOX: UNAVAILABLE"


def tile_script(window: str, button: str, box: str, label: str) -> str:
    """Guarded write: a missing window or button logs a line instead of raising the
    ScriptError dialog that freezes the API (WISDOM, P1/P2)."""
    bg, fg = COLORS[box]
    if '"' in label or "'" in label:
        raise ValueError("label must not contain quotes")
    return (f'$dw = GetWindowObj("{window}"); '
            f'if (isObject($dw) == 1) {{ $db = $dw.GetCustButObj("{button}"); '
            f'if (isObject($db) == 1) {{ $db.text = "{label}"; '
            f'$db.BkColor = Color("{bg}"); $db.FgColor = Color("{fg}"); '
            f'MsgLog("{OK_TAG} {box}"); }} else {{ MsgLog("DASH no button {button}"); }} }} '
            f'else {{ MsgLog("DASH no window {window}"); }}')


def write_tile(das: DAS, script: str) -> str:
    """Inject and read DAS's own log for the outcome: ok, missing, error or silent."""
    """Dismisses a ScriptError dialog only when its log line quotes this feeder's own script.
    A dialog from the operator's own hotkey is left open for the operator to read; while it is
    open the API is frozen and the write comes back silent."""
    cur = LogCursor()
    das.script("GLOBALSCRIPT", script, 1.0)
    time.sleep(0.5)
    lines = cur.new_lines()
    for l in lines:
        if ",Error," in l and "$dw = GetWindowObj" in l:
            dismiss_errors()
            return "error: " + l.split(",Error,", 1)[1][:120]
    for l in lines:
        if OK_TAG in l:
            return "ok"
        if "DASH no " in l:
            return "missing: " + l.split("DASH no ", 1)[1].strip()
    return "silent: no log line (a DAS dialog may be open, or DAS_DIR points at the wrong install)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", default="montage1")
    ap.add_argument("--button", default="dash_box")
    ap.add_argument("--every", type=int, default=60, help="seconds between writes")
    ap.add_argument("--max-age", type=int, default=240, help="minutes before a box read is STALE")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print, open no socket")
    a = ap.parse_args()
    max_age = dt.timedelta(minutes=a.max_age)

    das: DAS | None = None
    try:
        while True:
            now = dt.datetime.now(ET)
            box, label = read_box(now, max_age)
            script = tile_script(a.window, a.button, box, label)
            if a.dry_run:
                print(f"{now:%H:%M:%S} {box:11} [{label}]\n{script}")
                return 0
            try:
                das = das or DAS().connect()
                result = write_tile(das, script)
            except NoConnection as exc:
                das = None
                result = f"NO CONNECTION: {exc}"
            print(f"{now:%H:%M:%S} {box:11} [{label}] {result}", flush=True)
            if a.once:
                return 0 if result == "ok" else 1
            time.sleep(a.every)
    except KeyboardInterrupt:
        return 0
    finally:
        if das:
            das.close()


if __name__ == "__main__":
    sys.exit(main())
