#!/usr/bin/env python3
"""Catalyst attribution for the backtests: were the trades earnings or filing reactions?

Source: SEC EDGAR submissions API (data.sec.gov/submissions/CIK##########.json), cached under
backtest/catalysts/edgar/.  An 8-K with item 2.02 (Results of Operations) is an earnings release;
its reaction day is the filing day if it was accepted before 09:30 ET, else the next trading day.
Other tags: any other 8-K accepted in the 24 hours before the session ("8-K"), an S-3/424B/S-1
in that window ("offering"), a 10-Q/10-K in that window ("10-Q/K").  A trade day is tagged with
the highest-priority match: earnings > offering > 8-K > 10-Q/K > none.

Usage: python3 backtest/catalysts/catalysts.py [--refresh]
"""
from __future__ import annotations

import json
import statistics
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / "backtest/catalysts"
CACHE = HERE / "edgar"
CACHE.mkdir(exist_ok=True)
UA = "TradingAsBuddies research davdunc@gmail.com"
ET = ZoneInfo("America/New_York")
START = date(2023, 8, 1)
EXTRA_CIKS = {"XOM": ["0000034088"]}          # Exxon Mobil Corp before the 2026 holding-company CIK
RISK = 75.0


def fetch(url: str, dest: Path, refresh: bool) -> dict:
    if dest.exists() and not refresh:
        return json.loads(dest.read_text())
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
    dest.write_bytes(raw)
    time.sleep(0.15)
    return json.loads(raw)


def filings_for(cik: str, refresh: bool) -> list[dict]:
    sub = fetch(f"https://data.sec.gov/submissions/CIK{cik}.json", CACHE / f"CIK{cik}.json", refresh)
    blocks = [sub["filings"]["recent"]]
    for extra in sub["filings"].get("files", []):
        if extra.get("filingTo", "9999") >= START.isoformat():
            blocks.append(fetch(f"https://data.sec.gov/submissions/{extra['name']}", CACHE / extra["name"], refresh))
    out = []
    for b in blocks:
        for i in range(len(b["form"])):
            fd = b["filingDate"][i]
            if fd < START.isoformat():
                continue
            out.append(dict(form=b["form"][i], date=fd, accepted=b["acceptanceDateTime"][i], items=b.get("items", [""] * len(b["form"]))[i]))
    return out


def trading_days(start: date, end: date) -> list[date]:
    d, out = start, []
    while d <= end:
        if d.weekday() < 5:
            out.append(d)
        d += timedelta(days=1)
    return out


DAYS = trading_days(START, date(2026, 12, 31))


def next_session(d: date) -> date:
    for x in DAYS:
        if x > d:
            return x
    return d


def reaction_day(accepted: str) -> date:
    """Session in which the market first trades on a filing accepted at `accepted` (UTC ISO)."""
    t = datetime.fromisoformat(accepted.replace("Z", "+00:00")).astimezone(ET)
    d = t.date()
    if t.weekday() >= 5:
        return next_session(d)
    return d if (t.hour, t.minute) < (9, 30) else next_session(d)


def calendar(ciks: dict[str, str], refresh: bool) -> dict[str, dict[date, str]]:
    """ticker -> {session: tag}."""
    cal: dict[str, dict[date, str]] = defaultdict(dict)
    prio = {"earnings": 4, "offering": 3, "8-K": 2, "10-Q/K": 1}
    for tk, cik in ciks.items():
        rows = []
        for c in [cik] + EXTRA_CIKS.get(tk, []):
            try:
                rows += filings_for(c, refresh)
            except Exception as e:  # noqa: BLE001
                print(f"  {tk} CIK{c}: {e}", file=sys.stderr)
        for r in rows:
            form, items = r["form"], r["items"] or ""
            if form.startswith("8-K") and "2.02" in items:
                tag = "earnings"
            elif form.startswith(("S-3", "S-1", "424B", "F-3", "F-1")):
                tag = "offering"
            elif form.startswith(("8-K", "6-K")):
                tag = "8-K"
            elif form.startswith(("10-Q", "10-K", "20-F", "40-F")):
                tag = "10-Q/K"
            else:
                continue
            day = reaction_day(r["accepted"])
            if prio[tag] > prio.get(cal[tk].get(day, ""), 0):
                cal[tk][day] = tag
        n = sum(1 for v in cal[tk].values() if v == "earnings")
        print(f"  {tk}: {len(rows)} filings since {START}, {n} earnings sessions")
    return cal


def tag_trades(trades: list[dict], cal, r_of) -> list[tuple[str, float, bool]]:
    out = []
    for t in trades:
        d = date.fromisoformat(t["day"])
        tag = cal.get(t["sym"], {}).get(d, "none")
        out.append((tag, r_of(t), t))
    return out


def table(rows, title):
    g = defaultdict(list)
    for tag, r, _ in rows:
        g[tag].append(r)
    print(f"\n{title}")
    print(f"  {'tag':<10}{'trades':>7}{'share':>7}{'win':>7}{'R':>9}{'R/trade':>9}{'avg win':>9}{'avg loss':>9}")
    for tag in ("earnings", "offering", "8-K", "10-Q/K", "none"):
        rs = g.get(tag, [])
        if not rs:
            continue
        w = [x for x in rs if x > 0]; l = [x for x in rs if x < 0]
        print(f"  {tag:<10}{len(rs):>7}{len(rs)/len(rows)*100:>6.0f}%{len(w)/len(rs)*100:>6.0f}%{sum(rs):>+9.1f}{sum(rs)/len(rs):>+9.3f}"
              f"{(statistics.mean(w) if w else 0):>+9.2f}{(statistics.mean(l) if l else 0):>+9.2f}")
    return g


def yearly(rows, tag_set, label):
    by = defaultdict(float)
    for tag, r, t in rows:
        if tag in tag_set:
            by[t["day"][:4]] += r
    print(f"  {label}: " + ", ".join(f"{k} {v:+.0f}R" for k, v in sorted(by.items())))


def main():
    refresh = "--refresh" in sys.argv
    ciks = json.load(open(HERE / "ciks.json"))
    print("EDGAR filings:")
    cal = calendar(ciks, refresh)
    json.dump({tk: {d.isoformat(): tag for d, tag in v.items()} for tk, v in cal.items()},
              open(HERE / "calendar.json", "w"), indent=1)

    R = ROOT / "backtest/results"
    s = json.load(open(R / "sma34-3y-preopen-ext-ema-s10.json"))["trades"]
    f = json.load(open(R / "fl-3y-15m-improved-11:00-intraday.json"))
    f = f["trades"] if isinstance(f, dict) else f
    rs = tag_trades(s, cal, lambda t: t["r"])
    rf = tag_trades(f, cal, lambda t: t["pnl"] / RISK)
    gs = table(rs, "34-SMA premarket trend (pre-open order, 1.0xATR, 9-EMA exit), 733 trades")
    yearly(rs, {"earnings"}, "earnings days by year"); yearly(rs, {"none", "8-K", "10-Q/K", "offering"}, "all other days by year")
    gf = table(rf, "Fashionably Late (15m, corrected), 2,282 trades")
    yearly(rf, {"earnings"}, "earnings days by year"); yearly(rf, {"none", "8-K", "10-Q/K", "offering"}, "all other days by year")

    # how many of the 34-SMA qualifying symbol-days (premarket >= 2x) were earnings reactions?
    sys.path.insert(0, str(ROOT / "backtest"))
    from backtest_sma34_trend import premarket, trading_days as tdays
    days = tdays(date(2023, 8, 10), date(2026, 9, 25))
    test = [d for d in days if d >= date(2023, 9, 25)]
    q_total = q_earn = e_total = e_q = 0
    for tk in "AMD,BB,CRWD,DELL,DRI,INTC,IONQ,META,MSTR,NVDA,RKLB,SMCI,TSLA,XOM".split(","):
        for d in test:
            idx = days.index(d)
            pv = premarket(tk, d)[1]
            if pv <= 0:
                continue
            hist = [v for v in (premarket(tk, x)[1] for x in days[max(0, idx - 20):idx]) if v > 0]
            if len(hist) < 10:
                continue
            ratio = pv / statistics.median(hist)
            is_e = cal.get(tk, {}).get(d) == "earnings"
            e_total += is_e
            if ratio >= 2:
                q_total += 1; q_earn += is_e
            if is_e and ratio >= 2:
                e_q += 1
    print(f"\n34-SMA universe: {q_total} symbol-days passed the 2x premarket filter; {q_earn} of them were earnings reactions "
          f"({q_earn/q_total*100:.0f}%). Of {e_total} earnings sessions in the universe, {e_q} passed the filter ({e_q/e_total*100:.0f}%).")

    # top trades and their tags
    for name, rows in (("34-SMA", rs), ("FL", rf)):
        top = sorted(rows, key=lambda x: -x[1])[:15]
        print(f"\n{name} fifteen largest wins: " + ", ".join(f"{t['sym']} {t['day']} {r:+.1f}R [{tag}]" for tag, r, t in top))
        e_share = sum(r for tag, r, _ in top if tag == "earnings")
        print(f"  earnings share of the fifteen: {sum(1 for tag,_,_ in top if tag=='earnings')} trades, {e_share:+.1f}R")
    json.dump(dict(sma34=[(tag, r, t["sym"], t["day"]) for tag, r, t in rs], fl=[(tag, r, t["sym"], t["day"]) for tag, r, t in rf]),
              open(HERE / "tagged_trades.json", "w"))


if __name__ == "__main__":
    main()
