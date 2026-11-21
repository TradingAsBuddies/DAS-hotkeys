#!/usr/bin/env python3
"""HVC Watcher for DAS Trader — daily scan.

Port of Major Hayden's TradingView indicator (see NOTICE, docs/HVC-WATCHER.md).
Massive daily bars → HVC/HVE events + retained close rays → DAS:

  * Market Viewer lists  <DAS_ROOT>\\GamePlan\\HVC-Events-Today.txt / HVC-Touches-Today.txt
  * chart rays           --draw-window <chart name>   (DrawHorzLineWithPrice)
  * DAS price alerts     --alerts                     (NewAlertObj per retained ray)

    hvc_daily.py --symbols NVDA,SMCI,SPY --dry-run
    hvc_daily.py --symbols "/mnt/c/Cobra Trading_x64-Beta/GamePlan/GamePlan-Today.txt" \\
                 --draw-window hvc_chart --alerts

Nightly (systemd timer, see run_nightly.sh):
    hvc_daily.py --gameplan --symbols tools/hvc/watchlist.local.txt --chartbook --notion

Exit codes: 0 ok · 1 some symbols failed (data) or DAS reported script problems ·
3 Notion publish failed ·
2 DAS unreachable / login refused.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bars_massive  # noqa: E402
import das_out  # noqa: E402
import engine  # noqa: E402


def newest_gameplan(env: dict) -> Path:
    """Newest dated GamePlan-YYYY-MM-DD.txt (not GamePlan-Today.txt, which may be stale)."""
    d = das_out.gameplan_dir(env)
    files = sorted(d.glob("GamePlan-????-??-??.txt"))
    if not files:
        raise FileNotFoundError(f"no GamePlan-YYYY-MM-DD.txt in {d}")
    return files[-1]


def parse_symbols(arg: str) -> list[str]:
    p = Path(arg)
    raw = p.read_text().split() if p.exists() else arg.replace(",", " ").split()
    seen, out = set(), []
    for s in raw:
        s = s.strip().upper()
        if s and not s.startswith("#") and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def scan(symbol: str, a, env: dict) -> dict:
    bars = bars_massive.load_cache(symbol) if a.offline else bars_massive.fetch_daily(symbol, a.years, env=env)
    bars = bars_massive.trim_years(bars, a.hve_lookback_years)
    if not bars:
        raise bars_massive.MassiveError(f"{symbol}: Massive returned no bars (unknown or delisted ticker?)")
    r = engine.compute(bars, sma_length=a.sma, mult=a.mult, ray_limit=a.ray_limit,
                       hve_min_bars=a.hve_warmup)
    i = r.last
    last = bars[i]
    event = "HVE" if r.hve[i] else "HVC" if r.hvc[i] else None
    return {
        "symbol": symbol, "bars": len(bars), "since": bars[0]["date"], "date": last["date"],
        "confirmed": last.get("confirmed", True), "close": last["c"], "volume": last["v"],
        "sma": r.sma[i], "multiplier": r.multiplier[i],
        "event": event, "touched": r.touched[i],
        "rays": [asdict(x) for x in r.rays],
        "_rays": r.rays,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--symbols", action="append", default=[],
                    help="comma/space list, or a file with one ticker per line (repeatable)")
    ap.add_argument("--gameplan", action="store_true",
                    help="add tickers from the newest <DAS_ROOT>\\GamePlan\\GamePlan-YYYY-MM-DD.txt")
    ap.add_argument("--sma", type=int, default=engine.DEFAULT_SMA_LENGTH)
    ap.add_argument("--mult", type=float, default=engine.DEFAULT_MULT_DAILY)
    ap.add_argument("--ray-limit", type=int, default=engine.DEFAULT_RAY_LIMIT)
    ap.add_argument("--years", type=int, default=20, help="history to fetch from Massive")
    ap.add_argument("--hve-lookback-years", type=int, default=None,
                    help="limit history used for HVE (approximate TradingView's loaded history)")
    ap.add_argument("--hve-warmup", type=int, default=252, metavar="BARS",
                    help="no HVE in the first N bars of history (default 252 ≈ 1y; 0 = exact Pine parity)")
    ap.add_argument("--offline", action="store_true", help="use cached bars only")
    ap.add_argument("--draw-window", metavar="CHART", help="named DAS chart window to draw rays in")
    ap.add_argument("--clear-lines", action="store_true",
                    help="RemoveAllTrendLines per symbol before drawing (deletes your own lines too)")
    ap.add_argument("--alerts", action="store_true", help="create a DAS price alert per retained ray")
    ap.add_argument("--alert-field", default="L1 LAST", help='NewAlertObj AddItem field (default "L1 LAST")')
    ap.add_argument("--list-dir", type=Path, help="where to write Market Viewer lists (default <DAS_ROOT>/GamePlan)")
    ap.add_argument("--no-lists", action="store_true")
    ap.add_argument("--report-dir", type=Path, default=HERE / "out", help="where the JSON report goes")
    ap.add_argument("--notion", action="store_true",
                    help="publish the book to Notion under HVC_NOTION_PARENT (private; licensed data)")
    ap.add_argument("--chartbook", action="store_true",
                    help="also write out/chartbook-<date>.html (Lightweight Charts; licensed data, keep local)")
    ap.add_argument("--dry-run", action="store_true", help="print SCRIPT payloads; never open a socket")
    a = ap.parse_args(argv)

    env = das_out.load_env()
    sources = list(a.symbols)
    if a.gameplan:
        gp = newest_gameplan(env)
        print(f"[universe] game plan {gp.name}", file=sys.stderr)
        sources.insert(0, str(gp))
    if not sources:
        ap.error("give --symbols and/or --gameplan")
    symbols = list(dict.fromkeys(s for src in sources for s in parse_symbols(src)))
    print(f"[universe] {len(symbols)}: {' '.join(symbols)}", file=sys.stderr)
    day = datetime.now(tz=bars_massive.ET).date().isoformat()

    results, errors = [], {}
    for sym in symbols:
        try:
            results.append(scan(sym, a, env))
        except bars_massive.MassiveError as exc:
            errors[sym] = str(exc)
            print(f"[data] {exc}", file=sys.stderr)

    events = [r["symbol"] for r in results if r["event"]]
    touches = [r["symbol"] for r in results if r["touched"]]

    for r in results:
        mult = "N/A" if r.get("multiplier") is None else f"{r['multiplier']:.1f}x"
        flag = (r["event"] or "") + (" TOUCH" if r["touched"] else "")
        state = "" if r.get("confirmed", True) else " (bar open)"
        levels = ", ".join(f"{x['kind']}@{x['level']:g}" for x in r["rays"])
        print(f"{r['symbol']:6} {r['date']}{state} vol {mult:>6} {flag:10} "
              f"HVE since {r['since']}  rays: {levels}")

    report_dir = a.report_dir
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f"{day}.json"
    report.write_text(json.dumps({
        "date": day, "params": {"sma": a.sma, "mult": a.mult, "ray_limit": a.ray_limit,
                                "hve_lookback_years": a.hve_lookback_years,
                                "hve_warmup": a.hve_warmup},
        "events": events, "touches": touches, "errors": errors,
        "symbols": [{k: v for k, v in r.items() if k != "_rays"} for r in results],
    }, indent=2))
    print(f"[report] {report}", file=sys.stderr)
    if a.chartbook:
        import chartbook
        print(f"[chartbook] {chartbook.build(report)}", file=sys.stderr)
    notion_failed = False
    if a.notion and results:
        import notion_publish
        try:
            print(f"[notion] {notion_publish.publish(report)}", file=sys.stderr)
        except (notion_publish.NotionError, RuntimeError) as exc:
            print(f"[notion] FAILED: {exc}", file=sys.stderr)
            notion_failed = True

    if not a.no_lists:
        list_dir = a.list_dir or das_out.gameplan_dir(env)
        for stem, syms in (("HVC-Events", events), ("HVC-Touches", touches)):
            paths = das_out.write_list(list_dir, stem, syms, day)
            print(f"[list] {len(syms)} → {paths[0]}  (Market Viewer: right-click → Load)", file=sys.stderr)

    payloads: list[das_out.Payload] = []
    for r in results:
        if a.draw_window:
            payloads += das_out.ray_payloads(a.draw_window, r["symbol"], r["_rays"], a.clear_lines)
        if a.alerts:
            payloads += das_out.alert_payloads(r["symbol"], r["_rays"], r["close"], a.alert_field)
    das_out.check_safe(payloads)

    rc = 3 if notion_failed else 1 if errors else 0
    if not payloads:
        return rc
    if a.dry_run:
        for w, text in payloads:
            print(f"SCRIPT {w}\t{text}")
        return rc
    try:
        problems = das_out.send(payloads)
    except das_out.NoConnection as exc:
        print(f"[das] NOT CONNECTED: {exc}", file=sys.stderr)
        return 2
    for p in problems:
        print(f"[das] {p}", file=sys.stderr)
    print(f"[das] sent {len(payloads)} SCRIPT command(s)", file=sys.stderr)
    return 1 if (problems or errors) else rc


if __name__ == "__main__":
    sys.exit(main())
