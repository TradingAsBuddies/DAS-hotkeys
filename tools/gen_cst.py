#!/usr/bin/env python3
"""Make DAS chart settings (`*.cst`) by patching a copy of one you saved.

    gen_cst.py list  FILE.cst                        the studies in a file, by number
    gen_cst.py make  TEMPLATE.cst [--ma 2:sma:34] [--name 1:EMA9] [-o OUT] [--install]

A .cst is what Save Screen Setting writes and `LoadSetting X.cst` loads: every study,
pane and colour of a chart. It is binary and mostly undecoded. What is known, from saved
files and paper loads on DAS 5.8.4.8 (2026-11-21):

- a study record starts u32 LEN, u32 2, a 20-byte TYPE ("Moving Average", "Price",
  NUL-padded), then the study's NAME as a NUL-terminated string. The name defaults to
  the class ("StudyMovingAvg"); it is what Study Config renames, and what GetStudyVal()
  is given [V 2026-11-21: GetStudyVal("SMA50") read a generated name].
- renaming in Study Config ("StudyMovingAvg" -> "EMA9") changed only that string and
  LEN, by the length difference (107 -> 97). No outer length moved [V, operator's
  t3-rename-manual.cst against t1-control.cst].
- after a moving average's name come a u32 period and a u32 type: 2 = EMA, 0 = SMA
  [V by diff of two saved files, and t2: EMA 21 -> SMA 50 loaded and drew].
- writing a name into the TYPE field made DAS drop the study silently [V, t3]. The tool
  never touches TYPE.
- a generated file with both MAs patched and renamed (t5: EMA9 ema 9, SMA50 sma 50)
  loaded, drew, and Study Config listed both names and parameters [V 2026-11-21].

Studies that are not in the template (VWAP, ATR) cannot be added: save a template that
has them.

A saved .cst also holds an account ID and the chart's symbol history (CONSTITUTION 16).
`list` prints neither, `make` writes under the gitignored scripts/local/ by default, and
--install copies into the DAS install, never into the repo.
"""

from __future__ import annotations

import argparse
import re
import shutil
import struct
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from das_script_test import das_dir  # noqa: E402
from gen_htk import REPO, git_tracks  # noqa: E402

MAGIC = b"ChartScreenFile"
TYPE_LEN = 20
MARK = b"\x02\x00\x00\x00"          # the u32 2 after LEN
MA_TYPE = "Moving Average"
MA_TYPES = {"sma": 0, "ema": 2}     # only the two seen in saved files
NAME_OK = re.compile(r"^[A-Za-z0-9 ()._-]{1,31}$")
OUT_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,60}\.cst$")


class CstError(ValueError):
    pass


@dataclass
class Study:
    number: int          # 1-based, in file order
    len_at: int          # offset of the u32 LEN
    type: str
    name: str
    name_at: int         # offset of the name string
    params_at: int       # offset just after the name's NUL
    period: int | None = None
    ma_type: int | None = None


def printable(b: bytes) -> bool:
    return bool(b) and all(32 <= c < 127 for c in b)


def parse(data: bytes) -> list[Study]:
    if not data.startswith(MAGIC):
        raise CstError("not a chart setting file (no ChartScreenFile header)")
    out, i = [], 4
    while (i := data.find(MARK, i)) >= 0:
        t_at, n_at = i + 4, i + 4 + TYPE_LEN
        field = data[t_at:n_at]
        typ = field.split(b"\0", 1)[0]
        end = data.find(b"\0", n_at)
        ok = (printable(typ) and not field[len(typ):].strip(b"\0") and end > n_at
              and printable(data[n_at:end]) and typ[:1].isalpha())
        if ok:
            ln = struct.unpack_from("<I", data, i - 4)[0]
            ok = TYPE_LEN + (end - n_at) < ln < 4096
        if not ok:
            i += 1
            continue
        s = Study(len(out) + 1, i - 4, typ.decode(), data[n_at:end].decode(), n_at, end + 1)
        if s.type == MA_TYPE:
            s.period, s.ma_type = struct.unpack_from("<II", data, s.params_at)
        out.append(s)
        i = end + 1
    return out


def type_name(t: int | None) -> str:
    return {v: k for k, v in MA_TYPES.items()}.get(t, f"type{t}")


def parse_ma(spec: str) -> tuple[int, int, int]:
    m = re.fullmatch(r"(\d{1,2}):(sma|ema):(\d{1,3})", spec.lower())
    if not m:
        raise CstError(f"--ma {spec!r}: use N:sma|ema:PERIOD, e.g. 2:sma:34")
    n, t, p = int(m[1]), MA_TYPES[m[2]], int(m[3])
    if not 1 <= p <= 500:
        raise CstError(f"--ma {spec!r}: period must be 1..500")
    return n, t, p


def parse_name(spec: str) -> tuple[int, str]:
    n, _, name = spec.partition(":")
    if not n.isdigit() or not NAME_OK.match(name):
        raise CstError(f"--name {spec!r}: use N:NAME, 1-31 of letters, digits, space ( ) . _ -")
    return int(n), name


def patch(data: bytes, mas=(), names=()) -> bytes:
    studies = {s.number: s for s in parse(data)}
    buf = bytearray(data)
    for n, t, p in mas:                       # in place, before any length changes
        s = studies.get(n)
        if s is None or s.type != MA_TYPE:
            raise CstError(f"study {n} is not a moving average (see `list`)")
        struct.pack_into("<II", buf, s.params_at, p, t)
    taken = {s.name for s in studies.values()}
    for n, name in sorted(names, reverse=True):   # last first, so earlier offsets hold
        s = studies.get(n)
        if s is None:
            raise CstError(f"no study {n} (see `list`)")
        if name != s.name and name in taken:
            raise CstError(f"name {name!r} is already used in this file")
        delta = len(name) - len(s.name)
        buf[s.name_at:s.params_at - 1] = name.encode()
        ln = struct.unpack_from("<I", buf, s.len_at)[0]
        struct.pack_into("<I", buf, s.len_at, ln + delta)
        taken.add(name)
    return bytes(buf)


def cmd_list(a) -> int:
    for s in parse(Path(a.file).read_bytes()):
        extra = f"  {type_name(s.ma_type)} {s.period}" if s.period is not None else ""
        print(f"{s.number:3}  {s.type:16} {s.name:20}{extra}")
    return 0


def resolve_template(t: str) -> Path:
    p = Path(t)
    return p if p.exists() or "/" in t else das_dir() / t


def cmd_make(a) -> int:
    try:
        src = resolve_template(a.template)
        data = patch(src.read_bytes(), [parse_ma(x) for x in a.ma], [parse_name(x) for x in a.name])
    except (CstError, OSError) as e:
        print(f"REFUSED: {e}")
        return 2
    out = Path(a.out) if a.out else REPO / "scripts" / "local" / src.name
    out = out if out.is_absolute() else Path.cwd() / out
    if not OUT_NAME.match(out.name):
        print(f"REFUSED: output name must be a bare NAME.cst: {out.name}")
        return 2
    if git_tracks(out):
        print(f"REFUSED: git would track {out}; a .cst holds an account ID. Write under scripts/local/")
        return 2
    if out.resolve() == src.resolve():
        print("REFUSED: output would overwrite the template")
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    print(f"wrote {out} ({len(data)} bytes)")
    for s in parse(data):
        if s.period is not None:
            print(f"  {s.number}: {s.name} {type_name(s.ma_type)} {s.period}")
    if a.install:
        dest = das_dir() / out.name
        if dest.exists() and not a.force:
            print(f"REFUSED: {dest} exists; pass --force to replace it")
            return 2
        shutil.copyfile(out, dest)
        print(f"installed {dest}  ->  LoadSetting {out.name}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list", help="the studies in a .cst")
    p.add_argument("file")
    p = sub.add_parser("make", help="copy a .cst, patch moving averages and study names")
    p.add_argument("template", help="a saved .cst; a bare name is looked up in the DAS install")
    p.add_argument("--ma", action="append", default=[], help="N:sma|ema:PERIOD")
    p.add_argument("--name", action="append", default=[], help="N:NAME, the name GetStudyVal() uses")
    p.add_argument("-o", "--out")
    p.add_argument("--install", action="store_true", help="also copy into the DAS install")
    p.add_argument("--force", action="store_true", help="with --install, replace an existing file")
    a = ap.parse_args(argv)
    return {"list": cmd_list, "make": cmd_make}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
