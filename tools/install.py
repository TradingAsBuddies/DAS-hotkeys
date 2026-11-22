#!/usr/bin/env python3
"""Build the montage3 hotkey file and button panels and copy them into a DAS install.

    install.py            dry run: say what would be built and copied, write nothing to DAS
    install.py --write    back up what is there, then copy
    install.py --list     the DAS folders found on this machine

Runs the same on Windows and Linux (WSL). The DAS folder comes only from
install.local.json, which you make by copying install.example.json and setting das_dir.
The installer lists the folders it can find, and marks the one that is running, but it
never chooses: a machine can hold several installs and only the operator knows which
desk these hotkeys belong on.

What it cannot do: load the files inside DAS. After --write, Setup > Hotkey > Load the
hotkey file, and load each .cbf from that montage's button menu. It installs no account
ID, R value or chart setting: those are yours (scripts/rconfig.example.das, tools/gen_cst.py).
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import re
import shutil
import string
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_htk  # noqa: E402
from das_script_test import running_das, win_to_wsl  # noqa: E402

REPO = gen_htk.REPO
EXAMPLE = REPO / "install.example.json"
LOCAL = REPO / "install.local.json"
STAGE = REPO / "scripts" / "local"
FILE_OK = re.compile(r"^[A-Za-z0-9_. -]{1,60}\.htk$")


class InstallError(Exception):
    pass


def to_local(path: str) -> Path:
    """A Windows path as this Python can open it: unchanged on Windows, /mnt/c/... under WSL."""
    return Path(path) if os.name == "nt" else win_to_wsl(path)


def load_config(path: Path = LOCAL) -> dict:
    if not path.exists():
        raise InstallError(
            f"no {path.name}. Copy {EXAMPLE.name} to {path.name} and set das_dir to your DAS folder.")
    try:
        cfg = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise InstallError(f"{path.name} is not valid JSON: {e}") from e
    for key in ("das_dir", "manifest", "hotkey_file"):
        if not cfg.get(key):
            raise InstallError(f"{path.name}: {key} is missing or empty")
    for key in ("hotkey_file", "base_hotkeys"):
        if cfg.get(key) and not FILE_OK.match(cfg[key]):
            raise InstallError(f"{path.name}: {key} must be a bare file name ending .htk")
    return cfg


def check_das_dir(d: Path) -> None:
    if not d.is_dir():
        raise InstallError(f"das_dir {d} is not a folder")
    if not (d / "Config.cfg").exists():
        raise InstallError(f"das_dir {d} has no Config.cfg, so it is not a DAS install")


def candidates() -> list[Path]:
    """Every top-level folder on a fixed drive that holds a Config.cfg."""
    if os.name == "nt":
        roots = [Path(f"{c}:\\") for c in string.ascii_uppercase if Path(f"{c}:\\").exists()]
    else:
        roots = sorted(p for p in Path("/mnt").glob("[a-z]") if p.is_dir())
    found = []
    for root in roots:
        try:
            found += sorted(p.parent for p in root.glob("*/Config.cfg"))
        except OSError:
            continue
    return found


def running_dir() -> Path | None:
    run = running_das()
    if not run or not run[0]:
        return None
    return to_local(run[0].rsplit("\\", 1)[0])


def same(a: Path, b: Path) -> bool:
    return a.as_posix().rstrip("/").lower() == b.as_posix().rstrip("/").lower()


def print_candidates() -> None:
    found, live = candidates(), running_dir()
    if not found:
        print("No folder with a Config.cfg was found at the top of any drive.")
        return
    print("DAS folders found (the installer does not choose between them):")
    for p in found:
        print(f"   {p}" + ("   <- DAS is running from this one" if live and same(p, live) else ""))


def quiet(fn, args) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(args)
    return rc, buf.getvalue()


def build(cfg: dict, das: Path) -> tuple[list[Path], str]:
    """Stage the hotkey file and the panels under scripts/local/. Returns (files, build stamp)."""
    manifest = REPO / cfg["manifest"]
    if not manifest.exists():
        raise InstallError(f"manifest {manifest} not found")
    base = cfg.get("base_hotkeys") or ""
    base_path = das / base if base else None
    if base_path and not base_path.exists():
        raise InstallError(
            f"base_hotkeys {base_path} not found. Set base_hotkeys to the hotkey file you use "
            'now, or to "" if you have none to keep.')
    out = STAGE / cfg["hotkey_file"]
    stamp = gen_htk.build_stamp()
    rc, text = quiet(gen_htk.cmd_build, SimpleNamespace(
        manifest=str(manifest), out=str(out), base=str(base_path) if base_path else None,
        stamp=stamp))
    if rc:
        raise InstallError("the hotkey file did not build:\n" + text)
    panels = SimpleNamespace(manifest=str(manifest))
    rc, text = quiet(gen_htk.cmd_cbf, panels)
    if rc:
        raise InstallError("the button panels did not build:\n" + text)
    return [out] + panels.written, stamp


def install(cfg: dict, write: bool, now: datetime | None = None) -> int:
    das = to_local(cfg["das_dir"])
    check_das_dir(das)
    files, stamp = build(cfg, das)
    live = running_dir()
    print(f"DAS folder   {das}")
    if live and not same(das, live):
        print(f"note         DAS is running from {live}, not this folder")
    if not cfg.get("base_hotkeys"):
        print("note         no base_hotkeys: loading this file may replace every hotkey you have")
    backup = STAGE / "backup" / (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    for f in files:
        dest = das / f.name
        verb = "replace" if dest.exists() else "add"
        print(f"{verb:12} {dest.name}  ({f.stat().st_size} bytes)")
        if write:
            if dest.exists():
                backup.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, backup / dest.name)
            shutil.copyfile(f, dest)
    if not write:
        print("\nDry run: nothing was copied. Run again with --write.")
        return 0
    if backup.exists():
        print(f"backups      {backup}")
    print(f"\nCopied. In DAS: Setup > Hotkey > Load > {cfg['hotkey_file']}, then OK.")
    print("Load each .cbf from its montage's button menu (only when the buttons changed).")
    print(f"Then press PING: it should read PING {stamp[-8:-3]} (build {stamp}).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--write", action="store_true", help="copy into the DAS folder (default: dry run)")
    ap.add_argument("--list", action="store_true", help="list the DAS folders found, then stop")
    ap.add_argument("--config", default=str(LOCAL), help="config file (default: install.local.json)")
    a = ap.parse_args(argv)
    if a.list:
        print_candidates()
        return 0
    try:
        return install(load_config(Path(a.config)), a.write)
    except InstallError as e:
        print(f"STOPPED: {e}\n")
        print_candidates()
        return 2


if __name__ == "__main__":
    sys.exit(main())
