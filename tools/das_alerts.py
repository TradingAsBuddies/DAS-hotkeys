#!/usr/bin/env python3
"""DAS price alerts over the CMD API: plan, create, verify, audit.

    das_alerts.py add ABCD LONG 101.25 --op ">="          dry run: prints the payload
    das_alerts.py add ABCD LONG 101.25 --op ">=" --send   creates it, skips it if present
    das_alerts.py plan alerts.json [--send]               many at once (format below)
    das_alerts.py check "K0102 ABCD LONG 101.25" ...      is it in DAS? (live read)
    das_alerts.py log [--day 261119]                      today's alert activity (file only)

The CMD API has no alert command and pushes no alert message (Frontend CMD API Manual, 2021,
checked 2026-11-19). Alerts exist only as hotkey-script objects, so every call here is a
`SCRIPT GLOBALSCRIPT` injection, and every answer comes back through `MsgLog` in the DAS log.
Facts and drills: docs/CMD-API-ALERTS.md.

Safety:
- Nothing is sent without --send. The dry run prints exactly what --send would inject.
- Every payload is screened for order and desktop tokens (tools/hvc/das_out.FORBIDDEN)
  before the socket opens. `Reset` is refused too: the advanced guide says
  `$alert.Reset(); $alert.save();` removes alerts, and nobody has measured how many.
- Read-back guards with IsObj(). `GetAlertObj("missing").Symb` raised ScriptError:100 on
  2026-11-19, and that error opens a dialog that freezes the CMD API until it is dismissed.
- Login is the harness's watch-mode login on the paper account (tools/das_script_test.py).

plan file (JSON):

    {"prefix": "K0102",
     "alerts": [{"symbol": "ABCD", "tag": "LONG", "level": 101.25, "op": ">="},
                {"symbol": "WXYZ",  "tag": "PRIOR_LO", "level": 50.07, "op": "<="}]}

Each alert is named "<prefix> <SYMBOL> <TAG> <level>", the convention an earlier game plan
used. The default prefix is K plus today's month and day.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(TOOLS / "hvc"))
from das_script_test import (DAS, LogCursor, NoConnection, das_dir,  # noqa: E402
                             dismiss_errors, read_log_value)

# The same screen tools/hvc uses, kept in one place. Imported lazily in screen() because
# das_out imports the HVC engine.
OPS = (">", ">=", "=", "<", "<=")
FIELDS = ("L1 LAST", "L1 BID", "L1 ASK")      # L1 LAST created and read back 11-19
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")
TAG = re.compile(r"^[A-Z0-9_]{1,16}$")
NAME_SAFE = re.compile(r'^[^"\\;\r\n]{1,60}$')
ACCOUNT = re.compile(r"\b(?:TR|ACC)[A-Z0-9]{3,}\b")


class AlertError(ValueError):
    pass


@dataclass(frozen=True)
class Alert:
    symbol: str
    tag: str
    level: float
    op: str
    prefix: str
    field: str = "L1 LAST"

    @property
    def name(self) -> str:
        return f"{self.prefix} {self.symbol} {self.tag} {px(self.level)}"


def px(x: float) -> str:
    """Price text: at least two decimals, at most four. Names carry it, so 15 must print
    as 15.00 to match the alerts the game plan already made."""
    s = f"{x:.4f}".rstrip("0")
    return s + "0" * (2 - len(s.split(".")[1]))


def default_prefix(now: datetime | None = None) -> str:
    return f"K{(now or datetime.now()):%m%d}"


def make_alert(symbol: str, tag: str, level, op: str, prefix: str,
               field: str = "L1 LAST") -> Alert:
    symbol, tag = str(symbol).upper(), str(tag).upper()
    if not SYMBOL.match(symbol):
        raise AlertError(f"symbol {symbol!r}: letters, digits and '.', starting with a letter")
    if not TAG.match(tag):
        raise AlertError(f"tag {tag!r}: A-Z, 0-9 and '_', at most 16")
    if op not in OPS:
        raise AlertError(f"operator {op!r}: one of {' '.join(OPS)}")
    if field not in FIELDS:
        raise AlertError(f"field {field!r}: one of {', '.join(FIELDS)}")
    try:
        lv = float(level)
    except (TypeError, ValueError):
        raise AlertError(f"level {level!r}: not a number") from None
    if isinstance(level, bool) or not lv > 0 or lv == float("inf") or float(px(lv)) <= 0:
        raise AlertError(f"level {level!r}: must be a positive number of at least 0.0001")
    a = Alert(symbol, tag, lv, op, prefix, field)
    if not NAME_SAFE.match(a.name):
        raise AlertError(f"name {a.name!r}: no quotes, backslashes, ';' or line breaks, at most 60")
    return a


def load_plan(path: Path, prefix: str | None) -> list[Alert]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise AlertError(f"{path}: {e}") from None
    if not isinstance(data, dict) or not isinstance(data.get("alerts"), list):
        raise AlertError(f'{path}: expected {{"prefix": ..., "alerts": [...]}}')
    pre = prefix or data.get("prefix") or default_prefix()
    out, errs = [], []
    for i, row in enumerate(data["alerts"], 1):
        if not isinstance(row, dict):
            errs.append(f"alert {i}: not an object")
            continue
        try:
            out.append(make_alert(row.get("symbol", ""), row.get("tag", ""), row.get("level"),
                                  row.get("op", ""), pre, row.get("field", "L1 LAST")))
        except AlertError as e:
            errs.append(f"alert {i}: {e}")
    names = [a.name for a in out]
    errs += [f"name used twice: {n}" for n in sorted({n for n in names if names.count(n) > 1})]
    if errs:
        raise AlertError("; ".join(errs))
    return out


# ── payloads ─────────────────────────────────────────────────────────────────

def create_payload(a: Alert) -> str:
    """The exact form that created and read back on 5.8.4.8 on 2026-11-19."""
    return (f'$a = NewAlertObj(); $a.name = "{a.name}"; $a.Symb = "{a.symbol}"; '
            f'$a.AddItem("{a.field}", "{a.op}", "{px(a.level)}"); $a.save();')


def check_payload(name: str, tag: str) -> str:
    """IsObj guard: never touch a property of what GetAlertObj returns until it is an object."""
    if not NAME_SAFE.match(name):
        raise AlertError(f"name {name!r}: no quotes, backslashes, ';' or line breaks")
    return (f'$q = GetAlertObj("{name}"); if (IsObj($q)) {{ MsgLog("{tag}=", $q.Symb); }} '
            f'else {{ MsgLog("{tag}=MISSING"); }}')


def screen(payload: str) -> None:
    """Refuse order, desktop and Reset tokens in the CODE. String literals are blanked
    first, so a tag such as SHORT or COVER inside a quoted name is not code. Names and
    symbols cannot hold a quote (NAME_SAFE, SYMBOL), so nothing escapes a literal."""
    from das_out import FORBIDDEN          # noqa: E402  (tools/hvc)
    code = re.sub(r'"[^"]*"', '""', payload)
    m = FORBIDDEN.search(code) or re.search(r"\bReset\b", code, re.I)
    if m:
        raise AlertError(f"refusing token {m.group(0)!r} in: {payload}")


# ── live ─────────────────────────────────────────────────────────────────────

def exists(das: DAS, name: str, symbol: str | None = None) -> bool | None:
    """True / False from DAS. None when no clean answer came back: no value, or a script
    error (a runtime error still logs a type string as the "value"). With `symbol`, present
    means the alert's .Symb equals it."""
    tag = f"alr{int(time.time() * 1000) % 10_000_000}"
    p = check_payload(name, tag)
    screen(p)
    cur = LogCursor()
    das.script("GLOBALSCRIPT", p, 0.6)
    val = read_log_value(tag, tries=6)
    errs = cur.new_lines(("Error",))
    if val is None:
        errs += dismiss_errors()
    for e in errs:
        print("   SCRIPT ERROR:", ACCOUNT.sub("<acct>", e)[:200], file=sys.stderr)
    if val is None or errs:
        return None
    val = val.strip()
    if val == "MISSING":
        return False
    return val == symbol if symbol else True


def send(alerts: list[Alert]) -> int:
    payloads = [create_payload(a) for a in alerts]
    for p in payloads:
        screen(p)
    try:
        das = DAS().connect()
    except NoConnection as e:
        print(f"NO CONNECTION: {e}", file=sys.stderr)
        return 2
    made = skipped = failed = 0
    try:
        for a, p in zip(alerts, payloads):
            try:
                before = exists(das, a.name)
                if before is None:
                    print(f"FAIL     {a.name}: no clean answer to the existence check; nothing sent")
                    failed += 1
                    continue
                if before:
                    print(f"present  {a.name}  (name only: operator and field are not compared)")
                    skipped += 1
                    continue
                reply = das.script("GLOBALSCRIPT", p, 0.6)
                if "does not exist" in reply or "Wrong command" in reply:
                    print(f"FAIL     {a.name}: {reply.strip()[:120]}")
                    failed += 1
                    continue
                if exists(das, a.name, a.symbol):
                    print(f"created  {a.name}  ({a.field} {a.op} {px(a.level)})")
                    made += 1
                else:
                    print(f"FAIL     {a.name}: sent, but not confirmed by read-back")
                    failed += 1
            except (NoConnection, RuntimeError, OSError) as e:
                print(f"FAIL     {a.name}: {e}")
                failed += 1
    finally:
        das.close()
    print(f"{made} created, {skipped} already present, {failed} failed")
    return 1 if failed else 0


def cmd_check(names: list[str]) -> int:
    try:
        das = DAS().connect()
    except NoConnection as e:
        print(f"NO CONNECTION: {e}", file=sys.stderr)
        return 2
    bad = 0
    try:
        for n in names:
            try:
                r = exists(das, n)
            except (AlertError, NoConnection, RuntimeError, OSError) as e:
                print(f"ERROR     {n}: {e}")
                bad += 1
                continue
            print(f"{ {True: 'present', False: 'missing', None: 'NO ANSWER'}[r]:9} {n}")
            bad += r is None
    finally:
        das.close()
    return 1 if bad else 0


# ── log audit (file only) ────────────────────────────────────────────────────

CREATE = re.compile(r'\$a\.name = "([^"]+)"; \$a\.Symb = "([^"]+)"; '
                    r'\$a\.AddItem\("([^"]+)", "([^"]+)", "([^"]+)"\); \$a\.save\(\);')


def audit(lines: list[str]) -> dict[str, list]:
    """Alert creations, read-backs and alert-related errors in DAS log lines."""
    out: dict[str, list] = {"created": [], "checks": [], "errors": []}
    for ln in lines:
        stamp = ln[:8]
        if ",CMDAPILog," in ln and "NewAlertObj" in ln:
            m = CREATE.search(ln)
            out["created"].append((stamp, *m.groups()) if m else (stamp, "?", "?", "?", "?", "?"))
        elif ",CMDAPILog," in ln and "GetAlertObj" in ln:
            m = re.search(r'GetAlertObj\("([^"]+)"\)', ln)
            out["checks"].append((stamp, m.group(1) if m else "?"))
        elif ",Error," in ln and "Alert" in ln:
            out["errors"].append(ACCOUNT.sub("<acct>", ln)[:200])
    return out


def cmd_log(day: str | None) -> int:
    log_dir = das_dir() / "LOG"
    path = log_dir / f"{day}Log.txt" if day else max(log_dir.glob("*Log.txt"),
                                                      key=lambda p: p.stat().st_mtime, default=None)
    if not path or not path.exists():
        print(f"no log at {path}")
        return 1
    r = audit(path.read_text(errors="replace").splitlines())
    print(f"{path.name}: {len(r['created'])} created, {len(r['checks'])} read-backs, "
          f"{len(r['errors'])} alert errors")
    for stamp, name, sym, field, op, lv in r["created"]:
        print(f"  {stamp}  {name:34} {sym:6} {field} {op} {lv}")
    for e in r["errors"]:
        print("  ERROR", e)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("add", help="one alert")
    p.add_argument("symbol"); p.add_argument("tag"); p.add_argument("level")
    p.add_argument("--op", required=True, choices=OPS)
    p.add_argument("--field", default="L1 LAST", choices=FIELDS)
    p.add_argument("--prefix"); p.add_argument("--send", action="store_true")
    p = sub.add_parser("plan", help="alerts from a JSON plan")
    p.add_argument("file"); p.add_argument("--prefix"); p.add_argument("--send", action="store_true")
    p = sub.add_parser("check", help="live read-back by name, IsObj-guarded")
    p.add_argument("names", nargs="+")
    p = sub.add_parser("log", help="alert activity in a DAS log (no socket)")
    p.add_argument("--day", help="YYMMDD; default the newest log")
    a = ap.parse_args()

    if a.cmd == "log":
        return cmd_log(a.day)
    if a.cmd == "check":
        return cmd_check(a.names)
    try:
        alerts = ([make_alert(a.symbol, a.tag, a.level, a.op, a.prefix or default_prefix(), a.field)]
                  if a.cmd == "add" else load_plan(Path(a.file), a.prefix))
        for al in alerts:
            screen(create_payload(al))
    except AlertError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    if not a.send:
        for al in alerts:
            print(f"SCRIPT GLOBALSCRIPT {create_payload(al)}")
        print(f"dry run: {len(alerts)} alert(s); add --send to create them", file=sys.stderr)
        return 0
    return send(alerts)


if __name__ == "__main__":
    sys.exit(main())
