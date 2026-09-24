#!/usr/bin/env python3
"""Fashionably Late forward test: drive the DAS entry scripts across today's gameplan.

Python decides, DAS executes. Every 45 s this fetches 1-minute bars for each
gameplan ticker over the CMD API, computes 9-EMA / 34-SMA / ATR(14) / 20-bar
average volume, and on a confirmed cross after the entry gate sets the
$FL_* globals and injects scripts/20-fl-long.das or 21-fl-short.das into
montage1. At the EOD gate it injects 22-fl-flatten.das once per open symbol
and writes a report.

    fl_forward_test.py --date 2026-09-24 [--risk 250] [--max-shares 300]
                       [--gate 09:45] [--eod 15:55] [--dry-run]

Clock: MARKET time is the newest $Quote timestamp DAS sends, never this
machine's clock (WSL was 53 min ahead of the exchange on 2026-09-24).
Account: refuses to run unless the harness's paper-account guard passes and
GET BP returns the paper figure. Logs: JSONL and a report under
docs/forward-tests/.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import das_script_test as h  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
GAMEPLAN_DIR = Path("/mnt/c/Cobra Trading_x64/GamePlan")
BANNED = {"MU", "CRCL", "UGRO"}            # fl_shared.BANNED_TICKERS
MAX_RT = 2                                  # fl_shared.MAX_RT_PER_TICKER
VOL_MULT, STOP_MULT, MIN_BARS = 1.5, 1.5, 34
PAPER_BP_PREFIX = "BP 5"                    # TR4425 shows BP 500000.00


def script_code(name: str) -> str:
    """One line of code, comments stripped, ready for SCRIPT injection."""
    src = (REPO / "scripts" / name).read_text()
    return " ".join(l.split("//", 1)[0].strip() for l in src.splitlines() if l.split("//", 1)[0].strip())


def ema(vals: list[float], n: int) -> float:
    k = 2 / (n + 1)
    e = statistics.mean(vals[:n])
    for v in vals[n:]:
        e = v * k + e * (1 - k)
    return e


class Ticker:
    def __init__(self, sym: str):
        self.sym = sym
        self.bars: dict[str, dict] = {}
        self.prev_sign: int | None = None
        self.rt = 0
        self.open_side: str | None = None
        self.last_pos = 0

    def ingest(self, lines: list[str]) -> None:
        for l in lines:
            p = l.split()
            if len(p) >= 8 and p[0] == "$Bar" and p[1] == self.sym and "-" in p[2]:
                self.bars[p[2]] = dict(t=p[2], h=float(p[3]), lo=float(p[4]),
                                       o=float(p[5]), c=float(p[6]), v=float(p[7]))

    def evaluate(self):
        """(signal, info) from COMPLETED bars only; the newest bar is still forming."""
        s = [self.bars[k] for k in sorted(self.bars)][:-1]
        if len(s) < MIN_BARS + 1:
            return None, {"bars": len(s)}
        closes = [b["c"] for b in s]
        e9, s34 = ema(closes, 9), statistics.mean(closes[-34:])
        atr = statistics.mean(b["h"] - b["lo"] for b in s[-14:])
        avgv = statistics.mean(b["v"] for b in s[-21:-1])
        vnow = s[-1]["v"]
        sign = 1 if e9 > s34 else -1
        cross = sign if (self.prev_sign is not None and sign != self.prev_sign) else 0
        self.prev_sign = sign
        info = dict(t=s[-1]["t"], close=closes[-1], ema9=round(e9, 4), sma34=round(s34, 4),
                    atr=round(atr, 4), vnow=vnow, avgv=round(avgv, 1), cross=cross,
                    volok=bool(avgv > 0 and vnow > VOL_MULT * avgv))
        if cross and info["volok"] and atr > 0:
            return ("LONG" if cross == 1 else "SHORT"), info
        return None, info


def market_time(d: h.DAS, sym: str = "SPY") -> str:
    d.send(f"SB {sym} Lv1")
    r = d.drain(2.0)
    d.send(f"UNSB {sym} Lv1")
    ts = [tok[2:] for l in r.splitlines() if l.startswith("$Quote")
          for tok in l.split() if tok.startswith("T:")]
    return ts[-1] if ts else ""


def positions(d: h.DAS) -> dict[str, int]:
    d.send("POSREFRESH")
    pos: dict[str, int] = {}
    for l in d.drain(2.0).splitlines():
        p = l.split()
        if p and p[0] in ("%POS", "%IPOS"):
            off = 1 if p[0] == "%IPOS" else 0
            try:
                pos[p[1 + off]] = int(float(p[3 + off]))
            except (IndexError, ValueError):
                pass
    return pos


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--risk", type=float, default=250.0, help="dollars at risk per trade")
    ap.add_argument("--max-shares", type=int, default=300)
    ap.add_argument("--gate", default="09:45")
    ap.add_argument("--eod", default="15:55")
    ap.add_argument("--interval", type=int, default=45)
    ap.add_argument("--dry-run", action="store_true", help="log signals, inject nothing")
    a = ap.parse_args()

    gp = GAMEPLAN_DIR / f"GamePlan-{a.date}.txt"
    syms = [s.strip().upper() for s in gp.read_text().splitlines() if s.strip()]
    out_dir = REPO / "docs" / "forward-tests"
    out_dir.mkdir(exist_ok=True)
    jl = (out_dir / f"fl-{a.date}.jsonl").open("a")

    def log(**kw):
        kw["wall"] = datetime.now().isoformat(timespec="seconds")
        jl.write(json.dumps(kw) + "\n")
        jl.flush()
        print(json.dumps(kw), flush=True)

    d = h.DAS().connect()
    d.send("GET BP")
    bp = [l for l in d.drain(2.0).splitlines() if l.startswith("BP ")]
    if not bp or not bp[0].startswith(PAPER_BP_PREFIX):
        log(event="refuse", reason="buying power is not the paper figure", bp=bp)
        return 2
    if not d.exists("montage1"):
        log(event="refuse", reason="montage1 missing")
        return 2
    tickers: dict[str, Ticker] = {}
    for s in syms:
        if s in BANNED:
            log(event="skip", sym=s, reason="BANNED_TICKERS")
            continue
        tickers[s] = Ticker(s)
    if len(tickers) > 50:
        log(event="refuse", reason="more than 50 symbols")
        return 2
    log(event="start", date=a.date, symbols=list(tickers), risk=a.risk,
        gate=a.gate, eod=a.eod, dry_run=a.dry_run, bp=bp[0])

    long_code = script_code("20-fl-long.das")
    short_code = script_code("21-fl-short.das")
    close_code = script_code("22-fl-flatten.das")
    day = a.date.replace("-", "/")
    last_inject = 0.0

    while True:
        mt = market_time(d)
        if not mt:
            log(event="warn", reason="no quote timestamp; DAS frozen?")
            h.dismiss_errors()
            time.sleep(10)
            continue
        hhmm = mt[:5]
        for t in tickers.values():
            d.send(f"SB {t.sym} MINCHART {day}-00:00 LATEST 1")
            t.ingest(d.drain(2.5).splitlines())
            d.send(f"UNSB {t.sym} MINCHART")
        pos = positions(d)
        log(event="cycle", market=mt, pos={k: v for k, v in pos.items() if v},
            bars={t.sym: len(t.bars) for t in tickers.values()})
        for t in tickers.values():
            q = pos.get(t.sym, 0)
            if t.open_side and q == 0 and t.last_pos != 0:
                t.rt += 1
                log(event="closed", sym=t.sym, side=t.open_side, rt=t.rt, market=mt)
                t.open_side = None
            t.last_pos = q
            sig, info = t.evaluate()
            if info.get("cross"):
                log(event="cross", sym=t.sym, market=mt, **info)
            if not sig:
                continue
            log(event="signal", sym=t.sym, side=sig, market=mt, **info)
            if hhmm < a.gate:
                log(event="suppress", sym=t.sym, reason="before gate", market=mt)
                continue
            if t.rt >= MAX_RT:
                log(event="suppress", sym=t.sym, reason="RT cap")
                continue
            if t.open_side or q != 0:
                log(event="suppress", sym=t.sym, reason="position open")
                continue
            qty = max(1, min(a.max_shares, int(a.risk / (STOP_MULT * info["atr"]))))
            if a.dry_run:
                log(event="dry", sym=t.sym, side=sig, qty=qty)
                continue
            while time.time() - last_inject < 3.0:
                time.sleep(0.5)
            cur = h.LogCursor()
            d.script("GLOBALSCRIPT", f'$FL_SYM = "{t.sym}"; $FL_QTY = {qty}; $FL_ATR = {info["atr"]};', 0.8)
            d.script("montage1", long_code if sig == "LONG" else short_code, 4.0)
            last_inject = time.time()
            time.sleep(1.5)
            lines = cur.new_lines()
            h.dismiss_errors()
            log(event="inject", sym=t.sym, side=sig, qty=qty, atr=info["atr"], das=lines)
            if any("FL DONE" in l for l in lines):
                t.open_side = sig
                t.last_pos = qty
        if hhmm >= a.eod:
            pos = positions(d)
            for sym, q in pos.items():
                if q == 0:
                    continue
                cur = h.LogCursor()
                if not a.dry_run:
                    d.script("GLOBALSCRIPT", f'$FL_SYM = "{sym}";', 0.8)
                    d.script("montage1", close_code, 4.0)
                    time.sleep(2.5)
                log(event="flatten", sym=sym, qty=q, market=mt, das=cur.new_lines())
            break
        time.sleep(a.interval)

    d.send("POSREFRESH")
    pr = d.drain(3.0)
    trades = [l for l in pr.splitlines() if l.startswith(("%TRADE", "%ITRADE"))]
    posl = [l for l in pr.splitlines() if l.startswith(("%POS", "%IPOS"))]
    log(event="end", trades=len(trades), open_positions=posl)
    rep = out_dir / f"fl-{a.date}-report.md"
    lines = [f"# FL forward test {a.date}", "",
             f"Gameplan: {', '.join(syms)}",
             f"Traded universe: {', '.join(tickers)}",
             f"Risk per trade ${a.risk:.0f}, stop {STOP_MULT} x ATR, gate {a.gate}, EOD {a.eod}",
             "", "## Trades (from DAS %TRADE)", ""] + [f"    {l}" for l in trades] + \
            ["", "## Open positions at end", ""] + [f"    {l}" for l in posl] + \
            ["", "## Round trips per ticker", ""] + [f"- {t.sym}: {t.rt}" for t in tickers.values()]
    rep.write_text("\n".join(lines) + "\n")
    print("report:", rep)
    d.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
