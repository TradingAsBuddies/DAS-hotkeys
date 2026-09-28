#!/usr/bin/env python3
"""Read-only Level 2 + time-and-sales recorder and rolling day profile for one symbol.

Logs in to the DAS CMD API in WATCH mode (trailing 1: this session cannot place orders),
subscribes Lv2, tms and Lv1, appends every raw line to a tape file and rewrites a profile
markdown every --report-every seconds.  Alert lines go to stdout, one per line, prefixed
ALERT, so a Monitor can surface them.

    das_tape_profile.py KOD [--report-every 300] [--big-print 5000] [--until 16:05]

Formats seen live 2026-09-28 (Frontend CMD API, watch mode):
    $Lv2 KOD A EDGX 65 5 UPDATED 07:48:20          side MMID price size status time
    $T&S KOD 64.3506 1 I 08:48:20 FADF I 64          price size cond time MMID flag n
    $Quote KOD A:65 Asz:5 B:64.26 Bsz:2 V:.. L:.. Hi:.. Lo:.. VWAP:.. tradesAllDay:.. T:08:48:20
Lv2 times are DAS-local (an hour behind exchange time on this host); T&S and Quote times are
exchange time.  All profile times are exchange time.

Credentials from ~/.claude/.env (DAS_HOST, DAS_PORT, DAS_USER, DAS_PASSWORD, DAS_ACCOUNT).
Never printed.  No order command exists in this file.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import time
from collections import defaultdict, deque
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude" / "Tools"))
import das_quote as Q  # noqa: E402  (load_env, parse_quote)

TAPE_DIR = Path.home() / "market_data" / "tape"
REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "docs" / "forward-tests" / "tape"


def hm(t: str) -> tuple[int, int]:
    h, m = t.split(":")[:2]
    return int(h), int(m)


class Profile:
    def __init__(self, sym: str, big_print: int):
        self.sym, self.big = sym, big_print
        self.trades: list[tuple[str, float, int, str, str]] = []   # time, price, size, mmid, side
        self.quote: dict = {}
        self.bid = self.ask = None
        self.book: dict[str, dict[str, tuple[float, int]]] = {"A": {}, "B": {}}   # side -> mmid -> (price, size)
        self.book_samples: list[tuple[str, int, int, float]] = []   # time, bid5, ask5, spread
        self.hod = self.lod = None
        self.hod_t = self.lod_t = ""
        self.seeded = False
        self.hod_alerted = self.lod_alerted = 0.0
        self.above_vwap = None
        self.imb_state = None
        self.imb_since = 0.0
        self.alerts: list[str] = []
        self.last_sample = 0.0

    # ---- ingest -------------------------------------------------------------
    def on_line(self, line: str, now: float) -> list[str]:
        out: list[str] = []
        p = line.split()
        if line.startswith("$T&S") and len(p) >= 6:
            try:
                px, sz, t, mmid = float(p[2]), int(float(p[3])), p[5], p[6] if len(p) > 6 else ""
            except ValueError:
                return out
            side = "?"
            if self.bid and self.ask:
                if px >= self.ask:
                    side = "buy"
                elif px <= self.bid:
                    side = "sell"
                else:
                    side = "mid"
            self.trades.append((t, px, sz, mmid, side))
            # HOD/LOD are seeded from the Lv1 quote's Hi/Lo (the whole day, not just what this
            # session saw); until a quote arrives, track silently.  Alert once per 0.5% step.
            if self.hod is None or px > self.hod:
                if self.hod is not None and self.seeded and px >= self.hod_alerted * 1.005:
                    out.append(f"ALERT {t} new HOD {px:.2f} (prev {self.hod:.2f})")
                    self.hod_alerted = px
                self.hod, self.hod_t = px, t
            if self.lod is None or px < self.lod:
                if self.lod is not None and self.seeded and px <= self.lod_alerted * 0.995:
                    out.append(f"ALERT {t} new LOD {px:.2f} (prev {self.lod:.2f})")
                    self.lod_alerted = px
                self.lod, self.lod_t = px, t
            if sz >= self.big:
                out.append(f"ALERT {t} big print {sz:,} @ {px:.2f} {side} {mmid}")
            vwap = self.quote.get("VWAP")
            if vwap:
                try:
                    v = float(vwap)
                    ab = px > v
                    if self.above_vwap is not None and ab != self.above_vwap:
                        out.append(f"ALERT {t} VWAP cross: {px:.2f} {'above' if ab else 'below'} VWAP {v:.2f}")
                    self.above_vwap = ab
                except ValueError:
                    pass
        elif line.startswith("$Lv2") and len(p) >= 8:
            side, mmid = p[2], p[3]
            try:
                px, sz = float(p[4]), int(float(p[5]))
            except ValueError:
                return out
            if sz <= 0 or p[6].upper().startswith(("DELETE", "REMOVE")):
                self.book[side].pop(mmid, None)
            else:
                self.book[side][mmid] = (px, sz)
        elif line.startswith("$Quote"):
            q = Q.parse_quote(line)
            if q:
                self.quote.update(q)
                try:
                    if "B" in q:
                        self.bid = float(q["B"])
                    if "A" in q:
                        self.ask = float(q["A"])
                    if not self.seeded and q.get("Hi") and q.get("Lo") and float(q["Hi"]) > 0:
                        self.hod, self.lod = float(q["Hi"]), float(q["Lo"])
                        self.hod_t = self.lod_t = "before watch"
                        self.hod_alerted, self.lod_alerted = self.hod, self.lod
                        self.seeded = True
                except ValueError:
                    pass
        if now - self.last_sample >= 10:
            self.last_sample = now
            out += self.sample_book()
        return out

    def top5(self, side: str) -> list[tuple[float, int]]:
        lv = sorted(self.book[side].values(), key=lambda x: -x[0] if side == "B" else x[0])
        best = lv[0][0] if lv else None
        if best is None:
            return []
        # top five price levels, sizes summed per level
        levels: dict[float, int] = defaultdict(int)
        for px, sz in lv:
            levels[px] += sz
        keys = sorted(levels, reverse=(side == "B"))[:5]
        return [(k, levels[k]) for k in keys]

    def sample_book(self) -> list[str]:
        out = []
        b, a = self.top5("B"), self.top5("A")
        if not b or not a:
            return out
        bs, as_ = sum(s for _, s in b), sum(s for _, s in a)
        spread = a[0][0] - b[0][0]
        t = self.quote.get("T", datetime.now().strftime("%H:%M:%S"))
        self.book_samples.append((t, bs, as_, spread))
        ratio = (bs / as_) if as_ else 99.0
        state = "bid-heavy" if ratio >= 2 else "ask-heavy" if ratio <= 0.5 else "balanced"
        if state != self.imb_state:
            self.imb_state, self.imb_since = state, time.time()
        elif state != "balanced" and time.time() - self.imb_since >= 60 and int(time.time() - self.imb_since) % 300 < 10:
            out.append(f"ALERT {t} book {state} for {int(time.time()-self.imb_since)}s: top5 bid {bs:,} vs ask {as_:,} (ratio {ratio:.1f})")
        return out

    # ---- report -------------------------------------------------------------
    def report(self) -> str:
        q = self.quote
        tr = [t for t in self.trades if t[0] >= "09:30:00"] or self.trades
        vol = sum(s for _, _, s, _, _ in tr)
        lines = [f"# {self.sym} tape profile — {date.today().isoformat()}", "",
                 f"Rewritten {datetime.now():%H:%M:%S} local · exchange time in tables · read-only watch session · "
                 f"raw tape in `~/market_data/tape/`", ""]
        lines += ["## Session", "",
                  f"| Last | VWAP (DAS) | Bid × Ask | HOD | LOD | Day volume (DAS) | Prints seen | Prev close |",
                  "|---:|---:|---|---:|---:|---:|---:|---:|",
                  f"| {q.get('L','')} | {q.get('VWAP','')} | {q.get('B','')} × {q.get('A','')} | {self.hod or ''} @ {self.hod_t} | "
                  f"{self.lod or ''} @ {self.lod_t} | {q.get('V','')} | {len(self.trades):,} ({vol:,} sh since 09:30) | {q.get('ycl','')} |", ""]
        if not tr:
            return "\n".join(lines + ["No prints yet."])
        # volume by price
        px_all = [p for _, p, _, _, _ in tr]
        lo, hi = min(px_all), max(px_all)
        step = max(0.05, round((hi - lo) / 30, 2)) if hi > lo else 0.05
        bins: dict[float, int] = defaultdict(int)
        for _, p, s, _, _ in tr:
            bins[round((p // step) * step, 2)] += s
        total = sum(bins.values())
        poc = max(bins, key=bins.get)
        # value area 70% expanding from POC
        order = sorted(bins)
        i = j = order.index(poc)
        acc = bins[poc]
        while acc < 0.7 * total and (i > 0 or j < len(order) - 1):
            up = bins[order[j + 1]] if j < len(order) - 1 else -1
            dn = bins[order[i - 1]] if i > 0 else -1
            if up >= dn:
                j += 1; acc += up
            else:
                i -= 1; acc += dn
        val, vah = order[i], order[j]
        lines += ["## Volume by price (since 09:30, prints seen by this session)", "",
                  f"POC **{poc:.2f}** · value area **{val:.2f} – {vah:.2f}** (70%) · bin {step:.2f}", "",
                  "| Price | Volume | Share | |", "|---:|---:|---:|---|"]
        mx = max(bins.values())
        for k in sorted(bins, reverse=True):
            bar = "█" * int(30 * bins[k] / mx)
            mark = " ← POC" if k == poc else ""
            lines.append(f"| {k:.2f} | {bins[k]:,} | {bins[k]/total*100:4.1f}% | {bar}{mark} |")
        # 15-minute bars with aggression
        bars: dict[str, dict] = {}
        for t, p, s, _, side in tr:
            h, m = hm(t)
            key = f"{h:02d}:{(m // 15) * 15:02d}"
            b = bars.setdefault(key, dict(o=p, h=p, l=p, c=p, v=0, buy=0, sell=0, n=0))
            b["h"] = max(b["h"], p); b["l"] = min(b["l"], p); b["c"] = p; b["v"] += s; b["n"] += 1
            if side == "buy":
                b["buy"] += s
            elif side == "sell":
                b["sell"] += s
        lines += ["", "## 15-minute bars from the tape (aggression = prints at/above ask vs at/below bid)", "",
                  "| Bar | Open | High | Low | Close | Volume | Prints | At ask | At bid | Net |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for k in sorted(bars):
            b = bars[k]
            lines.append(f"| {k} | {b['o']:.2f} | {b['h']:.2f} | {b['l']:.2f} | {b['c']:.2f} | {b['v']:,} | {b['n']:,} | "
                         f"{b['buy']:,} | {b['sell']:,} | {b['buy']-b['sell']:+,} |")
        # book imbalance per 5 min
        if self.book_samples:
            win: dict[str, list] = defaultdict(list)
            for t, bs, as_, sp in self.book_samples:
                h, m = hm(t)
                win[f"{h:02d}:{(m // 5) * 5:02d}"].append((bs, as_, sp))
            lines += ["", "## Book imbalance, top five levels each side (10-second samples, 5-minute means)", "",
                      "| Window | Bid size | Ask size | Bid/Ask | Spread |", "|---|---:|---:|---:|---:|"]
            for k in sorted(win):
                v = win[k]
                bs = sum(x[0] for x in v) / len(v); as_ = sum(x[1] for x in v) / len(v); sp = sum(x[2] for x in v) / len(v)
                lines.append(f"| {k} | {bs:,.0f} | {as_:,.0f} | {bs/as_ if as_ else 0:.2f} | {sp:.2f} |")
        # largest prints
        big = sorted(tr, key=lambda x: -x[2])[:10]
        lines += ["", "## Ten largest prints", "", "| Time | Price | Size | Side | MMID |", "|---|---:|---:|---|---|"]
        for t, p, s, mm, side in big:
            lines.append(f"| {t} | {p:.2f} | {s:,} | {side} | {mm} |")
        # participation
        tape_mm: dict[str, int] = defaultdict(int)
        for _, _, s, mm, _ in tr:
            tape_mm[mm] += s
        book_mm: dict[str, int] = defaultdict(int)
        for side in ("A", "B"):
            for mm, (_, s) in self.book[side].items():
                book_mm[mm] += s
        lines += ["", "## Participation", "", "Tape volume by venue: " + ", ".join(
            f"{k} {v:,}" for k, v in sorted(tape_mm.items(), key=lambda x: -x[1])[:8]),
                  "", "Book size on display now by MMID: " + (", ".join(
                      f"{k} {v:,}" for k, v in sorted(book_mm.items(), key=lambda x: -x[1])[:10]) or "none")]
        if self.alerts:
            lines += ["", "## Alerts (latest 40)", ""] + [f"- {a}" for a in self.alerts[-40:]]
        return "\n".join(lines) + "\n"


def run(sym: str, report_every: int, big_print: int, until: str) -> int:
    Q.load_env()
    host = os.environ.get("DAS_HOST", "127.0.0.1")
    port = int(os.environ.get("DAS_PORT", "9910"))
    user, pw, acct = os.environ.get("DAS_USER"), os.environ.get("DAS_PASSWORD"), os.environ.get("DAS_ACCOUNT")
    if not all([user, pw, acct]):
        print("credentials missing from ~/.claude/.env", file=sys.stderr)
        return 1
    TAPE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    tape = (TAPE_DIR / f"{sym}_{today}_tape.jsonl").open("a")
    out = OUT_DIR / f"{sym}-{today}-profile.md"
    prof = Profile(sym, big_print)
    until_hm = hm(until)
    backoff = 2
    last_report = 0.0
    print(f"ALERT start {sym} recorder; profile -> {out}", flush=True)
    while True:
        now_hm = hm(datetime.now().strftime("%H:%M"))
        # host clock is Central; exchange = host + 1h.  Stop at `until` exchange time.
        if (now_hm[0] + 1, now_hm[1]) >= until_hm:
            break
        try:
            with socket.create_connection((host, port), timeout=10) as sock:
                sock.settimeout(2.0)
                sock.sendall(f"LOGIN {user} {pw} {acct} 1\r\n".encode())     # watch mode: no orders possible
                time.sleep(1.0)
                for sub in ("Lv2", "tms", "Lv1"):
                    sock.sendall(f"SB {sym} {sub}\r\n".encode())
                print(f"ALERT connected {datetime.now():%H:%M:%S}", flush=True)
                backoff = 2
                buf = ""
                while True:
                    now_hm = hm(datetime.now().strftime("%H:%M"))
                    if (now_hm[0] + 1, now_hm[1]) >= until_hm:
                        break
                    try:
                        chunk = sock.recv(65536).decode(errors="replace")
                    except socket.timeout:
                        chunk = ""
                    if chunk == "" and not buf:
                        # timeout: fall through to report check; a closed socket returns b"" repeatedly
                        pass
                    buf += chunk
                    now = time.time()
                    while "\n" in buf:
                        line, _, buf = buf.partition("\n")
                        line = line.strip()
                        if not line:
                            continue
                        tape.write(json.dumps({"t": round(now, 3), "l": line}) + "\n")
                        if line.startswith("#") and ("allow IP" in line or "login" in line.lower() and "fail" in line.lower()):
                            print(f"ALERT DAS refused: {line}", flush=True)
                        for a in prof.on_line(line, now):
                            prof.alerts.append(a)
                            print(a, flush=True)
                    if now - last_report >= report_every:
                        last_report = now
                        tape.flush()
                        out.write_text(prof.report())
                        print(f"ALERT profile rewritten {datetime.now():%H:%M:%S} prints={len(prof.trades):,} "
                              f"last={prof.quote.get('L')} vwap={prof.quote.get('VWAP')} hod={prof.hod} lod={prof.lod}", flush=True)
                for sub in ("Lv2", "tms", "Lv1"):
                    sock.sendall(f"UNSB {sym} {sub}\r\n".encode())
                sock.sendall(b"QUIT\r\n")
        except (OSError, ConnectionError) as exc:
            print(f"ALERT connection lost ({type(exc).__name__}); retry in {backoff}s", flush=True)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue
        break
    out.write_text(prof.report())
    tape.close()
    print(f"ALERT stop {sym} recorder at {datetime.now():%H:%M:%S}; final profile written", flush=True)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--report-every", type=int, default=300)
    ap.add_argument("--big-print", type=int, default=5000)
    ap.add_argument("--until", default="16:05", help="exchange time to stop")
    a = ap.parse_args()
    return run(a.symbol.upper(), a.report_every, a.big_print, a.until)


if __name__ == "__main__":
    raise SystemExit(main())
