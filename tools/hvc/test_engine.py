"""Parity tests for engine.py, ported from Major Hayden's hvc_watcher.test.mjs.

Each case keeps the upstream fixture (volumes, prices, unconfirmed bars) and
expected per-bar values. Drawing/label/colour cases are out of scope: DAS draws
rays itself. Run: python3 -m unittest discover -s tools/hvc
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import compute, multiplier_for  # noqa: E402

NAN = float("nan")


def run(volumes, prices=None, unconfirmed=(), sma_length=3, mult=2.0, ray_limit=5):
    """Mirror the upstream harness: SMA 3, multiplier 2.0, OHLC 100/102/99/101."""
    prices = prices or []
    bars = []
    for i, v in enumerate(volumes):
        p = {"o": 100, "h": 102, "l": 99, "c": 101}
        if i < len(prices):
            p.update({k[0]: val for k, val in prices[i].items()})
        p["v"] = v
        p["confirmed"] = i not in unconfirmed
        bars.append(p)
    return compute(bars, sma_length=sma_length, mult=mult, ray_limit=ray_limit)


def ints(flags):
    return [1 if f else 0 for f in flags]


def P(o, h, l, c):
    return {"open": o, "high": h, "low": l, "close": c}


class Timeframes(unittest.TestCase):
    def test_default_multiplier_inclusive_boundary(self):
        for tf, m in [("1", 3), ("D", 3), ("2D", 3), ("W", 2), ("2W", 2), ("M", 2), ("3M", 2), ("12M", 2)]:
            boundary = 90 if m == 3 else 30
            for off in (-1, 0, 1):
                with self.subTest(tf=tf, off=off):
                    r = run([10, 10, 10, boundary + off], sma_length=4, mult=multiplier_for(tf))
                    self.assertEqual(ints(r.hvc), [0, 0, 0, 0 if off < 0 else 1])

    def test_independently_configured_multiplier(self):
        for tf, m in [("1", 1.5), ("D", 1.5), ("2D", 1.5), ("W", 2.5), ("2W", 2.5), ("M", 3.5), ("3M", 3.5), ("12M", 3.5)]:
            with self.subTest(tf=tf):
                sel = multiplier_for(tf, daily=1.5, weekly=2.5, monthly=3.5)
                self.assertEqual(sel, m)
                r = run([10, 10, 10, 90], sma_length=4, mult=sel)
                self.assertEqual(r.sma[3] * sel, 30 * m)
                self.assertEqual(ints(r.hvc), [0, 0, 0, 1 if m <= 3 else 0])


class Detection(unittest.TestCase):
    def test_current_inclusive_sma(self):
        for vols, exp in [([10, 10, 39], 0), ([10, 10, 40], 1), ([10, 10, 41], 1)]:
            with self.subTest(vols=vols):
                r = run(vols)
                self.assertEqual(ints(r.hvc), [0, 0, exp])
                self.assertAlmostEqual(r.sma[2], sum(vols) / 3)

    def test_length_one_sma_caps_multiplier(self):
        r = run([10, 50, 100], sma_length=1)
        self.assertEqual(r.multiplier, [1, 1, 1])
        self.assertEqual(ints(r.hvc), [0, 0, 0])

    def test_hve_first_positive_and_no_ties(self):
        r = run([0, 10, 10, 40, 30, 40, 41])
        self.assertEqual(ints(r.hve), [0, 1, 0, 1, 0, 0, 1])
        self.assertEqual(r.hve_threshold, [0, 0, 10, 10, 40, 40, 40])

    def test_simultaneous_hvc_hve(self):
        r = run([10, 10, 40])
        self.assertEqual(ints(r.hvc), [0, 0, 1])
        self.assertEqual(ints(r.hve), [1, 0, 1])

    def test_eligibility_ignores_prices(self):
        prices = [P(8, 11, 7, 10), P(18, 22, 17, 20), P(28, 33, 27, 30)]
        r = run([40, 10, 100], prices=prices)
        self.assertEqual(ints(r.hvc), [0, 0, 1])
        self.assertEqual(ints(r.hve), [1, 0, 1])

    def test_zero_volume(self):
        r = run([0, 0, 0, 0])
        self.assertEqual(ints(r.hvc), [0, 0, 0, 0])
        self.assertEqual(ints(r.hve), [0, 0, 0, 0])
        self.assertTrue(all(m is None for m in r.multiplier))

    def test_zero_current_volume_positive_baseline(self):
        r = run([10, 10, 0])
        self.assertEqual(r.multiplier[2], 0)
        self.assertFalse(r.hvc[2])

    def test_missing_volume_during_warmup(self):
        r = run([10, 10, NAN])
        self.assertEqual(ints(r.hvc), [0, 0, 0])
        self.assertTrue(all(m is None for m in r.multiplier))

    def test_missing_volume_after_warmup(self):
        r = run([10, 10, 10, None])
        self.assertFalse(r.hvc[3])
        self.assertIsNone(r.multiplier[3])

    def test_diagnostics(self):
        r = run([10, 10, 40])
        self.assertEqual(r.multiplier[2], 2)
        self.assertEqual(r.sma[2] * 2.0, 40)


class Confirmation(unittest.TestCase):
    def test_events_wait_for_close_touches_stay_live(self):
        r = run([10, 10, 40], unconfirmed=[2])
        self.assertEqual(ints(r.hvc), [0, 0, 0])
        self.assertEqual(ints(r.hve), [1, 0, 0])
        self.assertEqual(ints(r.touched), [0, 1, 1])
        self.assertEqual(r.multiplier[2], 2)
        self.assertEqual(len(r.all_rays), 1)

    def test_running_record_survives_unconfirmed(self):
        self.assertEqual(ints(run([10, 10, 40]).hvc), [0, 0, 1])
        r = run([10, 10, 40, 30], unconfirmed=[2])
        self.assertEqual(ints(r.hve), [1, 0, 0, 0])
        self.assertEqual(r.hve_threshold, [0, 10, 10, 40])


class Rays(unittest.TestCase):
    def test_close_anchors_and_kinds(self):
        for vols, anchors, kinds in [
            ([10, 10, 40], [0, 2], ["HVE", "HVE"]),
            ([100, 10, 10, 40], [0, 3], ["HVE", "HVC"]),
        ]:
            with self.subTest(vols=vols):
                prices = [P(i + 8, i + 11, i + 7, i + 10) for i in range(len(vols))]
                r = run(vols, prices=prices)
                self.assertEqual([x.bar for x in r.all_rays], anchors)
                self.assertEqual([x.kind for x in r.all_rays], kinds)
                for x in r.all_rays:
                    self.assertEqual(x.level, prices[x.bar]["close"])

    def test_hidden_default_monitoring(self):
        r = run([100, 10, 10, 40])
        self.assertEqual(len(r.rays), 2)
        self.assertEqual(ints(r.touched), [0, 1, 1, 1])
        self.assertEqual(ints(r.hvc), [0, 0, 0, 1])
        self.assertEqual(ints(r.hve), [1, 0, 0, 0])

    def test_touch_boundaries_gaps_repeats(self):
        prices = [P(10, 11, 9, 10), P(8, 9, 7, 8), P(12, 13, 11, 12),
                  P(11, 12, 10, 11), P(9, 10, 8, 9), P(10, 11, 9, 10)]
        r = run([100, 0, 0, 0, 0, 0], prices=prices, unconfirmed=[3, 4])
        self.assertEqual(ints(r.touched), [0, 0, 0, 1, 1, 1])

    def test_touch_scan_multiple_levels(self):
        prices = [P(10, 11, 9, 10), P(20, 21, 19, 20), P(20, 21, 19, 20),
                  P(10, 11, 9, 10), P(10, 21, 9, 20)]
        r = run([100, 200, 0, 0, 0], prices=prices)
        self.assertEqual(ints(r.touched), [0, 0, 1, 1, 1])
        self.assertEqual([x.level for x in r.rays], [10, 20])

    def test_unconfirmed_event_cannot_replace_at_capacity(self):
        prices = [P(10, 11, 9, 10), P(12, 13, 11, 12), P(10, 21, 9, 20),
                  P(10, 11, 9, 10), P(10, 21, 9, 20), P(10, 11, 9, 10)]
        r = run([100, 10, 300, 0, 400, 0], prices=prices, unconfirmed=[2], ray_limit=1)
        self.assertEqual(ints(r.hvc), [0, 0, 0, 0, 0, 0])
        self.assertEqual(ints(r.hve), [1, 0, 0, 0, 1, 0])
        self.assertEqual(ints(r.touched), [0, 0, 1, 1, 1, 0])
        self.assertEqual(r.ray_count, [1, 1, 1, 1, 1, 1])
        self.assertEqual([(x.bar, x.level) for x in r.rays], [(4, 20)])

    def test_retention_limits(self):
        for limit in (1, 5, 200):
            with self.subTest(limit=limit):
                r = run([10] * 202, sma_length=1, mult=1.0, ray_limit=limit)
                self.assertEqual(len(r.rays), limit)
                self.assertEqual(min(x.bar for x in r.rays), 202 - limit)
                self.assertEqual(r.ray_count[-1], limit)
                self.assertTrue(all(c <= limit for c in r.ray_count))

    def test_retiring_ray_touches_on_last_candle_only(self):
        prices = [P(10, 11, 9, 10), P(10, 21, 9, 20), P(10, 11, 9, 10)]
        r = run([100, 200, 0], prices=prices, ray_limit=1)
        self.assertEqual(ints(r.touched), [0, 1, 0])
        self.assertEqual([x.level for x in r.rays], [20])


class HveWarmup(unittest.TestCase):
    """Extension, not in the Pine: suppress trivially-true early records."""

    def test_warmup_suppresses_early_hve_but_keeps_record(self):
        r = compute([{"h": 102, "l": 99, "c": 101, "v": v} for v in [10, 20, 30, 25, 40]],
                    sma_length=3, mult=2.0, hve_min_bars=3)
        self.assertEqual(ints(r.hve), [0, 0, 0, 0, 1])
        self.assertEqual(r.hve_threshold, [0, 10, 20, 30, 30])

    def test_default_is_pine_parity(self):
        self.assertEqual(ints(run([10, 20, 30]).hve), [1, 1, 1])


class Validation(unittest.TestCase):
    def test_rejects_bad_params(self):
        for kw in ({"sma_length": 0}, {"mult": 0.9}, {"ray_limit": 0}, {"ray_limit": 201}):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                compute([], **kw)


if __name__ == "__main__":
    unittest.main()
