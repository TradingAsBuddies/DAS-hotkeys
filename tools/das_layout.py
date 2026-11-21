#!/usr/bin/env python3
"""Build DAS windows from a layout file, entirely by executed scripts.

A layout file (JSON, kept in the gitignored scripts/local/) lists windows. For each one this
tool writes the hotkey script that creates it, names it, sizes and places it, and fills it:
a symbol, a chart timeframe, a saved chart setting (.cst, which carries the studies), and
the faces of its hot buttons. A montage's buttons come from a template window copied with
DuplicateWindow, because no script command creates a button (WISDOM, 2026-11-18).

  das_layout.py build FILE                 dry run: print every SCRIPT line, send nothing
  das_layout.py build FILE --send          create missing windows, confirm each by name
  das_layout.py build FILE --send --reconfigure   also re-apply geometry and content
  das_layout.py check FILE                 which of the file's windows exist (live)
  das_layout.py close FILE --send          close the file's windows, and only those
  das_layout.py script FILE [-o OUT.das]   one standalone script: bind it to a hotkey,
                                           or paste it into the Desktop Load Script

Window entry:
  {"name": "lay_c1", "type": "Chart", "pos": [528, 0], "size": [1100, 900],
   "symbol": "SPY", "minutes": 1, "days": 2, "setting": "ema9-and-sma34.cst",
   "titlebar": true}
  {"name": "lay_m2", "clone": "montage1", "pos": [0, 0], "size": [520, 900],
   "symbol": "QQQ", "buttons": {"dash_box": {"text": "READY", "bg": "Green", "fg": "White"}}}

Safety: every payload is screened for order tokens (tools/hvc FORBIDDEN) and for
desktop-save tokens before the socket opens. Saving the desktop stays the operator's step.
Login is the harness's watch-mode login on the paper account.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "hvc"))
from das_script_test import (DAS, LogCursor, NoConnection, das_dir, dismiss_errors,
                             read_log_value)  # noqa: E402

NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,31}$")
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.]{0,9}$")
CST = re.compile(r"^[A-Za-z0-9_.-]{1,60}\.cst$")
TEXT = re.compile(r'^[^"\\;\r\n]{0,24}$')
# das-hotkeys-guide.pdf, NewWindow list (2025 revision)
TYPES = {t.lower(): t for t in (
    "Account Alert Basket Chart EventLog HighLow MarketView Montage Option Order "
    "Position TimeSale Toplist Trade TradeLog").split()}
CLONABLE = {"montage", "chart", "timesale", "option"}       # DuplicateWindow, hotkeys guide p.21
COLORS = {"red", "green", "yellow", "blue", "gray", "black", "white"}   # [V] 11-18, P11
DESKTOP = re.compile(r"\b(SaveDesktop|SaveLayout|ClearDesktop|SwitchDesktop|LoadDesktop|"
                     r"Close|Reset|Panic)\b", re.I)
WAIT_MS = 500                                   # NewWindow is asynchronous [V 2026-09-20]


class LayoutError(ValueError):
    pass


@dataclass
class Win:
    name: str
    type: str                      # canonical NewWindow type, or the template's for a clone
    clone: str | None = None
    pos: tuple[int, int] | None = None
    size: tuple[int, int] | None = None
    symbol: str | None = None
    minutes: int | None = None
    days: int | None = None
    daybars: int | None = None
    setting: str | None = None
    titlebar: bool | None = None
    link: str | None = None
    buttons: dict[str, dict] = field(default_factory=dict)


def _pair(v, what: str, lo: int, hi: int) -> tuple[int, int]:
    if (not isinstance(v, list) or len(v) != 2
            or not all(isinstance(n, int) and not isinstance(n, bool) for n in v)):
        raise LayoutError(f"{what} must be [int, int]")
    if not all(lo <= n <= hi for n in v):
        raise LayoutError(f"{what} {v} outside {lo}..{hi}")
    return v[0], v[1]


def _int(v, what: str, lo: int, hi: int) -> int:
    if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
        raise LayoutError(f"{what} must be an integer {lo}..{hi}")
    return v


def make_window(d: dict, cst_dir: Path | None = None) -> Win:
    if not isinstance(d, dict):
        raise LayoutError("each window is an object")
    unknown = set(d) - {"name", "type", "clone", "pos", "size", "symbol", "minutes", "days",
                        "daybars", "setting", "titlebar", "buttons", "template_type", "link"}
    if unknown:
        raise LayoutError(f"unknown keys {sorted(unknown)}")
    name = d.get("name")
    if not isinstance(name, str) or not NAME.match(name):
        raise LayoutError(f"name {name!r}: letters, digits, underscore; starts with a letter")
    clone = d.get("clone")
    if clone is not None:
        if not isinstance(clone, str) or not NAME.match(clone) or clone.lower() == name.lower():
            raise LayoutError(f"{name}: clone must name a different window")
        if "type" in d:
            raise LayoutError(f"{name}: give type or clone, not both")
        kind = str(d.get("template_type", "Montage")).lower()
    else:
        kind = str(d.get("type", "")).lower()
    if kind not in TYPES:
        raise LayoutError(f"{name}: type {kind!r} is not a NewWindow type")
    if clone and kind not in CLONABLE:
        raise LayoutError(f"{name}: DuplicateWindow copies only Montage, Chart, TimeSale, Option")
    w = Win(name=name, type=TYPES[kind], clone=clone)
    if "pos" in d:
        w.pos = _pair(d["pos"], f"{name}.pos", -10000, 20000)
    if "size" in d:
        w.size = _pair(d["size"], f"{name}.size", 50, 8000)
    if "symbol" in d:
        if not isinstance(d["symbol"], str) or not SYMBOL.match(d["symbol"].upper()):
            raise LayoutError(f"{name}: bad symbol {d['symbol']!r}")
        w.symbol = d["symbol"].upper()
    chart_keys = {"minutes", "days", "daybars", "setting"} & set(d)
    if chart_keys and w.type != "Chart":
        raise LayoutError(f"{name}: {sorted(chart_keys)} apply to charts only")
    if "minutes" in d and "daybars" in d:
        raise LayoutError(f"{name}: minutes or daybars, not both")
    if "minutes" in d:
        w.minutes = _int(d["minutes"], f"{name}.minutes", 1, 390)
    if "daybars" in d:
        w.daybars = _int(d["daybars"], f"{name}.daybars", 1, 30)
    if "days" in d:
        if w.minutes is None and w.daybars is None:
            raise LayoutError(f"{name}: days is the range of a minutes or daybars chart")
        w.days = _int(d["days"], f"{name}.days", 1, 3650)
    if "setting" in d:
        s = d["setting"]
        if not isinstance(s, str) or not CST.match(s):
            raise LayoutError(f"{name}: setting must be a bare file name ending .cst")
        if cst_dir is not None and cst_dir.is_dir() and not (cst_dir / s).is_file():
            raise LayoutError(f"{name}: {s} not found in {cst_dir}")
        w.setting = s
    if "titlebar" in d:
        if not isinstance(d["titlebar"], bool):
            raise LayoutError(f"{name}: titlebar is true or false")
        w.titlebar = d["titlebar"]
    if "link" in d:
        if not isinstance(d["link"], str) or not re.fullmatch(r"[A-Za-z]{3,12}", d["link"]):
            raise LayoutError(f"{name}: link is a colour name such as Red or Blue")
        w.link = d["link"].capitalize()
    btns = d.get("buttons", {})
    if not isinstance(btns, dict):
        raise LayoutError(f"{name}: buttons is an object of button-name to face")
    for bn, face in btns.items():
        if not NAME.match(bn) or not isinstance(face, dict) or set(face) - {"text", "bg", "fg"}:
            raise LayoutError(f"{name}: button {bn!r} needs a plain name and text/bg/fg only")
        if "text" in face and (not isinstance(face["text"], str) or not TEXT.match(face["text"])):
            raise LayoutError(f"{name}.{bn}: text up to 24 chars, no quotes or ;")
        for k in ("bg", "fg"):
            if k in face and str(face[k]).lower() not in COLORS:
                raise LayoutError(f"{name}.{bn}: {k} must be one of {sorted(COLORS)}")
    w.buttons = btns
    return w


def load_layout(path: Path, cst_dir: Path | None = None) -> list[Win]:
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise LayoutError(f"{path}: {e}")
    rows = data.get("windows") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        raise LayoutError(f"{path}: needs a non-empty \"windows\" list")
    wins, errs = [], []
    for i, r in enumerate(rows, 1):
        try:
            wins.append(make_window(r, cst_dir))
        except LayoutError as e:
            errs.append(f"window {i}: {e}")
    if errs:
        raise LayoutError("; ".join(errs))
    names = [w.name.lower() for w in wins]          # window names are case-insensitive [V]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise LayoutError(f"duplicate window names: {dup}")
    clash = sorted({w.clone for w in wins if w.clone and w.clone.lower() in names})
    if clash:
        raise LayoutError(f"a template must already exist, not be built here: {clash}")
    return wins


# ── payloads: (window the SCRIPT runs in, script text) ───────────────────────

def create_payload(w: Win) -> tuple[str, str]:
    """Make the window, and nothing else. DAS builds it only after the script returns:
    on 2026-11-19 a `Wait(500)` inside the same script still let GetWindowObj() return the
    PREVIOUS newest window, and three names landed one window late, one of them on DAS's
    Internal Message window [V 10:19]. So creation, the check and the naming are separate
    sends with a pause between."""
    if w.clone:
        # Runs inside the template, so DuplicateWindow copies it with its buttons [D].
        return w.clone, "DuplicateWindow;"
    return "GLOBALSCRIPT", f"NewWindow {w.type};"


def probe_payload(tag: str, name: str | None = None) -> str:
    """Log kind and name of the newest window, or of a named one. Logging the object gives
    its class: Obj:TradeWindowObject (montage), Obj:ChartWindowObject (chart), with no
    script error [V 2026-11-19 10:58]. Reading .BID on a chart logs ScriptError:1."""
    get = f'GetWindowObj("{name}")' if name else "GetWindowObj()"
    return (f'$lw = {get}; if (isObject($lw)) {{ MsgLog("{tag}=", $lw, "|", $lw.name); }} '
            f'else {{ MsgLog("{tag}=NOOBJ"); }}')


def name_payload(w: Win) -> str:
    return f'$lw = GetWindowObj(); if (isObject($lw)) {{ $lw.name = "{w.name}"; }}'


KIND = {"Montage": "Obj:TradeWindowObject", "Chart": "Obj:ChartWindowObject"}


def kind_ok(w: Win, kind: str) -> bool:
    kind = kind.strip()
    if w.type in KIND:
        return kind == KIND[w.type]
    return kind.startswith("Obj:") and kind not in KIND.values()


def newest_ok(w: Win, value: str | None) -> str | None:
    """None when the newest window is the one just made; otherwise why not. A fresh window
    has no name; a DuplicateWindow copy carries its template's name [D]."""
    if value is None or value == "NOOBJ" or "|" not in value:
        return f"no newest window ({value})"
    kind, name = value.split("|", 1)
    want = w.clone or ""
    if name.strip().lower() != want.lower():
        return f"newest window is named {name.strip()!r}, not a fresh {w.type}"
    if not kind_ok(w, kind):
        return f"newest window is a {kind.strip()!r}, not a {w.type}"
    return None


def config_payload(w: Win) -> tuple[str, str] | None:
    """Runs inside the named window. Size before move: WSize after an off-screen WPos does
    not take [V 2026-09-20]. The .cst loads first, so symbol and timeframe win over it."""
    parts = []
    if w.pos or w.size:
        parts.append("SetPopOut Y;")
    if w.size:
        parts.append(f"WSize {w.size[0]} {w.size[1]};")
    if w.pos:
        parts.append(f"WPos {w.pos[0]} {w.pos[1]};")
    if w.titlebar is not None:
        parts.append(f"TitleBar {'Y' if w.titlebar else 'N'};")
    if w.link:
        # Same colour = linked: a montage symbol change moves the chart [V 2026-11-19 12:2x,
        # with a control]. Set before the symbol so linked windows agree.
        parts.append(f'$lw = GetWindowObj("{w.name}"); '
                     f'if (isObject($lw)) {{ $lw.LinkColor = "{w.link}"; }}')
    if w.setting:
        parts.append(f"LoadSetting {w.setting};")
    if w.symbol:
        if w.type == "Chart":
            parts.append(f"Symbol {w.symbol};")
        else:
            parts.append(f'$lw = GetWindowObj("{w.name}"); '
                         f'if (isObject($lw)) {{ $lw.SYMBOL = "{w.symbol}"; }}')
    if w.minutes:
        parts.append(f"MinuteChart {w.minutes}" + (f" {w.days}d;" if w.days else ";"))
    if w.daybars:
        parts.append(f"DayChart {w.daybars}d" + (f" {w.days}d;" if w.days else ";"))
    return (w.name, " ".join(parts)) if parts else None


def button_payloads(w: Win) -> list[tuple[str, str]]:
    """Faces only. A face is live state, not saved with the button [V 2026-11-18]."""
    out = []
    for bn, face in w.buttons.items():
        sets = []
        if "text" in face:
            sets.append(f'$lb.text = "{face["text"]}";')
        if "bg" in face:
            sets.append(f'$lb.BkColor = Color("{face["bg"].capitalize()}");')
        if "fg" in face:
            sets.append(f'$lb.FgColor = Color("{face["fg"].capitalize()}");')
        if sets:
            out.append((w.name, f'$lb = GetCustButObj("{bn}"); '
                                f'if (isObject($lb)) {{ {" ".join(sets)} }} '
                                f'else {{ MsgLog("das_layout no button {w.name}.{bn}"); }}'))
    return out


def screen(payload: str) -> None:
    from das_out import FORBIDDEN          # noqa: E402  (tools/hvc)
    code = re.sub(r'"[^"]*"', '""', payload)
    m = FORBIDDEN.search(code) or DESKTOP.search(code)
    if m:
        raise LayoutError(f"refusing token {m.group(0)!r} in: {payload}")


def all_payloads(w: Win, tag: str = "lay") -> list[tuple[str, str]]:
    """Dry-run view, in send order."""
    out = [create_payload(w), ("GLOBALSCRIPT", probe_payload(tag)), ("GLOBALSCRIPT", name_payload(w))]
    c = config_payload(w)
    if c:
        out.append(c)
    return out + button_payloads(w)


def standalone(wins: list[Win]) -> str:
    """One script for a hotkey or the Desktop Load Script: create what is missing, then
    configure everything. UNVERIFIED: over the CMD API, GetWindowObj() after NewWindow and
    Wait(500) in one script returned the previous window [V 2026-11-19]. A pressed hotkey
    worked on 2026-09-20, so the header tells the operator to check names after one run."""
    lines = ["// generated by tools/das_layout.py; bind to a hotkey, run once, then",
             "// File > Save Desktop so the window names survive a restart.",
             "// CHECK each window's name after the first run: over the CMD API on 2026-11-19",
             "// GetWindowObj() returned the previous window. Use `das_layout.py build --send`."]
    for w in wins:
        lines.append(f'$lw = GetWindowObj("{w.name}");')
        lines.append("if (isObject($lw) == 0) {")
        if w.clone:
            lines.append(f"  FocusWindow {w.clone};")
            lines.append("  DuplicateWindow;")
        else:
            lines.append(f"  NewWindow {w.type};")
        lines += [f"  Wait({WAIT_MS});", "  $lw = GetWindowObj();",
                  f'  $lw.name = "{w.name}";', "}"]
        rest = [config_payload(w)] + button_payloads(w)
        if any(rest):
            lines.append(f"FocusWindow {w.name};")
        for p in rest:
            if p:
                lines.append(p[1])
    lines.append(f'MsgLog("das_layout built {len(wins)} window(s)");')
    text = "\n".join(lines) + "\n"
    code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//"))
    screen(code.replace("FocusWindow", "").replace("DuplicateWindow", ""))
    return text


# ── live ─────────────────────────────────────────────────────────────────────

def _errors(cur: LogCursor) -> list[str]:
    return cur.new_lines(("Error",))


def send(wins: list[Win], reconfigure: bool) -> int:
    for w in wins:
        for _, p in all_payloads(w):
            screen(p)
    try:
        das = DAS().connect()
    except NoConnection as e:
        print(f"NO CONNECTION: {e}", file=sys.stderr)
        return 2
    made = kept = failed = 0
    try:
        for w in wins:
            try:
                present = das.exists(w.name)
                if present and not reconfigure:
                    print(f"present  {w.name}  (not touched; --reconfigure re-applies)")
                    kept += 1
                    continue
                if w.clone and not present and not das.exists(w.clone):
                    print(f"FAIL     {w.name}: template {w.clone} does not exist")
                    failed += 1
                    continue
                cur = LogCursor()
                bad = None
                if not present:
                    win, text = create_payload(w)
                    reply = das.script(win, text, 0.6)
                    if "does not exist" in reply or "Wrong command" in reply:
                        bad = reply.strip()[:120]
                    else:
                        time.sleep(1.5)
                        tag = f"lay{int(time.time() * 1000) % 10_000_000}"
                        das.script("GLOBALSCRIPT", probe_payload(tag), 0.4)
                        bad = newest_ok(w, read_log_value(tag, tries=6))
                        if bad:
                            bad += "; nothing renamed. A new window may be left unnamed"
                        else:
                            das.script("GLOBALSCRIPT", name_payload(w), 0.4)
                if bad is None:
                    tag = f"lay{int(time.time() * 1000) % 10_000_000}"
                    das.script(w.name, probe_payload(tag, w.name), 0.4)
                    v = read_log_value(tag, tries=6)
                    if v is None or "|" not in v:
                        bad = "no window answers to the name after naming"
                    elif not kind_ok(w, v.split("|", 1)[0]):
                        bad = f"the window named {w.name} is a {v.split('|', 1)[0].strip()!r}, not a {w.type}; not configured"
                if bad is None:
                    for win, text in [c for c in [config_payload(w)] if c] + button_payloads(w):
                        das.script(win, text, 0.6)
                errs = _errors(cur)
                if errs:
                    dismiss_errors()
                    bad = bad or "script error: " + errs[0][:160]
                if bad:
                    print(f"FAIL     {w.name}: {bad}")
                    failed += 1
                else:
                    print(f"{'updated ' if present else 'created '} {w.name}  ({w.type}"
                          f"{' from ' + w.clone if w.clone else ''}, kind checked)")
                    made += 1
            except (NoConnection, RuntimeError, OSError) as e:
                print(f"FAIL     {w.name}: {e}")
                failed += 1
    finally:
        das.close()
    print(f"{made} built, {kept} already present, {failed} failed")
    if made:
        print("Window names are lost on restart until File > Save Desktop (operator's step).")
    return 1 if failed else 0


def cmd_check(wins: list[Win]) -> int:
    try:
        das = DAS().connect()
    except NoConnection as e:
        print(f"NO CONNECTION: {e}", file=sys.stderr)
        return 2
    missing = 0
    try:
        for w in wins:
            ok = das.exists(w.name)
            missing += not ok
            print(f"{'present' if ok else 'missing'}  {w.name}")
    except (NoConnection, RuntimeError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2
    finally:
        das.close()
    return 1 if missing else 0


def cmd_close(wins: list[Win], go: bool) -> int:
    """SCRIPT <name> Close: an unknown name is refused by DAS and nothing runs, unlike
    FocusWindow + Close, which would close whatever had focus."""
    if not go:
        for w in wins:
            print(f"SCRIPT {w.name} Close;")
        print("dry run; add --send to close these windows", file=sys.stderr)
        return 0
    try:
        das = DAS().connect()
    except NoConnection as e:
        print(f"NO CONNECTION: {e}", file=sys.stderr)
        return 2
    try:
        for w in wins:
            reply = das.script(w.name, "Close;", 0.6)
            gone = "does not exist" in reply
            print(f"{'absent ' if gone else 'closed '} {w.name}")
    finally:
        das.close()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("build"); p.add_argument("file")
    p.add_argument("--send", action="store_true"); p.add_argument("--reconfigure", action="store_true")
    p = sub.add_parser("check"); p.add_argument("file")
    p = sub.add_parser("close"); p.add_argument("file"); p.add_argument("--send", action="store_true")
    p = sub.add_parser("script"); p.add_argument("file"); p.add_argument("-o", "--out")
    a = ap.parse_args()
    try:
        wins = load_layout(Path(a.file), das_dir())
        for w in wins:
            for _, t in all_payloads(w):
                screen(t)
    except LayoutError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 1
    if a.cmd == "check":
        return cmd_check(wins)
    if a.cmd == "close":
        return cmd_close(wins, a.send)
    if a.cmd == "script":
        text = standalone(wins)
        if a.out:
            Path(a.out).write_text(text)
            print(f"wrote {a.out}", file=sys.stderr)
        else:
            sys.stdout.write(text)
        return 0
    if not a.send:
        for w in wins:
            for win, t in all_payloads(w):
                print(f"SCRIPT {win} {t}")
        print(f"dry run: {len(wins)} window(s); add --send to build them", file=sys.stderr)
        return 0
    return send(wins, a.reconfigure)


if __name__ == "__main__":
    sys.exit(main())
