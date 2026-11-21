"""Offline tests for chartbook.py. Synthetic bars only (never licensed data)."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bars_massive  # noqa: E402
import chartbook  # noqa: E402

# 5 bars: bar 0 HVE (close 10), bar 4 HVC (close 14, 90 >= 2 x sma(10,10,90)), touches of 10 on 1-4.
BARS = [{"date": f"2026-01-0{i + 1}", "o": 10, "h": 11 + i, "l": 9, "c": 10 + i, "v": v, "confirmed": True}
        for i, v in enumerate([100, 10, 10, 10, 90])]
PARAMS = {"sma": 3, "mult": 2.0, "ray_limit": 5, "hve_lookback_years": None, "hve_warmup": 0}


def report(tmp: Path, symbols=("ABC",), rays=None) -> Path:
    rays = rays if rays is not None else [{"bar": 0, "level": 10, "kind": "HVE", "date": "2026-01-01"},
                                          {"bar": 4, "level": 14, "kind": "HVC", "date": "2026-01-05"}]
    p = tmp / "2026-01-05.json"
    p.write_text(json.dumps({
        "date": "2026-01-05", "params": PARAMS, "events": ["ABC"], "touches": ["ABC"], "errors": {},
        "symbols": [{"symbol": s, "bars": 5, "since": "2026-01-01", "date": "2026-01-05", "confirmed": True,
                     "close": 14, "volume": 90, "sma": 36.7, "multiplier": 2.45, "event": "HVC",
                     "touched": True, "rays": rays} for s in symbols]}))
    return p


def payload(html: str) -> dict:
    m = re.search(r"const DATA = (\{.*?\});\n", html, re.S)
    return json.loads(m.group(1))


class Chartbook(unittest.TestCase):
    def build(self, **kw):
        with tempfile.TemporaryDirectory() as d, mock.patch.object(bars_massive, "load_cache", return_value=BARS):
            out = chartbook.build(report(Path(d), **{k: v for k, v in kw.items() if k in ("symbols", "rays")}),
                                  n_bars=kw.get("n_bars", 260), inline_lib=kw.get("inline_lib"))
            return out.name, out.read_text()

    def test_series_markers_and_rays(self):
        name, html = self.build()
        self.assertEqual(name, "chartbook-2026-01-05.html")
        d = payload(html)["ABC"]
        self.assertEqual(len(d["candles"]), 5)
        self.assertEqual([m["text"] for m in d["markers"] if m["position"] == "aboveBar"], ["HVE", "HVC 2.5x"])
        self.assertEqual(sum(m["position"] == "belowBar" for m in d["markers"]), 4)   # touches of 10
        self.assertEqual([(r["price"], r["color"]) for r in d["rays"]], [(10, "#4CAF50"), (14, "#FF9800")])
        self.assertEqual(d["volume"][4]["color"], "#FF9800")
        self.assertNotIn("color", d["volume"][1])
        self.assertAlmostEqual(d["threshold"][0]["value"], 2.0 * 40)   # first SMA at bar 2
        self.assertFalse(d["stale"])

    def test_bar_window_and_off_chart_rays(self):
        d = payload(self.build(n_bars=2)[1])["ABC"]
        self.assertEqual([c["time"] for c in d["candles"]], ["2026-01-04", "2026-01-05"])
        far = [dict(BARS[0])] + [{**b, "o": 50, "h": 51, "l": 49, "c": 50} for b in BARS[1:]]
        with tempfile.TemporaryDirectory() as t, mock.patch.object(bars_massive, "load_cache", return_value=far):
            html = chartbook.build(report(Path(t)), n_bars=2).read_text()
        d = payload(html)["ABC"]
        self.assertEqual([(r["price"], r["off_chart"]) for r in d["rays"]], [(10, True), (50, False)])
        self.assertIn("not reached", html)

    def test_stale_report_flagged(self):
        _, html = self.build(rays=[{"bar": 0, "level": 10, "kind": "HVE", "date": "2026-01-01"}])
        self.assertIn("cache newer than report", html)

    def test_pinned_cdn_with_sri_and_attribution(self):
        _, html = self.build()
        self.assertIn(f'src="{chartbook.LWC_URL}" integrity="{chartbook.LWC_SRI}"', html)
        self.assertIn("@5.2.1/", chartbook.LWC_URL)
        self.assertIn("TradingView Lightweight Charts", html)
        self.assertIn("licensed market data", html)

    def test_inline_lib_for_offline(self):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write("window.LightweightCharts={};")
        _, html = self.build(inline_lib=Path(f.name))
        self.assertIn("<script>window.LightweightCharts={};</script>", html)
        self.assertNotIn("unpkg.com", html)

    def test_script_breakout_escaped(self):
        evil = [{**b, "date": "</script><b>x"} if i == 0 else b for i, b in enumerate(BARS)]
        with tempfile.TemporaryDirectory() as t, mock.patch.object(bars_massive, "load_cache", return_value=evil):
            html = chartbook.build(report(Path(t))).read_text()
        self.assertNotIn("</script><b>", html)
        self.assertEqual(payload(html)["ABC"]["candles"][0]["time"], "</script><b>x")

    def test_missing_cache_listed_not_fatal(self):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(bars_massive, "load_cache", side_effect=bars_massive.MassiveError("ABC: no cached bars")):
            html = chartbook.build(report(Path(d))).read_text()
        self.assertIn("ABC: no cached bars", html)
        self.assertEqual(payload(html), {})


if __name__ == "__main__":
    unittest.main()
