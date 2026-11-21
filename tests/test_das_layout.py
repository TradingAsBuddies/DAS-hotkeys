"""tools/das_layout.py offline: validation, payload order, safety screen, standalone script."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from das_layout import (LayoutError, all_payloads, config_payload, create_payload,  # noqa: E402
                        load_layout, make_window, newest_ok, probe_payload, screen,
                        standalone)

EXAMPLE = Path(__file__).resolve().parent.parent / "scripts" / "layout" / "example.json"


class Validation(unittest.TestCase):
    def test_example_loads(self):
        self.assertEqual([w.name for w in load_layout(EXAMPLE)],
                         ["lay_m1", "lay_c1", "lay_c5", "lay_m2"])

    def test_rejects(self):
        bad = [{"name": "1x", "type": "Chart"}, {"name": "a b", "type": "Chart"},
               {"name": "x", "type": "Desktop"}, {"name": "x", "type": "Chart", "pos": [1]},
               {"name": "x", "type": "Chart", "pos": [1.5, 2]}, {"name": "x", "type": "Chart", "size": [10, 10]},
               {"name": "x", "type": "Chart", "minutes": 0}, {"name": "x", "type": "Montage", "minutes": 1},
               {"name": "x", "type": "Chart", "days": 5}, {"name": "x", "type": "Chart", "setting": "../a.cst"},
               {"name": "x", "type": "Chart", "setting": "a.dsk"}, {"name": "x", "type": "Chart", "symbol": "S PY"},
               {"name": "x", "type": "Chart", "zoom": 1}, {"name": "x", "clone": "x"},
               {"name": "x", "clone": "m", "type": "Chart"}, {"name": "x", "clone": "m", "template_type": "Position"},
               {"name": "x", "type": "Montage", "buttons": {"b": {"text": 'a"b'}}},
               {"name": "x", "type": "Montage", "buttons": {"b": {"bg": "Purple"}}},
               {"name": "x", "type": "Chart", "pos": [True, 0]}]
        for d in bad:
            with self.subTest(d), self.assertRaises(LayoutError):
                make_window(d)

    def test_missing_cst_is_refused_when_install_readable(self):
        d = Path(tempfile.mkdtemp())
        (d / "have.cst").write_bytes(b"x")
        make_window({"name": "c", "type": "Chart", "setting": "have.cst"}, d)
        with self.assertRaises(LayoutError):
            make_window({"name": "c", "type": "Chart", "setting": "nope.cst"}, d)

    def test_duplicates_case_insensitive_and_template_clash(self):
        for rows in ([{"name": "A", "type": "Chart"}, {"name": "a", "type": "Chart"}],
                     [{"name": "t", "type": "Montage"}, {"name": "c", "clone": "t"}]):
            f = Path(tempfile.mkdtemp()) / "l.json"
            f.write_text(json.dumps({"windows": rows}))
            with self.subTest(rows), self.assertRaises(LayoutError):
                load_layout(f)


class Payloads(unittest.TestCase):
    def test_create_is_a_send_of_its_own(self):
        # 2026-11-19: a name in the same script landed one window late.
        self.assertEqual(create_payload(make_window({"name": "c", "type": "Chart"})),
                         ("GLOBALSCRIPT", "NewWindow Chart;"))

    def test_clone_runs_inside_the_template(self):
        self.assertEqual(create_payload(make_window({"name": "m2", "clone": "montage1"})),
                         ("montage1", "DuplicateWindow;"))

    def test_newest_window_check(self):
        chart = make_window({"name": "c", "type": "Chart"})
        mont = make_window({"name": "m", "type": "Montage"})
        clone = make_window({"name": "m2", "clone": "montage1"})
        self.assertIsNone(newest_ok(chart, "Obj:ChartWindowObject|"))
        self.assertIsNone(newest_ok(mont, "Obj:TradeWindowObject|"))
        self.assertIsNone(newest_ok(clone, "Obj:TradeWindowObject|montage1"))
        # the 10:19 failure: the newest window was the montage, or Internal Message
        self.assertIsNotNone(newest_ok(chart, "Obj:TradeWindowObject|"))
        self.assertIsNotNone(newest_ok(mont, "Obj:WindowObject|"))
        self.assertIsNotNone(newest_ok(chart, "Obj:ChartWindowObject|lay_m1"))
        self.assertIsNotNone(newest_ok(chart, None))
        self.assertIsNotNone(newest_ok(chart, "NOOBJ"))

    def test_probe_guards(self):
        p = probe_payload("t")
        self.assertLess(p.index("isObject($lw)"), p.index("$lw,"))

    def test_config_order(self):
        w = make_window({"name": "c", "type": "Chart", "pos": [1, 2], "size": [300, 200],
                         "symbol": "spy", "minutes": 5, "days": 3, "setting": "a.cst"})
        win, p = config_payload(w)
        self.assertEqual(win, "c")
        order = ["SetPopOut Y", "WSize 300 200", "WPos 1 2", "LoadSetting a.cst",
                 "Symbol SPY", "MinuteChart 5 3d"]
        self.assertEqual(sorted(order, key=p.index), order)

    def test_montage_symbol_uses_property_behind_guard(self):
        _, p = config_payload(make_window({"name": "m", "type": "Montage", "symbol": "QQQ"}))
        self.assertIn('if (isObject($lw)) { $lw.SYMBOL = "QQQ"; }', p)

    def test_link_colour(self):
        _, p = config_payload(make_window({"name": "c", "type": "Chart", "link": "blue", "symbol": "SPY"}))
        self.assertLess(p.index('$lw.LinkColor = "Blue"'), p.index("Symbol SPY"))
        with self.assertRaises(LayoutError):
            make_window({"name": "c", "type": "Chart", "link": "bl;ue"})

    def test_button_face_guarded(self):
        w = make_window({"name": "m", "type": "Montage",
                         "buttons": {"dash_box": {"text": "SHORT OK", "bg": "red"}}})
        p = all_payloads(w)[-1][1]
        self.assertLess(p.index("isObject($lb)"), p.index("$lb.text"))
        self.assertIn('Color("Red")', p)
        screen(p)                          # SHORT inside a quoted face is not code

    def test_screen_refuses(self):
        for bad in ("SaveDesktop;", "ClearDesktop;", "Close;", "BUY=Send", "Panic"):
            with self.subTest(bad), self.assertRaises(LayoutError):
                screen(bad)

    def test_every_example_payload_passes_screen(self):
        for w in load_layout(EXAMPLE):
            for _, p in all_payloads(w):
                screen(p)

    def test_standalone_is_multiline_and_guarded(self):
        s = standalone(load_layout(EXAMPLE))
        self.assertIn('$lw = GetWindowObj("lay_c1");\nif (isObject($lw) == 0) {', s)
        self.assertIn("  FocusWindow montage1;\n  DuplicateWindow;", s)
        self.assertNotIn("SaveDesktop", s)


if __name__ == "__main__":
    unittest.main()
