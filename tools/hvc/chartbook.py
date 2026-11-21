#!/usr/bin/env python3
"""HVC Watcher chart book: one static HTML page per scan, one chart per symbol.

Candles with HVC/HVE markers and retained rays as price lines, plus a volume pane
with the HVC threshold (SMA × multiplier). Drawn with TradingView Lightweight
Charts (Apache-2.0; attribution logo kept on, see NOTICE).

    chartbook.py                         # newest tools/hvc/out/<date>.json
    chartbook.py --report tools/hvc/out/2026-11-10.json --bars 520
    chartbook.py --inline-lib lightweight-charts.standalone.production.js   # offline page

The page embeds Polygon OHLCV, which is LICENSED DATA. It's written to the
gitignored tools/hvc/out/. Never commit or publish it. Use synthetic bars
for anything public.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import bars_massive  # noqa: E402
import engine  # noqa: E402

LWC_VERSION = "5.2.1"
LWC_URL = f"https://unpkg.com/lightweight-charts@{LWC_VERSION}/dist/lightweight-charts.standalone.production.js"
LWC_SRI = "sha384-KkYqTZlM13Zya6fVUF3IGCBOQ1ehFeJVVgxaVvD/0MebineF9EI8Jkd3NnWNChqN"

HVE_COLOR, HVC_COLOR = "#4CAF50", "#FF9800"   # Pine defaults
TOUCH_COLOR = "#2962FF"


def newest_report() -> Path:
    reports = sorted((HERE / "out").glob("????-??-??.json"))
    if not reports:
        raise SystemExit("no report in tools/hvc/out/; run hvc_daily.py first")
    return reports[-1]


def symbol_data(sym: dict, params: dict, n_bars: int) -> dict:
    """Recompute per-bar series from the cached bars with the report's parameters."""
    bars = bars_massive.load_cache(sym["symbol"])
    bars = bars_massive.trim_years(bars, params.get("hve_lookback_years"))
    r = engine.compute(bars, sma_length=params["sma"], mult=params["mult"],
                       ray_limit=params["ray_limit"], hve_min_bars=params.get("hve_warmup", 0))
    # The cache may have been refreshed after the report; the chart shows what the
    # bars say now and flags the mismatch instead of hiding it.
    stale = [(x.date, x.level) for x in r.rays] != [(x["date"], x["level"]) for x in sym["rays"]]

    start = max(0, len(bars) - n_bars)
    candles, volume, threshold, markers = [], [], [], []
    for i in range(start, len(bars)):
        b, t = bars[i], bars[i]["date"]
        candles.append({"time": t, "open": b["o"], "high": b["h"], "low": b["l"], "close": b["c"]})
        kind = "HVE" if r.hve[i] else "HVC" if r.hvc[i] else None
        if b["v"] is not None:
            volume.append({"time": t, "value": b["v"],
                           **({"color": HVE_COLOR if kind == "HVE" else HVC_COLOR} if kind else {})})
        if r.sma[i] is not None:
            threshold.append({"time": t, "value": r.sma[i] * params["mult"]})
        if kind:
            m = r.multiplier[i]
            markers.append({"time": t, "position": "aboveBar", "shape": "circle",
                            "color": HVE_COLOR if kind == "HVE" else HVC_COLOR,
                            "text": kind if m is None else f"{kind} {m:.1f}x"})
        if r.touched[i]:
            markers.append({"time": t, "position": "belowBar", "shape": "arrowUp",
                            "color": TOUCH_COLOR, "size": 0.5})

    lo = min((c["low"] for c in candles), default=0.0)
    hi = max((c["high"] for c in candles), default=0.0)
    rays = [{"price": x.level, "color": HVE_COLOR if x.kind == "HVE" else HVC_COLOR,
             "title": f"{x.kind} {x.date}", "off_chart": not lo <= x.level <= hi} for x in r.rays]
    return {"symbol": sym["symbol"], "candles": candles, "volume": volume,
            "threshold": threshold, "markers": markers, "rays": rays, "stale": stale,
            "open_bar": not bars[-1].get("confirmed", True)}


def _section(s: dict, data: dict) -> str:
    sym = html.escape(s["symbol"])
    mult = "N/A" if s.get("multiplier") is None else f"{s['multiplier']:.1f}x"
    badges = []
    if s.get("event"):
        badges.append(f'<span class="badge {s["event"].lower()}">{s["event"]}</span>')
    if s.get("touched"):
        badges.append('<span class="badge touch">ray touch</span>')
    if not s.get("confirmed", True):
        badges.append('<span class="badge open">bar open</span>')
    if data["stale"]:
        badges.append('<span class="badge warn">cache newer than report</span>')
    rows = "".join(
        f'<tr><td><span class="dot" style="background:{r["color"]}"></span>{html.escape(r["title"])}'
        f'{" <span class=\'muted\' title=\'No bar in this window traded at this level\'>· not reached</span>" if r["off_chart"] else ""}</td>'
        f'<td class="num">{r["price"]:g}</td></tr>' for r in data["rays"]) or \
        '<tr><td colspan="2" class="muted">no retained rays</td></tr>'
    return f"""
<section class="sym" id="{sym}">
  <header>
    <h2>{sym}</h2>{''.join(badges)}
    <p class="meta">{html.escape(str(s.get("date")))} · close {s.get("close"):g} · volume {mult} of SMA ·
      HVE since {html.escape(str(s.get("since")))}</p>
  </header>
  <div class="body">
    <div class="chart" data-symbol="{sym}"></div>
    <table class="rays"><thead><tr><th>Retained ray</th><th class="num">Level</th></tr></thead>
      <tbody>{rows}</tbody></table>
  </div>
</section>"""


def build(report_path: Path, out: Path | None = None, n_bars: int = 260,
          inline_lib: Path | None = None) -> Path:
    report = json.loads(report_path.read_text())
    params = report["params"]
    syms = report["symbols"]
    rank = {s: 0 for s in report["events"]} | {s: 1 for s in report["touches"] if s not in report["events"]}
    syms = sorted(syms, key=lambda s: (rank.get(s["symbol"], 2), s["symbol"]))

    datasets, sections, missing = {}, [], []
    for s in syms:
        try:
            datasets[s["symbol"]] = symbol_data(s, params, n_bars)
        except bars_massive.MassiveError as exc:
            missing.append(f"{s['symbol']}: {exc}")
            continue
        sections.append(_section(s, datasets[s["symbol"]]))

    if inline_lib:
        lib = f"<script>{inline_lib.read_text()}</script>"
    else:
        lib = f'<script src="{LWC_URL}" integrity="{LWC_SRI}" crossorigin="anonymous"></script>'
    payload = json.dumps(datasets, separators=(",", ":")).replace("</", "<\\/")
    nav = " ".join(f'<a href="#{html.escape(s["symbol"])}">{html.escape(s["symbol"])}</a>'
                   for s in syms if s["symbol"] in datasets)
    errs = "".join(f"<li>{html.escape(m)}</li>" for m in missing)
    errs_html = f'<ul class="errors">{errs}</ul>' if errs else ""
    p = params
    page = TEMPLATE.format(
        date=html.escape(report["date"]), lib=lib, payload=payload, nav=nav, errors=errs_html,
        sections="".join(sections) or '<p class="muted">No symbols in this report.</p>',
        n_events=len(report["events"]), n_touches=len(report["touches"]), n_syms=len(datasets),
        params=html.escape(f"SMA {p['sma']} · {p['mult']}x · {p['ray_limit']} rays · "
                           f"HVE warm-up {p.get('hve_warmup', 0)} bars"),
        hve=HVE_COLOR, hvc=HVC_COLOR, touch=TOUCH_COLOR, lwc=LWC_VERSION)
    out = out or report_path.with_name(f"chartbook-{report['date']}.html")
    out.write_text(page)
    return out


TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>HVC Chart Book {date}</title>
<style>
:root {{ --bg:#ffffff; --fg:#131722; --muted:#6a6d78; --line:#e0e3eb; --card:#f8f9fd; }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{ --bg:#131722; --fg:#d1d4dc; --muted:#868993; --line:#2a2e39; --card:#1c2030; }}
}}
:root[data-theme="dark"] {{ --bg:#131722; --fg:#d1d4dc; --muted:#868993; --line:#2a2e39; --card:#1c2030; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--bg); color:var(--fg);
  font:14px/1.45 -apple-system, "Segoe UI", Roboto, sans-serif; }}
main {{ max-width:1200px; margin:0 auto; padding:24px 16px 48px; }}
h1 {{ font-size:22px; margin:0 0 4px; }}
h2 {{ font-size:18px; margin:0 8px 0 0; display:inline; }}
.lede, .meta, .muted {{ color:var(--muted); }}
.meta {{ margin:4px 0 0; font-size:13px; }}
nav {{ margin:12px 0 20px; display:flex; flex-wrap:wrap; gap:6px 12px; }}
nav a {{ color:var(--fg); }}
.legend span {{ margin-right:14px; white-space:nowrap; }}
.dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; vertical-align:middle; }}
.sym {{ border:1px solid var(--line); border-radius:8px; background:var(--card); padding:14px; margin:0 0 18px; }}
.badge {{ font-size:12px; padding:2px 8px; border-radius:10px; margin-right:4px; color:#fff; vertical-align:2px; }}
.badge.hve {{ background:{hve}; }} .badge.hvc {{ background:{hvc}; }} .badge.touch {{ background:{touch}; }}
.badge.open {{ background:#787b86; }} .badge.warn {{ background:#f23645; }}
.body {{ display:grid; grid-template-columns:1fr 220px; gap:14px; margin-top:10px; }}
.chart {{ height:440px; min-width:0; }}
table.rays {{ border-collapse:collapse; font-size:13px; align-self:start; width:100%; }}
.rays th, .rays td {{ text-align:left; padding:4px 6px; border-bottom:1px solid var(--line); }}
.num {{ text-align:right !important; font-variant-numeric:tabular-nums; }}
.errors {{ color:#f23645; }}
footer {{ margin-top:28px; font-size:12px; color:var(--muted); }}
footer a {{ color:var(--muted); }}
@media (max-width:720px) {{ .body {{ grid-template-columns:1fr; }} .chart {{ height:360px; }} }}
</style>
{lib}
</head><body><main>
<h1>HVC Chart Book · {date}</h1>
<p class="lede">{n_syms} symbols · {n_events} with an event on the last bar · {n_touches} touching a ray · {params}</p>
<p class="legend"><span><i class="dot" style="background:{hve}"></i>HVE: volume record</span>
<span><i class="dot" style="background:{hvc}"></i>HVC: volume ≥ threshold</span>
<span style="color:{touch}">▲</span><span>later bar touched a retained ray</span>
<span>Dashed line on the volume pane: HVC threshold (SMA × multiplier)</span></p>
<nav>{nav}</nav>
{errors}
{sections}
<footer>Signals ported from Major Hayden's hvc_watcher (Apache-2.0). Charts by
<a href="https://www.tradingview.com/lightweight-charts/">TradingView Lightweight Charts™</a> v{lwc} (Apache-2.0).
Contains licensed market data: personal use only, do not share.</footer>
</main>
<script>
const DATA = {payload};
(function () {{
  if (!window.LightweightCharts) {{
    document.querySelectorAll('.chart').forEach(el => el.textContent = 'Lightweight Charts failed to load (offline? rebuild with --inline-lib).');
    return;
  }}
  const L = window.LightweightCharts;
  const css = getComputedStyle(document.documentElement);
  const v = name => css.getPropertyValue(name).trim();
  document.querySelectorAll('.chart').forEach(el => {{
    const d = DATA[el.dataset.symbol];
    const chart = L.createChart(el, {{
      autoSize: true,
      layout: {{ background: {{ color: v('--card') }}, textColor: v('--fg'),
                panes: {{ separatorColor: v('--line') }} }},
      grid: {{ vertLines: {{ color: v('--line') }}, horzLines: {{ color: v('--line') }} }},
      rightPriceScale: {{ borderColor: v('--line') }},
      timeScale: {{ borderColor: v('--line') }},
    }});
    const candles = chart.addSeries(L.CandlestickSeries, {{
      upColor: '#26a69a', downColor: '#ef5350', borderVisible: false,
      wickUpColor: '#26a69a', wickDownColor: '#ef5350' }});
    candles.setData(d.candles);
    L.createSeriesMarkers(candles, d.markers);
    d.rays.forEach(r => candles.createPriceLine({{ price: r.price, color: r.color, lineWidth: 2,
      lineStyle: L.LineStyle.Solid, axisLabelVisible: true, title: r.title }}));
    const vol = chart.addSeries(L.HistogramSeries, {{ color: '#787b8680',
      priceFormat: {{ type: 'volume' }}, priceLineVisible: false, lastValueVisible: false }}, 1);
    vol.setData(d.volume);
    const thr = chart.addSeries(L.LineSeries, {{ color: v('--muted'), lineWidth: 1,
      lineStyle: L.LineStyle.Dashed, priceLineVisible: false, lastValueVisible: false,
      crosshairMarkerVisible: false }}, 1);
    thr.setData(d.threshold);
    chart.panes()[0].setStretchFactor(3);
    chart.panes()[1].setStretchFactor(1);
    chart.timeScale().fitContent();
  }});
}})();
</script>
</body></html>
"""


def find_chrome() -> Path:
    """Headless Chromium for screenshots: $HVC_CHROME, else Playwright's cached headless shell."""
    import os
    if os.environ.get("HVC_CHROME"):
        return Path(os.environ["HVC_CHROME"])
    found = sorted(Path.home().glob(".cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell"))
    if not found:
        raise RuntimeError("no headless Chromium; set HVC_CHROME or `npx playwright install chromium-headless-shell`")
    return found[-1]


def render_pngs(report_path: Path, out_dir: Path, n_bars: int = 260,
                size: tuple[int, int] = (1200, 560)) -> dict[str, Path]:
    """One PNG per symbol (chart + ray table, page header hidden) for static targets like Notion."""
    import subprocess
    chrome = find_chrome()
    out_dir.mkdir(parents=True, exist_ok=True)
    report = json.loads(report_path.read_text())
    hide = "<style>main>h1,.lede,.legend,nav,footer{display:none}main{padding:8px}.sym{margin:0}</style></head>"
    pngs: dict[str, Path] = {}
    for s in report["symbols"]:
        sym = s["symbol"]
        one = out_dir / f"{sym}.json"
        one.write_text(json.dumps(dict(report, symbols=[s])))
        page = build(one, out_dir / f"{sym}.html", n_bars)
        page.write_text(page.read_text().replace("</head>", hide, 1))
        png = out_dir / f"{sym}.png"
        png.unlink(missing_ok=True)
        subprocess.run([str(chrome), "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                        f"--window-size={size[0]},{size[1]}", "--virtual-time-budget=8000",
                        f"--screenshot={png}", page.resolve().as_uri()],
                       capture_output=True, timeout=90, check=False)
        if not png.exists() or png.stat().st_size < 10_000:   # blank page = library didn't load
            raise RuntimeError(f"{sym}: screenshot failed or blank ({png})")
        pngs[sym] = png
    return pngs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", type=Path, help="hvc_daily JSON report (default: newest in tools/hvc/out/)")
    ap.add_argument("--bars", type=int, default=260, help="bars to show per chart (default 260 ≈ 1y)")
    ap.add_argument("--out", type=Path, help="output HTML (default: next to the report)")
    ap.add_argument("--inline-lib", type=Path, help="embed a local Lightweight Charts build (offline page)")
    a = ap.parse_args(argv)
    out = build(a.report or newest_report(), a.out, a.bars, a.inline_lib)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
