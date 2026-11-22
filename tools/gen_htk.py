#!/usr/bin/env python3
"""Read, write and generate DAS hotkey files (`*.htk`).

    gen_htk.py selftest  FILE.htk ...          parse and rewrite; must be byte-identical
    gen_htk.py list      FILE.htk              key and name of each record, never the script
    gen_htk.py build     MANIFEST.json [-o OUT] [--base FILE.htk]

The format, read from the live install on 2026-11-19 (roadmap item 4; spec
docs/spec/features/002-hotkey-dashboard/plan.md). Latin-1 text, CRLF, one record per hotkey:

    Key:Name:Script               short form, one line
    Key:Name:~ NNN:Script         length-prefixed form, wrapped over several lines

- An empty Key is a hotkey with no key bound. ExecHotkey("Name") can still run it.
- Name cannot contain ':'. Script may, because the record splits on the first two.
- Inside a prefixed record, '~', control characters and every byte above 0x7E are stored
  as ~XX (upper-case hex): a typed line break is ~0D~0A, an em dash is ~E2~80~94 (its
  UTF-8 bytes). Each escape counts as ONE character of NNN.
- NNN counts script characters. The CRLFs that DAS inserts to wrap the record are not
  counted. A wrap follows the token that brings the line to 51 or more raw characters,
  where a plain character is 1 raw character and an escape is 3. An escape is never split.
- Observed: every script of 95 characters or fewer with no line break uses the short
  form. Every script of 124 or more uses the prefixed form. Nothing in between was seen,
  so `build` uses the prefixed form for anything over 95 characters or or needing an escape.

`selftest` reproduces all eight .htk files in both installs byte for byte (2026-11-19),
including a 2,744-character script with ~7E and UTF-8 escapes. Still UNVERIFIED (plan.md L3, L4): that DAS loads a generated file, and
that ExecHotkey runs a no-key record from a button.

A live .htk holds ACCOUNT= strings (CONSTITUTION 16), so `list` and `selftest` print no
script text. `build` writes under scripts/local/ by default, which is gitignored, and
refuses a path git would track.

Manifest (JSON):

    {"hotkeys": [
      {"name": "dash.baf_long", "key": "", "source": "scripts/40-bracket-at-fill.das",
       "block": "A", "button": {"window": "montage1", "label": "BAF LONG"}}
    ]}

`block` picks the text after a `// BLOCK A ...` banner, up to the next banner. Every
selected source is linted first with the static checks of `das_script_test.py check`.
Comments and blank lines are removed. Scripts keep their line breaks.
"""

from __future__ import annotations

import argparse
import json
import re
import struct
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WRAP = 51            # raw characters per physical line before DAS wraps
SHORT_MAX = 95       # longest short-form script seen in a live file
HEXESC = re.compile(r"~([0-9A-F]{2})")


def esc(ch: str) -> str:
    """One logical character as stored inside a prefixed record."""
    o = ord(ch)
    return f"~{o:02X}" if ch == "~" or o < 0x20 or o > 0x7E else ch
CRLF = "\r\n"


class HtkError(ValueError):
    pass


@dataclass
class Record:
    key: str
    name: str
    script: str          # logical text: a typed line break is "\r\n"
    prefixed: bool


# ── format ───────────────────────────────────────────────────────────────────

HEAD = re.compile(r"([^:\r\n]*):([^:\r\n]*):~ (\d+):")


def parse(data: bytes) -> list[Record]:
    t = data.decode("latin-1")
    out: list[Record] = []
    i = 0
    while i < len(t):
        m = HEAD.match(t, i)
        if m:
            need, j, chars = int(m.group(3)), m.end(), []
            while len(chars) < need:
                if t.startswith(CRLF, j):
                    j += 2
                elif (e := HEXESC.match(t, j)):
                    chars.append(chr(int(e.group(1), 16)))
                    j += 3
                elif j >= len(t):
                    raise HtkError(f"record {len(out) + 1}: file ends inside a {need}-character script")
                else:
                    chars.append(t[j])
                    j += 1
            if not t.startswith(CRLF, j):
                raise HtkError(f"record {len(out) + 1}: no CRLF after {need} characters")
            out.append(Record(m.group(1), m.group(2), "".join(chars), True))
            i = j + 2
        else:
            j = t.find(CRLF, i)
            if j < 0:
                raise HtkError(f"record {len(out) + 1}: no closing CRLF")
            parts = t[i:j].split(":", 2)
            if len(parts) != 3:
                raise HtkError(f"record {len(out) + 1}: fewer than two ':'")
            out.append(Record(parts[0], parts[1], parts[2], False))
            i = j + 2
    return out


def encode(r: Record) -> str:
    if not r.prefixed:
        if "\r" in r.script or "\n" in r.script:
            raise HtkError(f"{r.name}: a short-form record cannot hold a line break")
        return f"{r.key}:{r.name}:{r.script}{CRLF}"
    lines, cur, n = [], "", 0
    for k, ch in enumerate(r.script):
        tok = esc(ch)
        cur += tok
        n += len(tok)
        if n >= WRAP and k < len(r.script) - 1:
            lines.append(cur)
            cur, n = "", 0
    lines.append(cur)
    return f"{r.key}:{r.name}:~ {len(r.script)}:" + CRLF.join(lines) + CRLF


def serialize(records: list[Record]) -> bytes:
    return "".join(encode(r) for r in records).encode("latin-1")


def make_record(key: str, name: str, script: str) -> Record:
    for field, v in (("key", key), ("name", name)):
        if ":" in v or "\r" in v or "\n" in v:
            raise HtkError(f"{field} {v!r}: ':' and line breaks are not allowed")
    if not script.isascii():
        raise HtkError(f"{name}: non-ASCII character in script; keep sources ASCII")
    long = len(script) > SHORT_MAX or any(esc(c) != c for c in script)
    return Record(key, name, script, long)


# ── source preparation ───────────────────────────────────────────────────────

BANNER = re.compile(r"^//\s*=+\s*$")
BLOCK = re.compile(r"^//\s*BLOCK\s+(\w+)\b")


def select_block(src: str, block: str | None) -> str:
    if block is None:
        return src
    lines = src.splitlines()
    for i, line in enumerate(lines):
        m = BLOCK.match(line.strip())
        if m and m.group(1) == block:
            start = i + 1
            if start < len(lines) and BANNER.match(lines[start].strip()):
                start += 1
            end = start
            while end < len(lines):
                if BANNER.match(lines[end].strip()) and end + 1 < len(lines) \
                        and BLOCK.match(lines[end + 1].strip()):
                    break
                end += 1
            return "\n".join(lines[start:end])
    raise HtkError(f"no '// BLOCK {block}' banner")


def strip_comments(src: str) -> str:
    """Remove // and /* */ comments outside strings, trailing space and blank lines."""
    out, i, in_str, in_block = [], 0, False, False
    while i < len(src):
        ch = src[i]
        if in_block:
            if src.startswith("*/", i):
                in_block = False
                i += 2
            else:
                if ch == "\n":
                    out.append("\n")
                i += 1
            continue
        if in_str:
            out.append(ch)
            if ch == "\\" and i + 1 < len(src):
                out.append(src[i + 1])
                i += 1
            elif ch == '"' or ch == "\n":
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
        elif src.startswith("//", i):
            while i < len(src) and src[i] != "\n":
                i += 1
            continue
        elif src.startswith("/*", i):
            in_block = True
            i += 2
            continue
        out.append(ch)
        i += 1
    kept = [ln.rstrip() for ln in "".join(out).splitlines()]
    return "\r\n".join(ln for ln in kept if ln.strip())


def lint(text: str) -> list[str]:
    """The static checks of das_script_test.py check, on the selected text."""
    sys.path.insert(0, str(REPO / "tools"))
    from das_script_test import mixed_logic   # noqa: E402  (stdlib-only module)
    problems = []
    for i, line in enumerate(text.splitlines(), 1):
        if "'" in line.split("//", 1)[0]:
            problems.append(f"{i}: single quote in code")
    for i in mixed_logic(text.splitlines()):
        problems.append(f"{i}: && and || mixed without parentheses")
    return problems


# ── commands ─────────────────────────────────────────────────────────────────

def git_tracks(path: Path) -> bool:
    """True when git would track this path (not ignored)."""
    r = subprocess.run(["git", "-C", str(REPO), "check-ignore", "-q", str(path)],
                       capture_output=True)
    return r.returncode != 0


def cmd_selftest(a) -> int:
    bad = 0
    for f in a.files:
        data = Path(f).read_bytes()
        try:
            recs = parse(data)
        except HtkError as e:
            print(f"FAIL  {f}: {e}")
            bad += 1
            continue
        again = serialize(recs)
        same = again == data
        n_pref = sum(r.prefixed for r in recs)
        print(f"{'ok  ' if same else 'FAIL'}  {Path(f).name}: {len(recs)} records, "
              f"{n_pref} prefixed, {len(data)} bytes{'' if same else ', rewrite differs'}")
        if not same:
            k = next(i for i, (x, y) in enumerate(zip(data, again + b"\0" * len(data))) if x != y)
            print(f"      first difference at byte {k}")
            bad += 1
    return 1 if bad else 0


def cmd_list(a) -> int:
    for i, r in enumerate(parse(Path(a.file).read_bytes()), 1):
        print(f"{i:3}  {r.key or '(no key)':16} {'~' if r.prefixed else ' '} {len(r.script):5}  {r.name}")
    return 0


BUILD_TOKEN = "@BUILD@"


def build_stamp() -> str:
    """When this .htk was built, in US Eastern time, the clock the DAS log uses."""
    from datetime import datetime
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    try:
        now = datetime.now(ZoneInfo("America/New_York"))
    except ZoneInfoNotFoundError:      # Windows Python without the tzdata package
        now = datetime.now()           # local time: still unique per build
    return now.strftime("%m-%d %H:%M:%S")


def stamp_build(body: str, stamp: str) -> str:
    """Replace @BUILD@ in a script. A loaded .htk is invisible from outside DAS, and a
    load that did not take cost several wrong test runs on 2026-11-21; a script that
    logs its own build time proves which version DAS is running."""
    # @BUILDHM@ is the short form (HH:MM) for a button face, which is only 100 wide
    return body.replace("@BUILDHM@", stamp[-8:-3]).replace(BUILD_TOKEN, stamp)


def cmd_build(a) -> int:
    man = json.loads(Path(a.manifest).read_text())
    out = Path(a.out) if a.out else REPO / "scripts" / "local" / (Path(a.manifest).stem + ".htk")
    out = out if out.is_absolute() else Path.cwd() / out
    if git_tracks(out):
        print(f"REFUSED: git would track {out}; write under scripts/local/")
        return 2
    records, problems, buttons = [], [], []
    stamp = getattr(a, "stamp", None) or build_stamp()   # a caller may supply its own
    print(f"build stamp {stamp} (PING logs and shows it once this file is loaded)")
    for h in man["hotkeys"]:
        src = (REPO / h["source"]).read_text()
        try:
            body = stamp_build(select_block(src, h.get("block")), stamp)
        except HtkError as e:
            problems.append(f"{h['name']}: {h['source']}: {e}")
            continue
        for p in lint(body):
            problems.append(f"{h['name']}: {h['source']} block line {p}")
        try:
            records.append(make_record(h.get("key", ""), h["name"], strip_comments(body)))
        except HtkError as e:
            problems.append(str(e))
        if "button" in h:
            buttons.append((h["button"]["window"], h["button"]["label"], h["name"]))
    names = [r.name for r in records]
    for n in sorted({n for n in names if names.count(n) > 1}):
        problems.append(f"{n}: name used twice")
    if problems:
        print(f"NOT WRITTEN: {len(problems)} problem(s)")
        for p in problems:
            print("   ", p)
        return 1
    if a.base:
        base = parse(Path(a.base).read_bytes())
        mine = set(names)
        kept = [r for r in base if r.name not in mine]
        print(f"base {a.base}: kept {len(kept)} record(s), replaced {len(base) - len(kept)}")
        records = kept + records
    data = serialize(records)
    if parse(data) != records:
        print("NOT WRITTEN: the output does not parse back to the same records")
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"wrote {out}: {len(records)} record(s), {len(data)} bytes")
    if buttons:
        print("\nButtons to create by hand (once per template):")
        for win, label, name in buttons:
            print(f"  {win:10} {label:14} script: ExecHotkey(\"{name}\");")
    print("\nLoad: Setup > Hotkey > Load. UNVERIFIED that DAS accepts it (plan.md L3).")
    if not a.base:
        print("Without --base, loading this file may replace every existing hotkey.")
    return 0


# ── .cbf hot-button panels ──────────────────────────────────────────────────
# Format read from a DAS 5.8.4.8 export (2026-11-19), byte-identical on rewrite:
#   "cbffile\0", u32 36, u32 len(file)-20, u32 0, u32 count,
#   per button: u32 0, name\0, text\0, script\0, u32 type 0, u32 100,
#               u32 text colour, u32 background colour (Windows BGR: 0x0000FF is red),
#   tail: 00, u32 20, u32 40 (meaning untested [I]).
# Loading one is a UI step (the button window's menu); no script command is documented.

CBF_MAGIC = b"cbffile\0"
CBF_TAIL = b"\x00" + struct.pack("<II", 20, 40)
COLORREF = {"black": 0x000000, "white": 0xFFFFFF, "red": 0x0000FF, "green": 0x00FF00,
            "blue": 0xFF0000, "yellow": 0x00FFFF, "gray": 0xC8C8C8, "grey": 0xC8C8C8}


@dataclass
class Button:
    name: str
    text: str
    script: str = ""
    fg: int = 0x000000
    bg: int = 0xC8C8C8
    kind: int = 0
    width: int = 100


def parse_cbf(data: bytes) -> tuple[list[Button], bytes]:
    if not data.startswith(CBF_MAGIC):
        raise HtkError("not a cbffile")
    v, ln, z, n = struct.unpack_from("<4I", data, 8)
    if (v, ln) != (36, len(data) - 20) or z not in (0, 8):
        raise HtkError(f"unexpected cbf header {v} {ln} {z}")
    o, out = 24, []
    def cstr(o):
        e = data.index(b"\0", o)
        return data[o:e].decode("latin-1"), e + 1
    for _ in range(n):
        (lead,) = struct.unpack_from("<I", data, o)
        if lead != 0:
            raise HtkError(f"unexpected button lead {lead} at {o}")
        name, o = cstr(o + 4)
        text, o = cstr(o)
        script, o = cstr(o)
        kind, width, fg, bg = struct.unpack_from("<4I", data, o)
        o += 16
        out.append(Button(name, text, script, fg, bg, kind, width))
    if z != cbf_rows_flag(out):
        raise HtkError(f"cbf header flag {z} does not match the button rows")
    return out, data[o:]


def cbf_rows_flag(buttons: list[Button]) -> int:
    """Third header field. 0 in a one-row export, 8 in the operator's two-row export
    (2026-11-21), where the second-row button also had kind 1. So `kind` is the row,
    and only rows 0 and 1 have been seen."""
    rows = {b.kind for b in buttons}
    if not rows <= {0, 1}:
        raise HtkError("only button rows 0 and 1 have been seen in a DAS export")
    return 8 if 1 in rows else 0


def serialize_cbf(buttons: list[Button], tail: bytes = CBF_TAIL) -> bytes:
    body = b"".join(struct.pack("<I", 0) + b"\0".join(x.encode("latin-1") for x in
                    (b.name, b.text, b.script)) + b"\0" +
                    struct.pack("<4I", b.kind, b.width, b.fg, b.bg) for b in buttons) + tail
    return CBF_MAGIC + struct.pack("<4I", 36, len(body) + 4, cbf_rows_flag(buttons),
                                   len(buttons)) + body


def make_button(name: str, text: str, script: str = "", fg: str = "black",
                bg: str = "gray", row: int = 0) -> Button:
    if row not in (0, 1):
        raise HtkError(f"button {name}: row must be 0 or 1")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,31}", name):
        raise HtkError(f"button name {name!r}: letters, digits, underscore")
    for what, v in (("text", text), ("script", script)):
        if "\0" in v or any(ord(c) > 0x7E or (ord(c) < 0x20) for c in v):
            raise HtkError(f"button {name}: {what} must be plain ASCII on one line")
    try:
        return Button(name, text, script, COLORREF[fg.lower()], COLORREF[bg.lower()], row)
    except KeyError as e:
        raise HtkError(f"button {name}: colour {e} not in {sorted(COLORREF)}")


def cmd_cbf(a) -> int:
    """One .cbf per window from the manifest's `button` entries, plus its `panels` extras."""
    man = json.loads(Path(a.manifest).read_text())
    panels: dict[str, list[Button]] = {}
    try:
        for extra in man.get("panels", []):
            panels.setdefault(extra["window"], []).append(make_button(
                extra["name"], extra.get("text", extra["name"]), extra.get("script", ""),
                extra.get("fg", "black"), extra.get("bg", "gray"), extra.get("row", 0)))
        for h in man["hotkeys"]:
            bt = h.get("button")
            if bt:
                panels.setdefault(bt["window"], []).append(make_button(
                    bt.get("name", re.sub(r"\W", "_", h["name"])), bt["label"],
                    f'ExecHotkey("{h["name"]}");', bt.get("fg", "black"), bt.get("bg", "gray"),
                    bt.get("row", 0)))
    except (HtkError, KeyError) as e:
        print(f"NOT WRITTEN: {e}")
        return 1
    outdir = REPO / "scripts" / "local"
    a.written = []                      # for callers: the panel files this run wrote
    for win, btns in panels.items():
        names = [b.name.lower() for b in btns]
        if len(set(names)) != len(names):
            print(f"NOT WRITTEN: {win}: button name used twice")
            return 1
        out = outdir / f"{Path(a.manifest).stem}-{win}.cbf"
        data = serialize_cbf(btns)
        assert parse_cbf(data)[0] == btns
        out.write_bytes(data)
        a.written.append(out)
        print(f"wrote {out}: {len(btns)} button(s) for {win}")
        for b in btns:
            print(f"   row {b.kind}  {b.name:16} {b.text!r:20} {b.script}")
    print("Load: the button window's menu on that montage. UNVERIFIED that DAS loads a "
          "generated file.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("selftest", help="parse and rewrite each file; must be byte-identical")
    p.add_argument("files", nargs="+")
    p = sub.add_parser("list", help="key and name of each record (no script text)")
    p.add_argument("file")
    p = sub.add_parser("cbf", help="write .cbf hot-button panels from a manifest")
    p.add_argument("manifest")
    p = sub.add_parser("build", help="write a .htk from a manifest")
    p.add_argument("manifest")
    p.add_argument("-o", "--out")
    p.add_argument("--base", help="existing .htk to keep; same-name records are replaced")
    a = ap.parse_args()
    return {"selftest": cmd_selftest, "list": cmd_list, "build": cmd_build,
            "cbf": cmd_cbf}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
