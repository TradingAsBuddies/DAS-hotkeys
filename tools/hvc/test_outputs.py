"""Offline tests for DAS outputs and the CLI's failure contract. No socket, no network."""

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bars_massive  # noqa: E402
import das_out  # noqa: E402
import hvc_daily  # noqa: E402
from engine import Ray  # noqa: E402

BARS = [{"date": f"2026-01-{i + 1:02d}", "o": 10, "h": 11, "l": 9, "c": 10 + i, "v": v, "confirmed": True}
        for i, v in enumerate([100, 10, 10, 10, 90])]


class Payloads(unittest.TestCase):
    def test_alert_operator_follows_side_of_close(self):
        rays = [Ray(0, 12.5, "HVE", "2026-01-01"), Ray(1, 8.0, "HVC", "2026-01-02")]
        p = das_out.alert_payloads("ABC", rays, last_close=10.0)
        self.assertIn('AddItem("L1 LAST", ">=", "12.5")', p[0][1])
        self.assertIn('AddItem("L1 LAST", "<=", "8")', p[1][1])
        self.assertTrue(all(w == "GLOBALSCRIPT" for w, _ in p))

    def test_rays_switch_symbol_then_draw_with_kind_colour(self):
        p = das_out.ray_payloads("hvc_chart", "ABC", [Ray(0, 10.0, "HVE"), Ray(3, 13.25, "HVC")], clear=False)
        self.assertEqual(p[0], ("hvc_chart", "SYMBOL ABC;"))
        self.assertNotIn("RemoveAllTrendLines", p[1][1])
        self.assertIn("DrawHorzLineWithPrice(10, Color(76,175,80));", p[1][1])
        self.assertIn("DrawHorzLineWithPrice(13.25, Color(255,152,0));", p[1][1])

    def test_clear_is_opt_in(self):
        p = das_out.ray_payloads("c", "ABC", [Ray(0, 10.0, "HVE")], clear=True)
        self.assertTrue(p[1][1].startswith("RemoveAllTrendLines;"))

    def test_no_rays_no_payload(self):
        self.assertEqual(das_out.ray_payloads("c", "ABC", [], clear=True), [])

    def test_order_tokens_refused(self):
        for bad in ("BUY=Send;", "CXL ALLSYMB;", "TriggerOrder=RT:STOP;", "Panic;"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                das_out.check_safe([("montage1", bad)])
        das_out.check_safe(das_out.alert_payloads("ABC", [Ray(0, 1.0, "HVE")], 2.0))


class Lists(unittest.TestCase):
    def test_one_ticker_per_line_today_and_dated(self):
        with tempfile.TemporaryDirectory() as d:
            paths = das_out.write_list(Path(d), "HVC-Events", ["NVDA", "SPY"], "2026-11-10")
            self.assertEqual([p.name for p in paths], ["HVC-Events-Today.txt", "HVC-Events-2026-11-10.txt"])
            self.assertEqual(paths[0].read_text(), "NVDA\nSPY\n")

    def test_empty_list_still_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            das_out.write_list(Path(d), "X", ["OLD"], "2026-11-09")
            p = das_out.write_list(Path(d), "X", [], "2026-11-10")[0]
            self.assertEqual(p.read_text(), "")

    def test_gameplan_dir_from_das_root(self):
        self.assertEqual(das_out.gameplan_dir({"DAS_ROOT": r"C:\Cobra Trading_x64-NEW"}),
                         Path("/mnt/c/Cobra Trading_x64-NEW/GamePlan"))


class Cli(unittest.TestCase):
    def _run(self, *extra):
        with tempfile.TemporaryDirectory() as d, \
                mock.patch.object(bars_massive, "load_cache", return_value=BARS), \
                redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
            rc = hvc_daily.main(["--symbols", "ABC", "--offline", "--sma", "3", "--mult", "2.0", "--hve-warmup", "0",
                                 "--list-dir", d, "--report-dir", d, *extra])
            events = (Path(d) / "HVC-Events-Today.txt").read_text()
        return rc, out.getvalue(), err.getvalue(), events

    def test_unreachable_das_exits_2_not_no_events(self):
        boom = mock.Mock(side_effect=das_out.NoConnection("DAS CMD API unreachable at 127.0.0.1:1"))
        with mock.patch.object(das_out, "send", boom):
            rc, _, err, _ = self._run("--alerts")
        self.assertEqual(rc, 2)
        self.assertIn("NOT CONNECTED", err)

    def test_dry_run_never_sends(self):
        with mock.patch.object(das_out, "send", side_effect=AssertionError("socket opened")):
            rc, out, _, events = self._run("--alerts", "--draw-window", "hvc_chart", "--dry-run")
        self.assertEqual(rc, 0)
        self.assertIn("SCRIPT hvc_chart\tSYMBOL ABC;", out)
        self.assertIn("NewAlertObj()", out)
        self.assertEqual(events, "ABC\n")    # last bar: 90 >= 2.0 * sma(10,10,90)=73.3

    def test_data_failure_exits_1(self):
        with mock.patch.object(bars_massive, "fetch_daily",
                               side_effect=bars_massive.MassiveError("HTTP 403 from Massive")), \
                tempfile.TemporaryDirectory() as d, redirect_stdout(io.StringIO()), \
                redirect_stderr(io.StringIO()) as err:
            rc = hvc_daily.main(["--symbols", "ABC", "--list-dir", d, "--report-dir", d])
        self.assertEqual(rc, 1)
        self.assertIn("HTTP 403", err.getvalue())


class Massive(unittest.TestCase):
    def test_todays_bar_unconfirmed_before_cutoff(self):
        from datetime import datetime
        now = datetime(2026, 11, 10, 15, 0, tzinfo=bars_massive.ET)
        today_ms = int(datetime(2026, 11, 10, tzinfo=bars_massive.ET).timestamp() * 1000)
        prior_ms = int(datetime(2026, 11, 9, tzinfo=bars_massive.ET).timestamp() * 1000)
        row = {"o": 1, "h": 1, "l": 1, "c": 1, "v": 1}
        self.assertFalse(bars_massive._to_bar({**row, "t": today_ms}, now)["confirmed"])
        self.assertTrue(bars_massive._to_bar({**row, "t": prior_ms}, now)["confirmed"])
        late = datetime(2026, 11, 10, 20, 5, tzinfo=bars_massive.ET)
        self.assertTrue(bars_massive._to_bar({**row, "t": today_ms}, late)["confirmed"])


if __name__ == "__main__":
    unittest.main()
