#!/usr/bin/env python3
"""DAS hotkey-script test harness over the CMD API.

Inject hotkey-script text into a named DAS window, read the result back from
DAS's own log file, and clear any script-error dialog that would otherwise
freeze the API. Everything here was verified live on 2026-09-24; see
docs/CMD-API-TESTING.md for the evidence.

    das_script_test.py exists montage1 hidden_chart1
    das_script_test.py run GLOBALSCRIPT 'MsgLog("hi");'
    das_script_test.py eval montage1 '$w.BID'         # prints the value
    das_script_test.py study hidden_chart1 atr        # GetStudyVal by name
    das_script_test.py check scripts/00-fl-desktop-load.das --live
    das_script_test.py bars SPY --minutes 30
    das_script_test.py dismiss

Connection facts (CLAUDE.md): DAS binds loopback; host/port come from
~/.claude/.env (DAS_HOST, DAS_PORT, DAS_USER, DAS_PASSWORD, DAS_ACCOUNT) with
inline " #" comments stripped. The port is cross-checked against DAS's own
Config.cfg so drift is reported, never guessed. Login is WATCH mode (flag 1),
which blocks the socket's own NEWORDER command and nothing else: text injected
with SCRIPT runs inside DAS under whatever account DAS itself is logged into.
The only order guard for injected text is the refusal list in cmd_check and
your own discipline in `run`. Never inject order code outside the paper
round trip described in docs/CMD-API-TESTING.md.
"""

from __future__ import annotations

import argparse
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ENV_FILE = Path.home() / ".claude" / ".env"
WIN_PY = "/mnt/c/Python314/python.exe"          # has pywinauto; 3.13 does not
DEFAULT_DAS_DIR = "/mnt/c/Cobra Trading_x64"    # DasTrader64.exe lives here
PAPER_ACCOUNT = "TR4425"                        # the only account this tool logs into


class NoConnection(RuntimeError):
    """DAS CMD API unreachable. Distinct from 'no data'."""


# ── environment ──────────────────────────────────────────────────────────────

def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if not ENV_FILE.exists():
        return env
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        # split only on whitespace-preceded " #" so a '#' inside a password survives
        val = val.split(" #")[0].split("\t#")[0].strip().strip("'\"")
        env[key.strip().removeprefix("export ")] = val
    return env


def das_dir() -> Path:
    return Path(os.environ.get("DAS_DIR", DEFAULT_DAS_DIR))


def config_port() -> int | None:
    """Port DAS itself is configured to listen on: CMDAPI:PORT:<n> in Config.cfg."""
    cfg = das_dir() / "Config.cfg"
    if not cfg.exists():
        return None
    m = re.search(r"^CMDAPI:PORT:(\d+)", cfg.read_text(errors="replace"), re.M)
    return int(m.group(1)) if m else None


def log_file(day: datetime | None = None) -> Path:
    """DAS writes LOG/YYMMDDLog.txt: every CMD API command (CMDAPILog), every
    MsgLog (Log), every script error (Error, stamped when its dialog closes)."""
    logs = sorted((das_dir() / "LOG").glob("*Log.txt"), key=lambda p: p.stat().st_mtime)
    if logs:
        return logs[-1]                      # newest, whatever DAS thinks the date is
    day = day or datetime.now()
    return das_dir() / "LOG" / f"{day:%y%m%d}Log.txt"


# ── socket ───────────────────────────────────────────────────────────────────

class DAS:
    def __init__(self, env: dict[str, str] | None = None):
        self.env = env or load_env()
        self.host = self.env.get("DAS_HOST", "127.0.0.1")
        try:
            self.port = int(self.env["DAS_PORT"])
        except (KeyError, ValueError):
            raise NoConnection("DAS_PORT missing from ~/.claude/.env; do not guess it")
        cp = config_port()
        if cp is not None and cp != self.port:
            print(f"WARNING: .env DAS_PORT={self.port} but Config.cfg says {cp}; "
                  f"DAS is listening on {cp}", file=sys.stderr)
        self.sock: socket.socket | None = None
        self.last_errors: list[str] = []

    def connect(self) -> "DAS":
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=5)
        except OSError as exc:
            raise NoConnection(f"DAS CMD API unreachable at {self.host}:{self.port}: {exc}")
        self.sock.settimeout(1.0)
        user, pw, acct = (self.env.get(k) for k in ("DAS_USER", "DAS_PASSWORD", "DAS_ACCOUNT"))
        if not all([user, pw, acct]):
            raise NoConnection("DAS_USER / DAS_PASSWORD / DAS_ACCOUNT missing from ~/.claude/.env")
        allowed = os.environ.get("DAS_TEST_ACCOUNT", PAPER_ACCOUNT)
        if acct != allowed:
            raise NoConnection(f"DAS_ACCOUNT={acct} is not the paper account {allowed}; "
                               f"set DAS_TEST_ACCOUNT to override deliberately")
        self.send(f"LOGIN {user} {pw} {acct} 1")          # 1 = watch mode
        text = self.drain(2.5)
        if "LOGIN SUCCESSED" not in text:
            hint = "" if text.strip() else " (empty reply: a ScriptError dialog may be freezing DAS; run `dismiss`)"
            raise NoConnection("DAS refused login: " + text.strip()[:120] + hint)
        return self

    def send(self, cmd: str) -> None:
        assert self.sock
        self.sock.sendall((cmd + "\r\n").encode())

    def drain(self, seconds: float) -> str:
        assert self.sock
        buf = b""
        end = time.time() + seconds
        while time.time() < end:
            try:
                chunk = self.sock.recv(65536)
            except socket.timeout:
                continue
            except OSError as exc:
                raise NoConnection(f"socket error mid-session: {exc}")
            if not chunk:                      # peer closed: connection, not data
                raise NoConnection("DAS closed the connection")
            buf += chunk
        return buf.decode(errors="replace")

    def close(self) -> None:
        if self.sock:
            try:
                self.send("QUIT")
            except OSError:
                pass
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    # ── script primitives ────────────────────────────────────────────────

    def script(self, window: str, text: str, wait: float = 0.8) -> str:
        """SCRIPT <window> <text>. Window 'GLOBALSCRIPT' = desktop level.
        DAS re-tokenises on whitespace: quote a window name with spaces."""
        w = f'"{window}"' if " " in window and not window.startswith('"') else window
        self.send(f"SCRIPT\t{w}\t{text}")
        return self.drain(wait)

    def exists(self, window: str) -> bool:
        """Existence oracle: DAS answers
        'Wrong command, window name X does not exist!' for unknown names."""
        cur = LogCursor()
        reply = self.script(window, f'MsgLog("das_script_test exists {window}");', 0.6)
        if "does not exist" in reply:
            return False
        for _ in range(5):
            if any(f",Log,das_script_test exists {window}" in l for l in cur.new_lines()):
                return True
            time.sleep(0.3)
        raise RuntimeError(f"no answer for {window}: DAS did not reply or log; "
                           f"a ScriptError dialog may be freezing the API (run `dismiss`)")

    def eval(self, window: str, expr: str, tag: str | None = None) -> str | None:
        """Evaluate an expression inside a window and read the value back
        from the log. `$w` is bound to the window object. GLOBALSCRIPT
        leaves `$w` unset."""
        tag = tag or f"dst{int(time.time() * 1000) % 10_000_000}"
        bind = "" if window == "GLOBALSCRIPT" else f'$w = GetWindowObj("{window}"); '
        cur = LogCursor()
        self.script(window, f'{bind}MsgLog("{tag}=", {expr});', 0.6)
        val = read_log_value(tag, tries=3)
        # Runtime errors (ScriptError:1, e.g. a bad property name) are logged at
        # once and do not block; DAS then logs the object's type string as the
        # "value". Parse errors (ScriptError:100) block until dismissed.
        self.last_errors = [l for l in cur.new_lines(("Error",))]
        if val is None:
            self.last_errors += dismiss_errors()
        for e in self.last_errors:
            print("SCRIPT ERROR:", e, file=sys.stderr)
        return val


# ── log file ─────────────────────────────────────────────────────────────────

def read_log_value(tag: str, tries: int = 6) -> str | None:
    for _ in range(tries):
        lf = log_file()
        if lf.exists():
            for line in reversed(lf.read_text(errors="replace").splitlines()):
                if f",Log,{tag}=" in line:
                    return line.split(f"{tag}=", 1)[1].rstrip()
        time.sleep(0.4)
    return None


class LogCursor:
    """Remember where today's log ends now; later, return only what DAS
    appended. Byte offsets, not timestamps: DAS stamps with its own
    server-synced clock and WSL's clock has been seen 54 minutes off it."""

    def __init__(self):
        self.path = log_file()
        self.offset = self.path.stat().st_size if self.path.exists() else 0

    def new_lines(self, kinds: tuple[str, ...] = ("Log", "Error")) -> list[str]:
        if not self.path.exists():
            return []
        with self.path.open("rb") as fh:
            fh.seek(self.offset)
            tail = fh.read().decode(errors="replace")
        out: list[str] = []
        keep = False
        for line in tail.splitlines():
            parts = line.split(",", 2)
            if len(parts) == 3 and parts[1] in ("Log", "Error", "CMDAPILog"):
                keep = not kinds or parts[1] in kinds
                if keep:
                    out.append(line.rstrip())
            elif keep and out:                       # continuation of a multi-line MsgLog
                out[-1] += "\n" + line.rstrip()
        return out


# ── Windows UI Automation: clear the script-error modal ──────────────────────

DISMISS_SRC = r'''
import time, sys
from pywinauto import Desktop
d = Desktop(backend="uia")
mains = [w for w in d.windows() if "DASTrader" in w.window_text()]
if not mains: print("no DAS main window"); sys.exit(0)
main = mains[0]; n = 0; seen = []
for _ in range(25):
    # (a) ScriptError:100 parse dialog; (b) DAS MsgBox, a child Window titled "Message"
    # (a) ScriptError:100 parse dialog; (b) DAS MsgBox, a child Window titled "Message";
    # (c) any other notice: a child Window whose only buttons are OK/Close (seen for
    #     "PANIC can only run in market hours!", titled like the main window).
    errs = [c for c in main.descendants(control_type="Text") if "ScriptError" in c.window_text()]
    host = None
    if errs:
        e = errs[0]; seen.append(e.window_text()); host = e.parent()
    else:
        for c in main.descendants(control_type="Window", depth=3):
            names = [b.window_text() for b in c.descendants(control_type="Button", depth=3)]
            if names and set(names) <= {"OK", "Close", "Yes"} and len(names) <= 3:
                txt = " | ".join(t.window_text() for t in c.descendants(control_type="Text") if t.window_text())
                seen.append(f"{c.window_text()[:30]}: {txt[:200]}"); host = c; break
    if host is None:
        break
    oks = [b for b in host.descendants(control_type="Button") if b.window_text() in ("OK", "Yes", "Close")]
    if not oks: print("no OK button"); break
    oks[0].invoke(); n += 1; time.sleep(0.5)
for t in seen: print("DISMISSED:", t)
print("dismissed", n)
'''


def win_user() -> str:
    """Windows account name, for a scratch path the Windows Python can read."""
    if os.environ.get("WIN_USER"):
        return os.environ["WIN_USER"]
    try:
        out = subprocess.run(["/mnt/c/Windows/System32/cmd.exe", "/c", "echo %USERNAME%"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
        if out and "%" not in out:
            return out
    except (OSError, subprocess.SubprocessError):
        pass
    raise RuntimeError("cannot determine the Windows user; set WIN_USER")


def dismiss_errors() -> list[str]:
    """A ScriptError dialog blocks DAS's CMD API thread; every later command
    queues until it is closed. This finds the dialog under the DAS main
    window via UIA and invokes its OK. Returns the error texts it cleared."""
    if not Path(WIN_PY).exists():
        print(f"{WIN_PY} not found; cannot dismiss dialogs", file=sys.stderr)
        return []
    tmp = Path("/mnt/c/Users") / win_user() / "das_dismiss_tmp.py"
    tmp.write_text(DISMISS_SRC)
    win_path = subprocess.run(["wslpath", "-w", str(tmp)], capture_output=True, text=True).stdout.strip()
    if not win_path:
        raise RuntimeError("wslpath failed; cannot hand the dismiss script to Windows Python")
    try:
        res = subprocess.run([WIN_PY, win_path], capture_output=True, text=True, timeout=120,
                             stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Windows Python did not return in 120 s; dialog state unknown")
    if res.returncode != 0:
        raise RuntimeError("dismiss failed on the Windows side: " + res.stderr.strip()[-300:])
    out = res.stdout.strip()
    if out:
        print(out)
    return [l[len("DISMISSED: "):] for l in out.splitlines() if l.startswith("DISMISSED: ")]


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_exists(das: DAS, a) -> int:
    rc = 0
    for name in a.names:
        ok = das.exists(name)
        print(f"{name}: {'exists' if ok else 'MISSING'}")
        rc |= 0 if ok else 1
    return rc


def cmd_run(das: DAS, a) -> int:
    cur = LogCursor()
    text = re.sub(r"\bMsgBox\(", "MsgLog(", a.script)   # a modal would freeze the API
    if text != a.script:
        print("note: MsgBox rewritten to MsgLog before injection", file=sys.stderr)
    das.script(a.window, text, 1.0)
    time.sleep(0.6)
    # The Error line is written only when its dialog closes, so always try to
    # close one; this is also what un-freezes the API if the script failed.
    errs = dismiss_errors()
    lines = cur.new_lines()
    for line in lines:
        print(line)
    return 1 if errs or any(",Error," in l for l in lines) else 0


def cmd_eval(das: DAS, a) -> int:
    v = das.eval(a.window, a.expr)
    print(v if v is not None else "(no value logged; script error? run `dismiss`)")
    return 0 if v is not None and not das.last_errors else 1


def cmd_study(das: DAS, a) -> int:
    v = das.eval(a.window, f'$w.GetStudyVal("{a.study}")')
    print(f"{a.window}.{a.study} = {v}" + ("   (0 = study missing, misnamed, or not warmed up)" if v == "0" else ""))
    return 0 if v not in (None, "0") and not das.last_errors else 1


ORDER_TOKENS = re.compile(r"(\bBUY\b|\bSELL\b|\bSS\b|\bCXL\b|\bPanic\b|\bSend\s*\(|\.Send\b|NewOrderObj|"
                          r"\bSwitchDesktop\b|\bClearDesktop\b)", re.I)


def cmd_check(das: DAS | None, a) -> int:
    """Static lint (repo rules). With --live, EXECUTE the whole file inside DAS
    and report Log/Error lines. Live mode refuses any file whose code contains
    an order-sending or desktop-wiping token: SCRIPT runs inside DAS, so the
    watch-mode login is no protection. Order scripts get the paper-account
    round trip described in docs/CMD-API-TESTING.md instead."""
    src = Path(a.file).read_text()
    problems, warnings, forbidden = [], [], []
    code_lines = []
    for i, line in enumerate(src.splitlines(), 1):
        code = line.split("//", 1)[0]
        if "'" in code:
            problems.append(f"{i}: single quote in code")
        elif "'" in line:
            warnings.append(f"{i}: single quote in a comment (00 ran live with these; keep them out anyway)")
        if "&&" in code or "||" in code:
            problems.append(f"{i}: && or || (nest ifs)")
        m = ORDER_TOKENS.search(code)
        if m:
            forbidden.append(f"{i}: {m.group(0)}")
        if code.strip():
            code_lines.append(code.strip())
    print(f"static: {len(problems)} problem(s), {len(warnings)} warning(s)")
    for p in problems:
        print("   PROBLEM", p)
    for w in warnings:
        print("   warn   ", w)
    if not a.live:
        return 1 if problems else 0
    if forbidden:
        print("LIVE REFUSED: file contains order or desktop commands, which SCRIPT would execute:")
        for f in forbidden:
            print("   ", f)
        return 3
    assert das is not None
    # Joined into one line: DAS reports every error as Line:1, so the source line
    # must be found from the quoted text in the error, not from N.
    cur = LogCursor()
    text = re.sub(r"\bMsgBox\(", "MsgLog(", " ".join(code_lines))   # a modal would freeze the API
    das.script(a.window, text, 1.5)
    time.sleep(1.0)
    errs = dismiss_errors()
    for line in cur.new_lines():
        print(line)
    if errs:
        print(f"LIVE: {len(errs)} script error(s)")
        return 1
    print("LIVE: ran to completion with no script error dialog")
    return 1 if problems else 0


def cmd_bars(das: DAS, a) -> int:
    today = datetime.now()
    das.send(f"SB {a.symbol} MINCHART {today:%Y/%m/%d}-00:00 LATEST {a.mintype}")
    text = das.drain(4.0)
    das.send(f"UNSB {a.symbol} MINCHART")
    bars = sorted(l for l in text.splitlines() if l.startswith("$Bar "))
    if not bars:
        print(f"{a.symbol}: no bars returned (connection is up; symbol or window empty)")
        return 1
    for b in bars[-a.minutes:]:
        print(b)
    return 0


def cmd_dismiss(das: DAS | None, a) -> int:
    dismiss_errors()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("exists", help="window-existence oracle"); p.add_argument("names", nargs="+")
    p = sub.add_parser("run", help="inject script, print new Log/Error lines"); p.add_argument("window"); p.add_argument("script")
    p = sub.add_parser("eval", help="evaluate an expression, $w = window"); p.add_argument("window"); p.add_argument("expr")
    p = sub.add_parser("study", help="GetStudyVal on a named chart"); p.add_argument("window"); p.add_argument("study")
    p = sub.add_parser("check", help="lint a .das file; --live executes it (refused if it contains order code)")
    p.add_argument("file"); p.add_argument("--live", action="store_true"); p.add_argument("--window", default="GLOBALSCRIPT")
    p = sub.add_parser("bars", help="minute bars via SB MINCHART"); p.add_argument("symbol")
    p.add_argument("--minutes", type=int, default=10); p.add_argument("--mintype", type=int, default=1)
    sub.add_parser("dismiss", help="close any ScriptError dialog via UI Automation")
    a = ap.parse_args()

    if a.cmd == "dismiss":
        return cmd_dismiss(None, a)
    if a.cmd == "check" and not a.live:
        return cmd_check(None, a)          # static lint needs no socket
    try:
        das = DAS().connect()
    except NoConnection as exc:
        print(f"NO CONNECTION: {exc}", file=sys.stderr)
        return 2
    try:
        return {"exists": cmd_exists, "run": cmd_run, "eval": cmd_eval, "study": cmd_study,
                "check": cmd_check, "bars": cmd_bars}[a.cmd](das, a)
    finally:
        das.close()


if __name__ == "__main__":
    sys.exit(main())
