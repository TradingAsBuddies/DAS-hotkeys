"""DAS outputs for HVC Watcher: Market Viewer import lists, chart rays, alerts.

Payload builders are pure (return (window, text) pairs) so --dry-run can print
exactly what would be sent. Sending reuses tools/das_script_test.DAS, which
logs in watch mode on the paper account only and raises NoConnection rather
than returning "no data".
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
from das_script_test import DAS, NoConnection, dismiss_errors, load_env  # noqa: E402,F401

from engine import Ray  # noqa: E402

# Pine defaults #4CAF50 (HVE green) and #FF9800 (HVC orange).
RGB = {"HVE": (76, 175, 80), "HVC": (255, 152, 0)}

# Any of these inside an injected SCRIPT would trade or wipe the desktop.
# SCRIPT runs inside DAS under DAS's own login, so watch mode is no protection.
FORBIDDEN = re.compile(
    r"\b(Send|BUY|SELL|SHORT|COVER|CXL|CANCEL|Panic|Flatten|Reverse|TriggerOrder|"
    r"NEWORDER|LoadDesktop|CloseAll)\b", re.I)

Payload = tuple[str, str]   # (window, script text)


# ── Market Viewer lists ──────────────────────────────────────────────────────

def gameplan_dir(env: dict[str, str]) -> Path:
    """<DAS_ROOT>\\GamePlan as a WSL path. DAS_ROOT in ~/.claude/.env is authoritative."""
    root = env.get("DAS_ROOT") or r"C:\Cobra Trading_x64"
    m = re.match(r"^([A-Za-z]):[\\/](.*)$", root)
    if not m:
        raise ValueError(f"DAS_ROOT is not a Windows path: {root!r}")
    return Path(f"/mnt/{m.group(1).lower()}") / m.group(2).replace("\\", "/") / "GamePlan"


def write_list(out_dir: Path, stem: str, symbols: list[str], day: str) -> list[Path]:
    """One ticker per line (the format Market Viewer → Load reads), Today + dated copy.
    An empty list is still written so yesterday's file can't be mistaken for today's."""
    out_dir.mkdir(parents=True, exist_ok=True)
    body = "".join(f"{s}\n" for s in symbols)
    paths = [out_dir / f"{stem}-Today.txt", out_dir / f"{stem}-{day}.txt"]
    for p in paths:
        p.write_text(body)
    return paths


# ── SCRIPT payloads ──────────────────────────────────────────────────────────

def _px(x: float) -> str:
    return f"{x:.4f}".rstrip("0").rstrip(".")


def ray_payloads(window: str, symbol: str, rays: list[Ray], clear: bool) -> list[Payload]:
    """Load the symbol in a named chart, then draw one horizontal line per ray.
    `SYMBOL X` is sent as its own SCRIPT so the chart switches before drawing.
    RemoveAllTrendLines deletes *every* line on that symbol, yours included,
    so it only runs when clear=True."""
    if not rays:
        return []
    out: list[Payload] = [(window, f"SYMBOL {symbol};")]
    draw = "RemoveAllTrendLines; " if clear else ""
    draw += " ".join(
        f"DrawHorzLineWithPrice({_px(r.level)}, Color({','.join(map(str, RGB[r.kind]))}));"
        for r in rays)
    out.append((window, draw))
    return out


def alert_name(symbol: str, ray: Ray) -> str:
    return f"HVC {symbol} {ray.kind} {ray.date or ray.bar} {_px(ray.level)}"


def alert_payloads(symbol: str, rays: list[Ray], last_close: float,
                   field: str = "L1 LAST") -> list[Payload]:
    """One DAS alert per retained ray. A later bar touches a ray when its range
    includes the level; intraday that is Last crossing toward it from the
    current side, so the operator depends on where the level sits vs the close."""
    out: list[Payload] = []
    for r in rays:
        op = ">=" if r.level > last_close else "<="
        out.append(("GLOBALSCRIPT",
                    f'$a = NewAlertObj(); $a.name = "{alert_name(symbol, r)}"; '
                    f'$a.Symb = "{symbol}"; $a.AddItem("{field}", "{op}", "{_px(r.level)}"); '
                    f"$a.save();"))
    return out


def check_safe(payloads: list[Payload]) -> None:
    for w, text in payloads:
        m = FORBIDDEN.search(text)
        if m:
            raise ValueError(f"refusing to send order/desktop token {m.group(0)!r} to {w}: {text}")


def send(payloads: list[Payload], *, pause: float = 0.4, symbol_pause: float = 1.5) -> list[str]:
    """Send over the CMD API. Returns DAS replies that look like errors.
    Raises NoConnection if DAS is unreachable or refuses login."""
    check_safe(payloads)
    das = DAS().connect()
    problems: list[str] = []
    try:
        for w, text in payloads:
            reply = das.script(w, text, wait=pause)
            if "does not exist" in reply or "Wrong command" in reply:
                problems.append(f"{w}: {reply.strip()[:160]}")
            if text.startswith("SYMBOL "):
                time.sleep(symbol_pause)      # let the chart load before drawing
        problems += [f"script error dialog: {e}" for e in dismiss_errors()]
    finally:
        das.close()
    return problems
