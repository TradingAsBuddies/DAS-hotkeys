#!/usr/bin/env python3
"""Week backtest of the Fashionably Late rule the forward-test driver trades.

Same signal as tools/fl_forward_test.py: on completed 1-minute bars, 9-EMA of
closes crosses the 34-SMA (sign change between consecutive evaluations), the
signal bar's volume exceeds 1.5 x the prior 20-bar average, no entry before the
gate, one position per ticker, two round trips per ticker per day, stop 1.5 x
ATR(14) placed on entry, everything closed at the session end. Entry fills at
the next bar's open plus/minus 0.15 slip, as the DAS scripts pay.

Data: Massive.com flat files (us_stocks_sip minute_aggs_v1), one CSV per
ticker per day under ~/market_data/{T}/{T}_{date}_minute.csv, all sessions,
window_start in UTC nanoseconds. The driver evaluated once per 45 s cycle;
here every completed bar is evaluated, which is the same thing at 1-minute
resolution with no missed cycles.

    backtest_fl_week.py --start 2026-09-21 --end 2026-09-25 [--gate 09:45]
                        [--eod 15:55] [--risk 75] [--max-shares 300]
                        [--stop-floor-pct 0] [--atr-bars 1]
                        [--plans-dir "/mnt/c/Cobra Trading_x64/GamePlan"]

Universe per day: that day's GamePlan-{date}.txt if it exists, else the union
of the plans that do exist in the range (reported as such). MU is banned.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
DATA = Path.home() / "market_data"
BANNED = {"MU", "CRCL", "UGRO"}
VOL_MULT, STOP_MULT, MIN_BARS, MAX_RT, SLIP = 1.5, 1.5, 34, 2, 0.15


RTH_OPEN, RTH_CLOSE = (9, 30), (16, 0)


_DAY_CACHE: dict = {}


def load_day(sym: str, d: date, rth_only: bool = False) -> list[dict]:
    key = (sym, d, rth_only)
    if key in _DAY_CACHE:
        return _DAY_CACHE[key]
    rows = _load_day(sym, d, rth_only)
    if len(_DAY_CACHE) > 4000:
        _DAY_CACHE.clear()
    _DAY_CACHE[key] = rows
    return rows


def _load_day(sym: str, d: date, rth_only: bool = False) -> list[dict]:
    f = DATA / sym / f"{sym}_{d.isoformat()}_minute.csv"
    if not f.exists():
        return []
    rows = []
    with f.open() as fh:
        for r in csv.DictReader(fh):
            ts = datetime.fromtimestamp(int(r["window_start"]) / 1e9, tz=timezone.utc).astimezone(ET)
            if ts.hour < 4:
                continue
            if rth_only and not (RTH_OPEN <= (ts.hour, ts.minute) < RTH_CLOSE):
                continue
            rows.append(dict(t=ts, o=float(r["open"]), h=float(r["high"]), lo=float(r["low"]),
                             c=float(r["close"]), v=float(r["volume"])))
    rows.sort(key=lambda b: b["t"])
    return rows


def resample(bars: list[dict], minutes: int) -> list[dict]:
    """Aggregate 1-minute bars into N-minute bars aligned to the clock."""
    if minutes <= 1:
        return bars
    out: list[dict] = []
    for b in bars:
        key = b["t"].replace(minute=b["t"].minute - b["t"].minute % minutes, second=0, microsecond=0)
        if out and out[-1]["t"] == key:
            o = out[-1]
            o["h"] = max(o["h"], b["h"]); o["lo"] = min(o["lo"], b["lo"]); o["c"] = b["c"]; o["v"] += b["v"]
        else:
            out.append(dict(t=key, o=b["o"], h=b["h"], lo=b["lo"], c=b["c"], v=b["v"]))
    return out


def ema(vals, n):
    k = 2 / (n + 1)
    e = statistics.mean(vals[:n])
    for v in vals[n:]:
        e = v * k + e * (1 - k)
    return e


def atr_of(bars: list[dict], atr_bars: int) -> float:
    """ATR(14) on 1-minute bars, or on N-minute bars built from them."""
    if atr_bars <= 1:
        return statistics.mean(b["h"] - b["lo"] for b in bars[-14:])
    agg = []
    for i in range(len(bars) - (len(bars) % atr_bars), -1, -atr_bars):
        chunk = bars[i - atr_bars:i] if i - atr_bars >= 0 else None
        if chunk:
            agg.append((max(b["h"] for b in chunk), min(b["lo"] for b in chunk)))
        if len(agg) >= 14:
            break
    if len(agg) < 14:
        return 0.0
    return statistics.mean(h - lo for h, lo in agg)


def trend_5m(done: list[dict]) -> int:
    """Sign of 9-EMA vs 34-SMA on 5-minute closes built from the completed 1-minute bars."""
    closes = [b["c"] for b in done]
    fives = [closes[i] for i in range(len(closes) - 1, -1, -5)][::-1]     # every 5th close, aligned to the last
    if len(fives) < 34:
        return 0
    return 1 if ema(fives, 9) > statistics.mean(fives[-34:]) else -1


def ema9_close_exit(fine: list[dict], start, end, side: str):
    """First fine bar in (start, end] whose close is on the opposite side of the fine 9-EMA.
    Returns (bar, ema) or None. EMA seeded on the 9 bars before `start`."""
    idx = [i for i, b in enumerate(fine) if start < b["t"] <= end]
    if not idx:
        return None
    first = idx[0]
    if first < 9:
        return None
    k = 2 / 10
    e = statistics.mean(b["c"] for b in fine[first - 9:first])
    for i in idx:
        b = fine[i]
        e = b["c"] * k + e * (1 - k)
        if (side == "LONG" and b["c"] < e) or (side == "SHORT" and b["c"] > e):
            return b, e
    return None


def indicator_series(bars: list[dict], atr_bars: int):
    """ema9[i], sma34[i], atr14[i], avgv20[i] computed over bars[:i+1] (i.e. bars[i] is the
    last COMPLETED bar). One pass, so a 3-year run is linear, not quadratic."""
    n = len(bars)
    closes = [b["c"] for b in bars]
    ema9 = [None] * n
    k = 0.2
    if n >= 9:
        e = statistics.mean(closes[:9]); ema9[8] = e
        for i in range(9, n):
            e = closes[i] * k + e * (1 - k); ema9[i] = e
    sma34 = [None] * n
    run = 0.0
    for i in range(n):
        run += closes[i]
        if i >= 34:
            run -= closes[i - 34]
        if i >= 33:
            sma34[i] = run / 34
    ranges = [b["h"] - b["lo"] for b in bars]
    atr = [None] * n
    rs = 0.0
    for i in range(n):
        rs += ranges[i]
        if i >= 14:
            rs -= ranges[i - 14]
        if i >= 13:
            atr[i] = rs / 14
    if atr_bars > 1:                                   # ATR on coarser bars, as before
        atr = [atr_of(bars[:i + 1], atr_bars) if i >= 14 * atr_bars else None for i in range(n)]
    vols = [b["v"] for b in bars]
    avgv = [None] * n                                  # mean of the 20 bars BEFORE bar i
    vs = 0.0
    for i in range(n):
        if i >= 1:
            vs += vols[i - 1]
        if i >= 21:
            vs -= vols[i - 21]
        if i >= 20:
            avgv[i] = vs / 20
    return ema9, sma34, atr, avgv


def run_day(sym: str, bars: list[dict], a, day: date | None = None, fine: list[dict] | None = None) -> list[dict]:
    """bars may include warm-up bars from earlier days; trades are only taken on `day`.
    `fine` is the same day resampled to --exit-ema9-close minutes, for the trailing exit."""
    trades = []
    E9, S34, ATR, AVGV = indicator_series(bars, a.atr_bars)
    prev_sign = None
    pending = None                      # (side, bars_held) while waiting for --hold-bars
    pos = None
    rt = 0
    max_rt = 1 if a.first_cross_only else MAX_RT
    gate = datetime.strptime(a.gate, "%H:%M").time()
    eod = datetime.strptime(a.eod, "%H:%M").time()
    last_entry = datetime.strptime(a.last_entry, "%H:%M").time() if a.last_entry else None
    for i in range(MIN_BARS + 1, len(bars)):
        done = bars[:i]                      # completed bars; bars[i] is the bar now forming
        now = bars[i]
        j = i - 1                                  # index of the last completed bar
        if day is not None and now["t"].date() != day:
            # warm-up bar: keep the indicator state current, take nothing
            prev_sign = 1 if E9[j] > S34[j] else -1
            continue
        # ── manage an open position on the forming bar ──────────────────────
        if pos:
            # breakeven: once the bar before this one has shown +R in our favour, stop -> entry
            if a.be_after and not pos.get("be"):
                prev = done[-1]
                fav = (prev["h"] - pos["entry"]) if pos["side"] == "LONG" else (pos["entry"] - prev["lo"])
                if fav >= a.be_after * pos["risk"]:
                    pos["stop"] = pos["entry"]; pos["be"] = True
            # finer-timeframe 9-EMA close exit, checked across this bar's span
            if fine is not None and pos.get("entered_bar") != now["t"]:
                span_end = now["t"] + timedelta(minutes=a.bar_minutes)
                hitx = ema9_close_exit(fine, now["t"] - timedelta(seconds=1), span_end, pos["side"])
                if hitx:
                    fb, _ = hitx
                    px = fb["c"] - SLIP if pos["side"] == "LONG" else fb["c"] + SLIP
                    pnl = (px - pos["entry"]) * pos["qty"] if pos["side"] == "LONG" else (pos["entry"] - px) * pos["qty"]
                    trades.append({**pos, "exit": px, "exit_t": fb["t"], "pnl": pnl, "why": "ema9"})
                    pos = None
                    rt += 1
        if pos:
            hit = (now["lo"] <= pos["stop"]) if pos["side"] == "LONG" else (now["h"] >= pos["stop"])
            if a.exit_on_opposite and prev_sign is not None:
                s_now = 1 if E9[j] > S34[j] else -1
                if (pos["side"] == "LONG" and s_now == -1) or (pos["side"] == "SHORT" and s_now == 1):
                    px = now["o"] - SLIP if pos["side"] == "LONG" else now["o"] + SLIP
                    pnl = (px - pos["entry"]) * pos["qty"] if pos["side"] == "LONG" else (pos["entry"] - px) * pos["qty"]
                    trades.append({**pos, "exit": px, "exit_t": now["t"], "pnl": pnl, "why": "opposite"})
                    pos = None
                    rt += 1
                    hit = False
            if pos and hit:
                fill = pos["stop"] - a.stop_slip if pos["side"] == "LONG" else pos["stop"] + a.stop_slip
                pnl = (fill - pos["entry"]) * pos["qty"] if pos["side"] == "LONG" else (pos["entry"] - fill) * pos["qty"]
                trades.append({**pos, "exit": fill, "exit_t": now["t"], "pnl": pnl, "why": "stop"})
                pos = None
                rt += 1
            elif pos and now["t"].time() >= eod:
                px = now["o"] - SLIP if pos["side"] == "LONG" else now["o"] + SLIP
                pnl = (px - pos["entry"]) * pos["qty"] if pos["side"] == "LONG" else (pos["entry"] - px) * pos["qty"]
                trades.append({**pos, "exit": px, "exit_t": now["t"], "pnl": pnl, "why": "eod"})
                pos = None
                rt += 1
        if now["t"].time() >= eod:
            if day is None:
                break
            continue
        # ── signal on completed bars ─────────────────────────────────────────
        e9, s34 = E9[j], S34[j]
        sign = 1 if e9 > s34 else -1
        cross = sign if (prev_sign is not None and sign != prev_sign) else 0
        prev_sign = sign
        # ── --hold-bars: a cross arms a pending entry that must survive N more bars ──
        if a.hold_bars:
            if cross:
                avgv0 = AVGV[j] or 0.0
                volok0 = a.vol_mult <= 0 or (avgv0 > 0 and done[-1]["v"] > a.vol_mult * avgv0)
                pending = {"side": sign, "held": 0} if volok0 else None
                continue
            if pending:
                if sign != pending["side"]:
                    pending = None
                    continue
                pending["held"] += 1
                if pending["held"] < a.hold_bars:
                    continue
                cross = pending["side"]
                pending = None
            else:
                continue
        if not cross or pos or rt >= max_rt:
            continue
        if done[-1]["t"].time() < gate:
            continue
        if a.last_entry and now["t"].time() >= last_entry:
            continue
        if not a.hold_bars and a.vol_mult > 0:
            avgv = AVGV[j] or 0.0
            if not (avgv > 0 and done[-1]["v"] > a.vol_mult * avgv):
                continue
        if a.trend_5m and trend_5m(done) != cross:
            continue
        atr = ATR[j] or 0.0
        if atr <= 0:
            continue
        side = "LONG" if cross == 1 else "SHORT"
        entry = now["o"] + SLIP if side == "LONG" else now["o"] - SLIP
        stop_dist = max(round(a.stop_mult * atr, 2), entry * a.stop_floor_pct / 100)
        if stop_dist < 0.02:
            continue
        size_dist = max(round((a.size_mult or a.stop_mult) * atr, 2), entry * a.stop_floor_pct / 100)
        qty = max(1, min(a.max_shares, int(a.risk / size_dist)))
        stop = entry - stop_dist if side == "LONG" else entry + stop_dist
        pos = dict(sym=sym, side=side, qty=qty, entry=entry, stop=stop, atr=atr, entry_t=now["t"],
                   risk=stop_dist, entered_bar=now["t"])
    if pos:
        # series ended with a position open (e.g. RTH 15-minute bars end before the eod gate):
        # close on the last bar's close, as the flatten would
        last = bars[-1]
        px = last["c"] - SLIP if pos["side"] == "LONG" else last["c"] + SLIP
        pnl = (px - pos["entry"]) * pos["qty"] if pos["side"] == "LONG" else (pos["entry"] - px) * pos["qty"]
        trades.append({**pos, "exit": px, "exit_t": last["t"], "pnl": pnl, "why": "eod"})
    return trades


def universe_for(d: date, plans: dict[date, list[str]], fixed: list[str] | None = None) -> tuple[list[str], str]:
    if fixed:
        return fixed, "fixed universe"
    if d in plans:
        return plans[d], "that day's plan"
    union = sorted({s for v in plans.values() for s in v})
    return union, "UNION of available plans (no plan published that day)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2026-09-21")
    ap.add_argument("--end", default="2026-09-25")
    ap.add_argument("--gate", default="09:45")
    ap.add_argument("--eod", default="15:55")
    ap.add_argument("--risk", type=float, default=75.0)
    ap.add_argument("--max-shares", type=int, default=300)
    ap.add_argument("--stop-floor-pct", type=float, default=0.0, help="minimum stop as %% of price")
    ap.add_argument("--atr-bars", type=int, default=1, help="ATR on N-minute bars (1 = as traded)")
    ap.add_argument("--stop-mult", type=float, default=STOP_MULT, help="stop distance in ATRs")
    ap.add_argument("--size-mult", type=float, default=0.0, help="size as if the stop were this many ATRs (default: --stop-mult)")
    ap.add_argument("--hold-bars", type=int, default=0, help="cross must hold N completed bars before entry")
    ap.add_argument("--first-cross-only", action="store_true", help="one entry per name per day")
    ap.add_argument("--exit-on-opposite", action="store_true", help="exit when the opposite cross prints")
    ap.add_argument("--trend-5m", action="store_true", help="only trade with the 5-minute 9/34 sign")
    ap.add_argument("--bar-minutes", type=int, default=1, help="signal timeframe: resample bars to N minutes")
    ap.add_argument("--warmup-days", type=int, default=0, help="prepend N prior trading days so the 34-SMA is warm at the open")
    ap.add_argument("--rth-only", action="store_true", help="regular-hours bars only (09:30-16:00)")
    ap.add_argument("--vol-mult", type=float, default=VOL_MULT, help="signal-bar volume vs 20-bar average; 0 disables")
    ap.add_argument("--quiet", action="store_true", help="week line only")
    ap.add_argument("--plans-dir", default="/mnt/c/Cobra Trading_x64/GamePlan")
    ap.add_argument("--json", help="write trades to this JSON file")
    ap.add_argument("--symbols", help="comma list: fixed universe for every day, ignoring plan files")
    ap.add_argument("--exit-ema9-close", type=int, default=0, help="exit when an N-minute bar closes across its 9-EMA (0 = off)")
    ap.add_argument("--be-after", type=float, default=0.0, help="move stop to entry after +R in favour (0 = off)")
    ap.add_argument("--last-entry", default="", help="no new entries at or after HH:MM")
    ap.add_argument("--stop-slip", type=float, default=0.0, help="adverse slippage per share on every stop fill")
    a = ap.parse_args()

    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    plans: dict[date, list[str]] = {}
    d = start
    while d <= end:
        f = Path(a.plans_dir) / f"GamePlan-{d.isoformat()}.txt"
        if f.exists():
            plans[d] = [s.strip().upper() for s in f.read_text().splitlines() if s.strip() and s.strip().upper() not in BANNED]
        d += timedelta(days=1)

    all_trades = []
    flags = " ".join(f for f, on in [("%dm-bars" % a.bar_minutes, a.bar_minutes > 1), ("warm%d" % a.warmup_days, a.warmup_days),
                                     ("rth", a.rth_only), ("vol%g" % a.vol_mult, a.vol_mult != VOL_MULT), ("hold%d" % a.hold_bars, a.hold_bars),
                                     ("ema9x%dm" % a.exit_ema9_close, a.exit_ema9_close), ("be%g" % a.be_after, a.be_after),
                                     ("last%s" % a.last_entry, a.last_entry), ("slip%g" % a.stop_slip, a.stop_slip),
                                     ("stop%g" % a.stop_mult, a.stop_mult != STOP_MULT),
                                     ("first", a.first_cross_only), ("opp-exit", a.exit_on_opposite), ("trend5m", a.trend_5m)] if on)
    if not a.quiet:
        print(f"FL week backtest {a.start}..{a.end}  gate {a.gate}  eod {a.eod}  risk ${a.risk:.0f}  "
              f"stop {a.stop_mult}xATR({a.atr_bars}m){f' floor {a.stop_floor_pct}%' if a.stop_floor_pct else ''} {flags}")
    d = start
    while d <= end:
        if d.weekday() < 5:
            syms, how = universe_for(d, plans, [x.strip().upper() for x in a.symbols.split(",")] if a.symbols else None)
            day_tr = []
            missing = []
            for s in syms:
                series = []
                back, dd = 0, d
                while back < a.warmup_days:
                    dd -= timedelta(days=1)
                    if dd.weekday() >= 5:
                        continue
                    series = load_day(s, dd, a.rth_only) + series
                    back += 1
                today = load_day(s, d, a.rth_only)
                if len(resample(today, a.bar_minutes)) < 5:
                    missing.append(s)
                    continue
                bars = resample(series + today, a.bar_minutes)
                if len(bars) < MIN_BARS + 10:
                    missing.append(s)
                    continue
                fine = resample(today, a.exit_ema9_close) if a.exit_ema9_close else None
                day_tr += run_day(s, bars, a, d, fine)
            pnl = sum(t["pnl"] for t in day_tr)
            stops = sum(1 for t in day_tr if t["why"] == "stop")
            if not a.quiet:
                print(f"\n{d} ({how}; {len(syms)} names{', no data: ' + ' '.join(missing) if missing else ''})")
                print(f"  trades {len(day_tr):3d}  stopped {stops:3d}  other {len(day_tr) - stops:3d}  "
                      f"P&L {pnl:9.2f}  R {pnl / a.risk:6.2f}")
                by = defaultdict(float)
                for t in day_tr:
                    by[t["sym"]] += t["pnl"]
                if by:
                    print("  " + "  ".join(f"{s} {v:+.0f}" for s, v in sorted(by.items(), key=lambda kv: kv[1])))
            all_trades += [{**t, "day": d.isoformat()} for t in day_tr]
        d += timedelta(days=1)

    tot = sum(t["pnl"] for t in all_trades)
    wins = [t for t in all_trades if t["pnl"] > 0]
    if not a.quiet and len(all_trades) and (end - start).days > 40:
        months = defaultdict(lambda: [0, 0.0])
        for t in all_trades:
            m = months[t["day"][:7]]; m[0] += 1; m[1] += t["pnl"]
        print("\nby month:  " + "  ".join(f"{m} {v[0]}t {v[1]:+.0f}" for m, v in sorted(months.items())))
        years = defaultdict(lambda: [0, 0.0])
        for t in all_trades:
            y = years[t["day"][:4]]; y[0] += 1; y[1] += t["pnl"]
        print("by year:   " + "  ".join(f"{y} {v[0]}t {v[1]:+.0f} ({v[1] / a.risk:+.1f}R)" for y, v in sorted(years.items())))
    why = defaultdict(int)
    for t in all_trades:
        why[t["why"]] += 1
    days = defaultdict(float)
    for t in all_trades:
        days[t["day"]] += t["pnl"]
    print(f"{'WEEK' if not a.quiet else flags or 'base':28} trades {len(all_trades):4d}  win {len(wins) / len(all_trades) * 100 if all_trades else 0:5.1f}%  "
          f"P&L {tot:9.2f}  R {tot / a.risk:6.2f}  exits {dict(why)}  days+ {sum(1 for v in days.values() if v > 0)}/{len(days)}")
    if not a.quiet:
        by = defaultdict(float)
        for t in all_trades:
            by[t["sym"]] += t["pnl"]
        print("by ticker: " + "  ".join(f"{s} {v:+.0f}" for s, v in sorted(by.items(), key=lambda kv: kv[1])))
    if a.json:
        Path(a.json).write_text(json.dumps([{k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in t.items()}
                                            for t in all_trades], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
