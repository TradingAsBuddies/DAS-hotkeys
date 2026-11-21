"""Offline tests for notion_publish.py and the --gameplan universe. Fake client, no network."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bars_massive  # noqa: E402
import hvc_daily  # noqa: E402
import notion_publish as np_  # noqa: E402

REPORT = {
    "date": "2026-11-11", "params": {"sma": 20, "mult": 3.0, "ray_limit": 5, "hve_warmup": 252},
    "events": ["BBB"], "touches": ["CCC"], "errors": {"ZZZ": "no bars"},
    "symbols": [
        {"symbol": "AAA", "since": "2021-11-11", "date": "2026-11-11", "confirmed": True, "close": 100.0,
         "multiplier": 0.8, "event": None, "touched": False, "rays": []},
        {"symbol": "BBB", "since": "2021-11-11", "date": "2026-11-11", "confirmed": True, "close": 50.0,
         "multiplier": 3.4, "event": "HVC", "touched": False,
         "rays": [{"bar": 9, "level": 55.0, "kind": "HVE", "date": "2026-01-02"}]},
        {"symbol": "CCC", "since": "2021-11-11", "date": "2026-11-11", "confirmed": True, "close": 10.0,
         "multiplier": None, "event": None, "touched": True,
         "rays": [{"bar": 3, "level": 9.5, "kind": "HVC", "date": "2026-02-03"}]},
    ],
}


class FakeNotion:
    def __init__(self, existing=()):
        self.calls, self.existing = [], list(existing)

    def upload_png(self, png):
        self.calls.append(("upload", png.name))
        return f"up-{png.stem}"

    def child_pages(self, parent):
        return [{"id": i, "child_page": {"title": t}} for i, t in self.existing]

    def call(self, method, path, body=None):
        self.calls.append((method, path, body))
        return {"id": "new-page", "url": "https://notion.so/new-page"}


def fake_render(report_path, out_dir):
    out = {}
    for s in json.loads(Path(report_path).read_text())["symbols"]:
        p = Path(out_dir) / f"{s['symbol']}.png"
        p.write_bytes(b"png")
        out[s["symbol"]] = p
    return out


def texts(blocks):
    out = []
    for b in blocks:
        body = b[b["type"]]
        out += ["".join(r["text"]["content"] for r in body.get("rich_text", []))]
        for row in body.get("children", []):
            out += ["|".join("".join(r["text"]["content"] for r in c) for c in row["table_row"]["cells"])]
    return out


class Blocks(unittest.TestCase):
    def setUp(self):
        self.blocks = np_.page_blocks(REPORT, {"AAA": "u1", "BBB": "u2", "CCC": "u3"})
        self.t = texts(self.blocks)

    def test_order_events_then_touches_then_rest(self):
        heads = texts([b for b in self.blocks if b["type"] == "heading_2"])
        self.assertEqual(heads, ["Summary", "BBB", "CCC", "AAA"])

    def test_summary_rows_and_nearest_ray(self):
        self.assertIn("BBB|50|3.4x|HVC|-|HVE 55 (2026-01-02)", self.t)
        self.assertIn("CCC|10|N/A|-|yes|HVC 9.5 (2026-02-03)", self.t)
        self.assertIn("AAA|100|0.8x|-|-|-", self.t)

    def test_ray_table_and_images(self):
        self.assertIn("HVE|2026-01-02|55|+10.0%", self.t)
        imgs = [b["image"]["file_upload"]["id"] for b in self.blocks if b["type"] == "image"]
        self.assertEqual(imgs, ["u2", "u3", "u1"])
        self.assertIn("No retained rays.", self.t)

    def test_privacy_and_error_callouts(self):
        self.assertTrue(any("licensed Polygon" in x for x in self.t))
        self.assertTrue(any("ZZZ: no bars" in x for x in self.t))

    def test_attribution(self):
        links = [r["text"]["link"]["url"] for b in self.blocks if b["type"] == "paragraph"
                 for r in b["paragraph"]["rich_text"] if r["text"]["link"]]
        self.assertEqual(links, [np_.UPSTREAM, np_.LWC_HOME])


class Publish(unittest.TestCase):
    def run_publish(self, fake, env=None, **kw):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "2026-11-11.json"
            p.write_text(json.dumps(REPORT))
            return np_.publish(p, env=env if env is not None else {"HVC_NOTION_PARENT": "parent"},
                               client=fake, render=fake_render, **kw)

    def test_creates_page_under_parent_with_uploads(self):
        fake = FakeNotion()
        url = self.run_publish(fake)
        self.assertEqual(url, "https://notion.so/new-page")
        self.assertEqual([c[1] for c in fake.calls if c[0] == "upload"], ["AAA.png", "BBB.png", "CCC.png"])
        post = [c for c in fake.calls if c[0] == "POST"][0]
        self.assertEqual(post[2]["parent"], {"type": "page_id", "page_id": "parent"})
        self.assertEqual(post[2]["properties"]["title"]["title"][0]["text"]["content"], "HVC Chart Book · 2026-11-11")

    def test_rerun_archives_same_date_only(self):
        fake = FakeNotion(existing=[("old", "HVC Chart Book · 2026-11-11"), ("keep", "HVC Chart Book · 2026-11-10")])
        self.run_publish(fake)
        patches = [c for c in fake.calls if c[0] == "PATCH"]
        self.assertEqual(patches, [("PATCH", "/pages/old", {"archived": True})])

    def test_archive_happens_after_uploads(self):
        fake = FakeNotion(existing=[("old", "HVC Chart Book · 2026-11-11")])
        self.run_publish(fake)
        kinds = [c[0] for c in fake.calls]
        self.assertLess(max(i for i, k in enumerate(kinds) if k == "upload"), kinds.index("PATCH"))

    def test_missing_parent_raises(self):
        with self.assertRaises(np_.NotionError):
            self.run_publish(FakeNotion(), env={})

    def test_dry_run_makes_no_calls(self):
        fake = FakeNotion()
        out = self.run_publish(fake, dry_run=True)
        self.assertIn("[dry-run]", out)
        self.assertEqual(fake.calls, [])


class Universe(unittest.TestCase):
    def test_newest_dated_gameplan_plus_watchlist_deduped(self):
        bars = [{"date": f"2026-01-0{i + 1}", "o": 1, "h": 2, "l": 1, "c": 1.5, "v": 10, "confirmed": True}
                for i in range(5)]
        with tempfile.TemporaryDirectory() as d:
            gp = Path(d) / "GamePlan"
            gp.mkdir()
            (gp / "GamePlan-2026-11-09.txt").write_text("OLD\n")
            (gp / "GamePlan-2026-11-10.txt").write_text("NVDA\nSPY\n")
            (gp / "GamePlan-Today.txt").write_text("STALE\n")
            wl = Path(d) / "wl.txt"
            wl.write_text("SPY\nQQQ\n")
            with mock.patch.object(hvc_daily.das_out, "gameplan_dir", return_value=gp), \
                    mock.patch.object(bars_massive, "load_cache", return_value=bars), \
                    redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rc = hvc_daily.main(["--gameplan", "--symbols", str(wl), "--offline", "--no-lists",
                                     "--report-dir", d])
            rep = json.loads(next(Path(d).glob("????-??-??.json")).read_text())
        self.assertEqual(rc, 0)
        self.assertEqual([s["symbol"] for s in rep["symbols"]], ["NVDA", "SPY", "QQQ"])

    def test_no_universe_is_usage_error(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            hvc_daily.main(["--offline"])


if __name__ == "__main__":
    unittest.main()
