#!/usr/bin/env python3
"""Charts and statistics for the SMB-format PlayBooks (docs/playbook/).

Run with the playbook venv:  ~/.venvs/playbook/bin/python docs/playbook/make_charts.py
Reads ~/market_data flat files through backtest/backtest_fl_week.py and the two trade lists under
backtest/results/, writes PNGs and stats.json into docs/playbook/build/.
"""
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backtest"))
from backtest_fl_week import load_day, resample, indicator_series  # noqa: E402
from backtest_sma34_trend import premarket, trading_days, true_range_atr  # noqa: E402

OUT = ROOT / "docs/playbook/build"
OUT.mkdir(parents=True, exist_ok=True)
RISK = 75.0
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.facecolor": "white", "axes.facecolor": "white"})
UP, DOWN, GREY = "#2e7d32", "#c62828", "#666666"
HM = matplotlib.dates.DateFormatter("%H:%M")


def naive(t):
    """Plot in wall-clock Eastern time: matplotlib converts aware datetimes to UTC."""
    return t.replace(tzinfo=None)


def at(d, hhmm):
    return matplotlib.dates.datestr2num(f"{d} {hhmm}")


def candles(ax, bars, width_min):
    w = width_min / (24 * 60) * 0.7
    for b in bars:
        x = matplotlib.dates.date2num(naive(b["t"]))
        col = UP if b["c"] >= b["o"] else DOWN
        ax.plot([x, x], [b["lo"], b["h"]], color=col, lw=0.8)
        ax.add_patch(Rectangle((x - w / 2, min(b["o"], b["c"])), w, abs(b["c"] - b["o"]) or 0.01,
                               facecolor=col, edgecolor=col, lw=0.6))
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(HM)


def series_for(sym, d, minutes, rth_only, warm_days):
    days = trading_days(date(d.year, d.month, 1) if d.day > 8 else date(d.year, d.month - 1 or 12, 1), d)
    idx = days.index(d)
    bars = []
    for x in days[max(0, idx - warm_days):idx + 1]:
        bars += load_day(sym, x, rth_only)
    bars = resample(bars, minutes)
    E9, S34, _, _ = indicator_series(bars, 1)
    return bars, E9, S34, true_range_atr(bars)


def annotate(ax, x, y, text, dy):
    ax.annotate(text, xy=(x, y), xytext=(0, dy), textcoords="offset points", ha="center", fontsize=9,
                arrowprops=dict(arrowstyle="->", color="black"))


def chart_sma34(ex, fname):
    sym, d = ex["sym"], date.fromisoformat(ex["day"])
    bars, E9, S34, ATR = series_for(sym, d, 15, False, 4)
    today = [i for i, b in enumerate(bars) if b["t"].date() == d and (b["t"].hour, b["t"].minute) < (16, 0)]
    pre = [i for i in today if (bars[i]["t"].hour, bars[i]["t"].minute) < (9, 30)]
    j = pre[-1]
    pm_vwap, _ = premarket(sym, d)
    xs = [naive(bars[i]["t"]) for i in today]
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=130)
    candles(ax, [bars[i] for i in today], 15)
    ax.plot(xs, [E9[i] for i in today], color="#1565c0", lw=1.4, label="9-EMA (15m, extended hours)")
    ax.plot(xs, [S34[i] for i in today], color="#ef6c00", lw=1.6, label="34-SMA (15m, extended hours)")
    ax.axhline(pm_vwap, color="#6a1b9a", lw=1.2, ls="--", label=f"premarket VWAP {pm_vwap:.2f}")
    ax.axvline(at(d, "09:30"), color=GREY, lw=0.8, ls=":")
    ax.axhline(ex["entry"], color="black", lw=1.0, ls="-.", label=f"resting limit at the pre-open 34-SMA {ex['entry']:.2f}")
    ax.axhline(ex["stop"], color=DOWN, lw=1.0, ls=":", label=f"stop 1.0×ATR {ex['stop']:.2f}")
    annotate(ax, at(d, ex["entry_t"]), ex["entry"], f"fill {ex['entry_t']}", -30)
    annotate(ax, at(d, ex["exit_t"]), ex["exit"], f"exit {ex['exit_t']} ({ex['reason']}) {ex['exit']:.2f}", 26)
    ax.set_title(f"{sym} {d} — 15-minute, extended hours · pre-open read at {bars[j]['t']:%H:%M}: 9-EMA {E9[j]:.2f} "
                 f"{'<' if E9[j] < pm_vwap else '>'} PM VWAP {pm_vwap:.2f} → {ex['side']} · 34-SMA {S34[j]:.2f} · ATR(14) {ATR[j]:.2f}",
                 fontsize=9.5, loc="left")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_ylabel("price")
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)


def chart_minutes(sym, d, start, end, lines, marks, title, fname):
    m = [b for b in load_day(sym, d, False) if start <= f"{b['t']:%H:%M}" < end]
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=130)
    candles(ax, m, 1)
    for y, lab, col, ls in lines:
        ax.axhline(y, color=col, lw=1.0, ls=ls, label=lab)
    for hhmm, y, text, dy in marks:
        annotate(ax, at(d, hhmm), y, text, dy)
    ax.set_title(title, fontsize=9.5, loc="left")
    ax.legend(loc="best", fontsize=8, frameon=False)
    ax.set_ylabel("price")
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)


def chart_fl(ex, fname):
    sym, d = ex["sym"], date.fromisoformat(ex["day"])
    bars, E9, S34, ATR = series_for(sym, d, 15, True, 4)
    today = [i for i, b in enumerate(bars) if b["t"].date() == d]
    xs = [naive(bars[i]["t"]) for i in today]
    fig, ax = plt.subplots(figsize=(11, 5.2), dpi=130)
    candles(ax, [bars[i] for i in today], 15)
    ax.plot(xs, [E9[i] for i in today], color="#1565c0", lw=1.4, label="9-EMA (15m, regular hours)")
    ax.plot(xs, [S34[i] for i in today], color="#ef6c00", lw=1.6, label="34-SMA (15m, regular hours)")
    stop0 = ex["entry"] - ex["risk"] if ex["side"] == "LONG" else ex["entry"] + ex["risk"]
    ax.axhline(ex["entry"], color="black", lw=1.0, ls="-.", label=f"entry {ex['entry']:.2f} (open of the bar after the cross, +0.15 slip)")
    ax.axhline(stop0, color=DOWN, lw=1.0, ls=":", label=f"initial stop 0.75×ATR {stop0:.2f}, to breakeven at +0.5R")
    et, xt = ex["entry_t"][11:16], ex["exit_t"][11:16]
    sig = bars[today[[bars[i]["t"].strftime("%H:%M") for i in today].index(et)] - 1]["t"].strftime("%H:%M")
    annotate(ax, at(d, sig), ex["entry"], f"cross on the {sig} bar", -30)
    annotate(ax, at(d, et), ex["entry"], f"entry {et}", -46)
    annotate(ax, at(d, xt), ex["exit"], f"exit {xt} ({ex['why']}) {ex['exit']:.2f}", 26)
    ax.set_title(f"{sym} {d} — 15-minute, regular hours · 9-EMA crosses the 34-SMA on the {sig} bar with volume above 1.5× "
                 f"the 20-bar average → {ex['side']}", fontsize=9.5, loc="left")
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.set_ylabel("price")
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)
    return sig, stop0


def chart_index(sym, d, fname, note):
    bars = resample(load_day(sym, d, True), 15)
    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=130)
    candles(ax, bars, 15)
    o, c = bars[0]["o"], bars[-1]["c"]
    ax.set_title(f"${sym} {d} — 15-minute, regular hours · open {o:.2f} close {c:.2f} ({(c / o - 1) * 100:+.2f}%) · {note}",
                 fontsize=9.5, loc="left")
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)
    return o, c


def equity(trades, r_of, fname, title):
    daily = defaultdict(float)
    for t in trades:
        daily[t["day"]] += r_of(t)
    xs, ys, eq = [], [], 0.0
    for dd in sorted(daily):
        eq += daily[dd]; xs.append(date.fromisoformat(dd)); ys.append(eq)
    peak = dd_max = 0.0
    for y in ys:
        peak = max(peak, y); dd_max = max(dd_max, peak - y)
    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=130)
    ax.plot(xs, ys, color="#1565c0", lw=1.5)
    ax.fill_between(xs, ys, 0, color="#1565c0", alpha=0.08)
    ax.set_title(f"{title} · cumulative R, 1R = $75 · max drawdown {dd_max:.1f}R", fontsize=9.5, loc="left")
    ax.set_ylabel("R")
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)
    return dd_max


def summarise(trades, r_of):
    rs = [r_of(t) for t in trades]
    wins = [r for r in rs if r > 0]; losses = [r for r in rs if r < 0]
    by_year = defaultdict(float)
    daily = defaultdict(float)
    for t, r in zip(trades, rs):
        by_year[t["day"][:4]] += r; daily[t["day"]] += r
    vals = list(daily.values()) + [0.0] * max(0, 754 - len(daily))
    return dict(trades=len(rs), wr=len(wins) / len(rs), r=sum(rs), per=sum(rs) / len(rs),
                avg_win=statistics.mean(wins), avg_loss=statistics.mean(losses), n_win=len(wins), n_loss=len(losses),
                n_flat=len(rs) - len(wins) - len(losses), by_year={k: round(v, 1) for k, v in sorted(by_year.items())},
                sharpe=statistics.mean(vals) / statistics.pstdev(vals) * 252 ** 0.5,
                by_hour={k: round(v, 1) for k, v in sorted(
                    defaultdict(float, {}).items())})


def main():
    R = ROOT / "backtest/results"
    s = json.load(open(R / "sma34-3y-preopen-ext-ema-s10.json"))["trades"]
    f = json.load(open(R / "fl-3y-15m-improved-11:00-intraday.json"))
    f = f["trades"] if isinstance(f, dict) else f

    ex_s = next(t for t in s if t["day"] == "2026-05-11" and t["sym"] == "RKLB")
    ex_f = next(t for t in f if t["day"] == "2026-08-27" and t["sym"] == "MSTR")
    d_s, d_f = date.fromisoformat(ex_s["day"]), date.fromisoformat(ex_f["day"])

    chart_sma34(ex_s, "sma34_example.png")
    pm_vwap, _ = premarket(ex_s["sym"], d_s)
    chart_minutes(ex_s["sym"], d_s, "09:00", "11:00",
                  [(ex_s["entry"], f"resting limit {ex_s['entry']:.2f}", "black", "-."),
                   (ex_s["stop"], f"stop {ex_s['stop']:.2f}", DOWN, ":"), (pm_vwap, f"PM VWAP {pm_vwap:.2f}", "#6a1b9a", "--")],
                  [(ex_s["entry_t"], ex_s["entry"], f"fill {ex_s['entry_t']} at the limit", -30)],
                  f"{ex_s['sym']} {d_s} — 1-minute, 09:00 to 11:00: the order is filled by the opening drive and the stop holds",
                  "sma34_fill.png")
    sig, stop0 = chart_fl(ex_f, "fl_example.png")
    chart_minutes(ex_f["sym"], d_f, "09:30", "11:30",
                  [(ex_f["entry"], f"entry {ex_f['entry']:.2f}", "black", "-."), (stop0, f"initial stop {stop0:.2f}", DOWN, ":")],
                  [(ex_f["entry_t"][11:16], ex_f["entry"], f"entry {ex_f['entry_t'][11:16]} at the bar open", -30)],
                  f"{ex_f['sym']} {d_f} — 1-minute, 09:30 to 11:30: the {sig} bar crosses, entry at the next open, breakeven after +0.5R",
                  "fl_fill.png")
    idx = {}
    for sym in ("SPY", "QQQ"):
        idx[f"sma34_{sym}"] = chart_index(sym, d_s, f"sma34_{sym.lower()}.png", f"context for the {ex_s['sym']} {ex_s['side'].lower()}")
        idx[f"fl_{sym}"] = chart_index(sym, d_f, f"fl_{sym.lower()}.png", f"context for the {ex_f['sym']} {ex_f['side'].lower()}")
    dd_s = equity(s, lambda t: t["r"], "sma34_equity.png", "34-SMA premarket trend · pre-open order, 1.0×ATR stop, 9-EMA close exit · 14 names")
    dd_f = equity(f, lambda t: t["pnl"] / RISK, "fl_equity.png", "Fashionably Late · 15m, 0.75×ATR + breakeven, entries 09:45–11:00, single stocks · gate corrected 2026-09-27")

    st = dict(
        sma34=dict(**summarise(s, lambda t: t["r"]), dd=dd_s,
                   exits={k: sum(1 for t in s if t["reason"] == k) for k in ("stop", "ema9", "eod")}, example=ex_s),
        fl=dict(**summarise(f, lambda t: t["pnl"] / RISK), dd=dd_f,
                exits={k: sum(1 for t in f if t["why"] == k) for k in ("stop", "eod")}, example=ex_f, signal_bar=sig, stop0=stop0),
        index=idx,
    )
    (OUT / "stats.json").write_text(json.dumps(st, indent=1, default=str))
    for k in ("sma34", "fl"):
        print(k, {kk: vv for kk, vv in st[k].items() if kk not in ("example",)})


if __name__ == "__main__":
    main()
