#!/usr/bin/env python3
"""34-SMA pullback in the premarket trend, 15-minute bars — David's second setup (2026-09-27).

Rule under test
  Universe   medium/large-cap single stocks whose premarket volume (04:00-09:29) is at least
             --pm-vol-mult times the median premarket volume of the prior 20 trading days.
  Direction  9-EMA (15-minute) relative to the day's premarket VWAP at the last completed
             bar: below -> SHORT, above -> LONG.  Re-read every 15-minute bar.
  Entry      limit order at the last completed 15-minute bar's 34-SMA, good for the next
             15-minute window, only when the last close is on the trade side of the SMA (a
             pullback to the level, not a break of it) and the 9-EMA is on the trade side too.
             Filled when a 1-minute bar touches the level; a minute that opens through the
             level fills at its open (a limit never fills worse than its price).
  Stop       --stop-mult x ATR(14, true range) on 15-minute bars (default 0.75).
  Target     --target-r x stop distance (default 1.8; 0 = hold to the close).
             Same-minute stop and target -> stop.
  Session    entries from --gate (09:45) to --last-entry (15:00), flat at --eod (15:55).
             Positions are only managed on regular-hours prints (09:30-16:00).
  Sizing     1R = --risk dollars, shares = risk / stop distance, capped at --max-shares.

Bars: 15-minute, all sessions from 04:00 by default, or regular hours only with --rth-only
(that is what a DAS chart without extended hours shows; the two give very different results,
see docs/forward-tests/sma34-trend-3y.md).  --warmup-days prior days are prepended so the
34-SMA is warm at the open.  Every indicator used for an entry, stop or target comes from bars
completed BEFORE the 15-minute window in which the fill happens.

Data: ~/market_data/{T}/{T}_{date}_minute.csv (Massive.com flat files).
"""
from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from backtest_fl_week import RTH_OPEN, indicator_series, load_day, resample

STOCKS = "AMD,BB,CRWD,DELL,DRI,INTC,IONQ,META,MSTR,NVDA,RKLB,SMCI,TSLA,XOM"

_PM: dict = {}          # (sym, day) -> (pm_vwap, pm_volume)
_BARS: dict = {}        # (sym, day, rth_only, minutes) -> resampled bars


def trading_days(start: date, end: date) -> list[date]:
    d, out = start, []
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


def premarket(sym: str, d: date) -> tuple[float, float]:
    """(PM VWAP, PM volume) from the day's 1-minute bars before 09:30, memoised."""
    key = (sym, d)
    if key not in _PM:
        pv = v = 0.0
        for b in load_day(sym, d):
            if (b["t"].hour, b["t"].minute) >= RTH_OPEN:
                break
            pv += b["c"] * b["v"]
            v += b["v"]
        _PM[key] = ((pv / v if v else 0.0), v)
    return _PM[key]


def day_bars(sym: str, d: date, rth_only: bool, minutes: int) -> list[dict]:
    """One day's bars resampled to `minutes`, memoised.  Windows never span days, so
    concatenating per-day lists equals resampling the concatenation."""
    key = (sym, d, rth_only, minutes)
    if key not in _BARS:
        _BARS[key] = resample(load_day(sym, d, rth_only), minutes)
    return _BARS[key]


def true_range_atr(bars: list[dict], n: int = 14) -> list:
    """Rolling mean true range over the last n bars, atr[i] over bars[:i+1]."""
    trs = [bars[0]["h"] - bars[0]["lo"]] + [
        max(b["h"] - b["lo"], abs(b["h"] - p["c"]), abs(b["lo"] - p["c"])) for p, b in zip(bars, bars[1:])]
    atr: list = [None] * len(bars)
    rs = 0.0
    for i, tr in enumerate(trs):
        rs += tr
        if i >= n:
            rs -= trs[i - n]
        if i >= n - 1:
            atr[i] = rs / n
    return atr


def run_day(sym: str, day: date, idx: int, days: list[date], a) -> tuple[list[dict], str]:
    """Trades on `day` (days[idx]).  Returns (trades, skip_reason) with skip_reason '' when
    the day passed the premarket filter."""
    today = load_day(sym, day)
    if not today:
        return [], "no data"
    pm_vwap, pm_vol = premarket(sym, day)
    if pm_vol <= 0:
        return [], "no premarket"
    hist = [v for v in (premarket(sym, d)[1] for d in days[max(0, idx - a.baseline_days):idx]) if v > 0]
    if len(hist) < a.baseline_days // 2:
        return [], "short baseline"
    ratio = pm_vol / statistics.median(hist)
    if ratio < a.pm_vol_mult:
        return [], "quiet premarket"
    if a.pm_vol_max and ratio > a.pm_vol_max:
        return [], "premarket above max"

    bars15: list[dict] = []
    for d in days[max(0, idx - a.warmup_days):idx + 1]:
        bars15 += day_bars(sym, d, a.rth_only, a.bar_minutes)
    if len(bars15) < 35:
        return [], "short history"
    E9, S34, _, _ = indicator_series(bars15, 1)
    ATR = true_range_atr(bars15)
    start_of = {b["t"]: i for i, b in enumerate(bars15)}
    rth = load_day(sym, day, True)                    # manage only on regular-hours prints

    trades: list[dict] = []

    def record(pos: dict, exit_t: datetime, px: float, reason: str) -> None:
        sgn = 1 if pos["side"] == "LONG" else -1
        pnl = (px - pos["entry"]) * pos["qty"] * sgn
        trades.append(dict(sym=sym, day=day.isoformat(), side=pos["side"], qty=pos["qty"],
                           entry_t=pos["t"].strftime("%H:%M"), entry=round(pos["entry"], 4),
                           stop=round(pos["stop"], 4), target=round(pos["target"], 4),
                           exit_t=exit_t.strftime("%H:%M"), exit=round(px, 4), reason=reason,
                           pnl=round(pnl, 2), r=round(pnl / a.risk, 3),
                           r_plan=round(pnl / (pos["qty"] * pos["dist"]), 3),
                           pm_ratio=round(ratio, 2), atr=round(pos["atr"], 4)))

    def stop_price(pos: dict, m: dict) -> float:
        """Stop fill: at the stop, or at the open when the minute gaps through it; plus slippage."""
        if pos["side"] == "LONG":
            return min(pos["stop"], m["o"]) - a.stop_slip
        return max(pos["stop"], m["o"]) + a.stop_slip

    def stopped(pos: dict, m: dict) -> bool:
        return m["lo"] <= pos["stop"] if pos["side"] == "LONG" else m["h"] >= pos["stop"]

    pos = None
    entries = 0
    filled_key = None                # window that already produced a fill
    ctx = {"key": None, "ok": False}  # setup for the current 15-minute window, from bar j
    for m in rth:
        t = m["t"]
        hm = (t.hour, t.minute)
        key = t.replace(minute=t.minute - t.minute % a.bar_minutes, second=0, microsecond=0)
        if ctx["key"] != key:
            i = start_of.get(key)
            j = (i - 1) if i is not None else None          # last COMPLETED bar
            ctx = {"key": key, "ok": False}
            if j is not None and j >= 34 and S34[j] and E9[j] and ATR[j] and ATR[j] > 0:
                side = "SHORT" if E9[j] < pm_vwap else "LONG"
                last, level, atr = bars15[j]["c"], S34[j], ATR[j]
                below = last < level and E9[j] < level
                above = last > level and E9[j] > level
                shallow = a.max_pull_atr <= 0 or abs(last - level) <= a.max_pull_atr * atr
                wanted = not a.side or side == a.side
                if ((side == "SHORT" and below) or (side == "LONG" and above)) and shallow and wanted:
                    ctx.update(ok=True, side=side, level=level, atr=atr)
        if pos:                                              # manage: stop, target, eod
            hit_tgt = a.target_r > 0 and (m["h"] >= pos["target"] if pos["side"] == "LONG" else m["lo"] <= pos["target"])
            if a.be_after > 0 and not pos.get("be"):
                fav = (m["h"] - pos["entry"]) if pos["side"] == "LONG" else (pos["entry"] - m["lo"])
                if fav >= a.be_after * pos["dist"]:
                    pos["stop"] = pos["entry"]; pos["be"] = True      # from the next minute on
            if stopped(pos, m):                              # same minute both -> stop
                record(pos, t, stop_price(pos, m), "stop"); pos = None
            elif hit_tgt:
                record(pos, t, pos["target"], "target"); pos = None
            elif hm >= a.eod_hm:
                record(pos, t, m["o"], "eod"); pos = None
            continue
        if not ctx["ok"] or key == filled_key or entries >= a.max_entries:
            continue
        if hm < a.gate_hm or hm >= a.last_entry_hm or hm >= a.eod_hm:
            continue
        level = ctx["level"]
        if ctx["side"] == "SHORT":
            fill = max(level, m["o"]) if m["h"] >= level + a.fill_through else None
        else:
            fill = min(level, m["o"]) if m["lo"] <= level - a.fill_through else None
        if fill is None:
            continue
        dist = a.stop_mult * ctx["atr"]
        qty = min(a.max_shares, int(a.risk / dist)) if dist > 0 else 0
        if qty < 1:
            continue
        sgn = 1 if ctx["side"] == "LONG" else -1
        pos = dict(side=ctx["side"], entry=fill, qty=qty, dist=dist, atr=ctx["atr"], t=t,
                   stop=fill - sgn * dist, target=fill + sgn * dist * a.target_r)
        entries += 1
        filled_key = key
        # Fill minute: only the stop is checked, never the target (conservative; a low
        # beyond the stop must have traded through the fill price first).
        if stopped(pos, m):
            record(pos, t, stop_price(pos, m), "stop"); pos = None
    if pos:                                   # half day: no 15:55 bar, close on the last RTH bar
        record(pos, rth[-1]["t"], rth[-1]["c"], "eod")
    return trades, ""


def stats(trades: list[dict], risk: float, n_days: int) -> dict:
    """Sharpe is over ALL trading days in the span (flat days count as zero), annualised."""
    if not trades:
        return dict(n=0, wr=0.0, pnl=0.0, r=0.0, per=0.0, dd=0.0, sharpe=0.0, r_plan=0.0)
    pnl = sum(t["pnl"] for t in trades)
    daily: dict[str, float] = defaultdict(float)
    for t in trades:
        daily[t["day"]] += t["pnl"]
    eq = peak = dd = 0.0
    for d in sorted(daily):
        eq += daily[d]; peak = max(peak, eq); dd = max(dd, peak - eq)
    vals = list(daily.values()) + [0.0] * max(0, n_days - len(daily))
    sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
    return dict(n=len(trades), wr=sum(t["pnl"] > 0 for t in trades) / len(trades), pnl=pnl, r=pnl / risk,
                per=pnl / risk / len(trades), dd=dd / risk,
                sharpe=(statistics.mean(vals) / sd * 252 ** 0.5) if sd else 0.0,
                r_plan=statistics.mean(t["r_plan"] for t in trades))


def line(label: str, s: dict) -> str:
    return (f"{label:<28} {s['n']:>5}  wr {s['wr']*100:5.1f}%  pnl {s['pnl']:>10,.0f}  R {s['r']:>+8.1f}"
            f"  /trade {s['per']:>+6.3f}R  plan {s['r_plan']:>+6.3f}R  maxDD {s['dd']:>5.1f}R  sharpe {s['sharpe']:>5.2f}")


def hm(s: str) -> tuple[int, int]:
    t = datetime.strptime(s, "%H:%M")
    return t.hour, t.minute


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--start", default="2023-09-25")
    ap.add_argument("--end", default="2026-09-25")
    ap.add_argument("--symbols", default=STOCKS, help="comma list (default: the 14 medium/large-cap stocks)")
    ap.add_argument("--exclude", default="", help="comma list to drop")
    ap.add_argument("--pm-vol-mult", type=float, default=2.0, help="PM volume vs prior-20-day median")
    ap.add_argument("--pm-vol-max", type=float, default=0.0, help="skip when the PM ratio is above this (0 = off)")
    ap.add_argument("--baseline-days", type=int, default=20)
    ap.add_argument("--bar-minutes", type=int, default=15)
    ap.add_argument("--warmup-days", type=int, default=4)
    ap.add_argument("--rth-only", action="store_true", help="SMA/EMA/ATR on regular-hours bars only")
    ap.add_argument("--stop-mult", type=float, default=0.75, help="stop distance in ATR(14, 15m)")
    ap.add_argument("--target-r", type=float, default=1.8, help="take profit in R (0 = none, hold to eod)")
    ap.add_argument("--be-after", type=float, default=0.0, help="move stop to entry after +R in favour (0 = off)")
    ap.add_argument("--max-pull-atr", type=float, default=0.0, help="skip when last close is more than N ATR from the level (0 = off)")
    ap.add_argument("--gate", default="09:45")
    ap.add_argument("--last-entry", default="15:00")
    ap.add_argument("--eod", default="15:55")
    ap.add_argument("--risk", type=float, default=75.0)
    ap.add_argument("--max-shares", type=int, default=300)
    ap.add_argument("--max-entries", type=int, default=1, help="entries per name per day")
    ap.add_argument("--fill-through", type=float, default=0.0, help="require the minute to trade this far past the level")
    ap.add_argument("--stop-slip", type=float, default=0.0, help="adverse slippage per share on stop fills")
    ap.add_argument("--side", default="", choices=["", "LONG", "SHORT"], help="take setups of one side only")
    ap.add_argument("--json", help="write trades here")
    ap.add_argument("--quiet", action="store_true", help="totals line only")
    a = ap.parse_args()
    a.gate_hm, a.last_entry_hm, a.eod_hm = hm(a.gate), hm(a.last_entry), hm(a.eod)

    syms = [s for s in a.symbols.split(",") if s and s not in set(a.exclude.split(","))]
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    days = trading_days(start - timedelta(days=45), end)      # room for baseline + warm-up
    trades: list[dict] = []
    skips: Counter = Counter()
    active = 0
    n_days = 0
    for idx, d in enumerate(days):
        if d < start:
            continue
        n_days += 1
        for s in syms:
            tr, skip = run_day(s, d, idx, days, a)
            if skip:
                skips[skip] += 1
            else:
                active += 1
            trades += tr
    trades.sort(key=lambda t: (t["day"], t["entry_t"]))

    print(line(f"TOTAL {a.start}..{a.end}", stats(trades, a.risk, n_days)))
    if a.quiet:
        return 0
    print(f"symbol-days: {sum(skips.values()) + active}, passed PM filter: {active}, skips: {dict(skips)}")
    print("exits: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(t["reason"] for t in trades).items())))

    def split(keyf, title, per_year_days=False):
        groups: dict = defaultdict(list)
        for t in trades:
            groups[keyf(t)].append(t)
        print(f"\n{title}")
        for k in sorted(groups):
            nd = sum(1 for d in days if d >= start and d.isoformat()[:4] == k) if per_year_days else n_days
            print(line(f"  {k}", stats(groups[k], a.risk, nd)))
    split(lambda t: t["day"][:4], "by year", per_year_days=True)
    split(lambda t: t["side"], "by side")
    split(lambda t: t["entry_t"][:2] + ":00", "by entry hour")
    split(lambda t: ("PM ratio 2-3" if t["pm_ratio"] < 3 else "PM ratio 3-5" if t["pm_ratio"] < 5 else "PM ratio 5+")
          if t["pm_ratio"] >= 2 else "PM ratio <2", "by premarket ratio")
    split(lambda t: t["sym"], "by ticker")
    if a.json:
        Path(a.json).parent.mkdir(parents=True, exist_ok=True)
        Path(a.json).write_text(json.dumps(dict(args=vars(a), trades=trades), indent=1, default=str))
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
