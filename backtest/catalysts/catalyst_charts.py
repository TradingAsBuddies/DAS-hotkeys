#!/usr/bin/env python3
"""Equity curves by catalyst tag and the catalyst-excluded numbers for the report.

Run with the playbook venv after catalysts.py:
  ~/.venvs/playbook/bin/python backtest/catalysts/catalyst_charts.py
Writes docs/playbook/build/{sma34,fl}_catalyst.png and prints the exclusion table.
Slippage is applied as the backtesters do: 5 cents per share on stop fills only.
"""
from __future__ import annotations

import json
import random
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "backtest/catalysts"
OUT = ROOT / "docs/playbook/build"
RISK, SLIP = 75.0, 0.05
CAT = {"earnings", "8-K"}


def load():
    cal = {tk: {date.fromisoformat(d): tag for d, tag in v.items()} for tk, v in json.load(open(HERE / "calendar.json")).items()}
    s = json.load(open(ROOT / "backtest/results/sma34-3y-preopen-ext-ema-s10.json"))["trades"]
    f = json.load(open(ROOT / "backtest/results/fl-3y-15m-improved-11:00-intraday.json"))
    f = f["trades"] if isinstance(f, dict) else f
    for t in s:
        t["_r"], t["_stop"] = t["r"], t["reason"] == "stop"
    for t in f:
        t["_r"], t["_stop"] = t["pnl"] / RISK, t["why"] == "stop" and abs(t["exit"] - t["entry"]) > 1e-9  # breakeven exits: no stop slip counted? keep as stop
        t["_stop"] = t["why"] == "stop"
    for t in s + f:
        t["_tag"] = cal.get(t["sym"], {}).get(date.fromisoformat(t["day"]), "none")
        t["_slip"] = (SLIP * t["qty"] / RISK) if t["_stop"] else 0.0
    return s, f


def summary(trades):
    daily = defaultdict(float)
    for t in trades:
        daily[t["day"]] += t["_r"]
    eq = peak = dd = 0.0
    for d in sorted(daily):
        eq += daily[d]; peak = max(peak, eq); dd = max(dd, peak - eq)
    r = sum(t["_r"] for t in trades)
    return dict(n=len(trades), r=r, per=r / len(trades), dd=dd, slip=r - sum(t["_slip"] for t in trades),
                wr=sum(t["_r"] > 0 for t in trades) / len(trades))


def curve(name, trades, title):
    fig, ax = plt.subplots(figsize=(11, 4.2), dpi=130)
    for label, pick, col in (("earnings or other 8-K reaction days", lambda t: t["_tag"] in CAT, "#c62828"),
                             ("all other days", lambda t: t["_tag"] not in CAT, "#1565c0")):
        sub = [t for t in trades if pick(t)]
        daily = defaultdict(float)
        for t in sub:
            daily[t["day"]] += t["_r"]
        xs, ys, eq = [], [], 0.0
        for d in sorted(daily):
            eq += daily[d]; xs.append(date.fromisoformat(d)); ys.append(eq)
        ax.plot(xs, ys, color=col, lw=1.5, label=f"{label} ({len(sub)} trades, {ys[-1]:+.0f}R)")
    ax.set_title(f"{title} · cumulative R by catalyst tag (SEC EDGAR 8-K item 2.02 and other 8-Ks)", fontsize=9.5, loc="left")
    ax.legend(loc="upper left", fontsize=8, frameon=False); ax.set_ylabel("R")
    fig.tight_layout(); fig.savefig(OUT / f"{name}_catalyst.png"); plt.close(fig)


def main():
    s, f = load()
    curve("sma34", s, "34-SMA premarket trend")
    curve("fl", f, "Fashionably Late (15m, corrected)")
    random.seed(7)
    for name, trades in (("34-SMA", s), ("FL", f)):
        print(f"\n{name}")
        for label, pick in (("all trades", lambda t: True), ("catalyst days only", lambda t: t["_tag"] in CAT),
                            ("catalyst days excluded", lambda t: t["_tag"] not in CAT)):
            x = summary([t for t in trades if pick(t)])
            print(f"  {label:<24} n {x['n']:>5}  wr {x['wr']*100:4.0f}%  R {x['r']:>+7.1f}  /trade {x['per']:>+6.3f}  maxDD {x['dd']:>5.1f}R  5c slip {x['slip']:>+7.1f}R")
        cat = [t["_r"] for t in trades if t["_tag"] in CAT]; allr = [t["_r"] for t in trades]
        obs, k, hits, N = statistics.mean(cat), len(cat), 0, 5000
        for _ in range(N):
            m = statistics.mean(random.sample(allr, k)); hits += (m >= obs) if obs > statistics.mean(allr) else (m <= obs)
        print(f"  permutation p for the catalyst subset: {hits / N:.3f}")


if __name__ == "__main__":
    main()
