"""tools/das_alerts.py offline: validation, payloads, the safety screen and the log audit."""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from das_alerts import (AlertError, audit, check_payload, create_payload,  # noqa: E402
                        default_prefix, load_plan, make_alert, px, screen)

# The payload an earlier game plan sent by hand, copied from the DAS log (no account in it).
LIVE_0901 = ('$a = NewAlertObj(); $a.name = "K0102 ABCD LONG 101.25"; $a.Symb = "ABCD"; '
             '$a.AddItem("L1 LAST", ">=", "101.25"); $a.save();')


class Validation(unittest.TestCase):
    def test_payload_matches_the_live_one(self):
        self.assertEqual(create_payload(make_alert("abcd", "long", "101.25", ">=", "K0102")),
                         LIVE_0901)

    def test_price_keeps_two_decimals(self):
        self.assertEqual([px(15), px(13.35), px(2.5), px(0.1234)],
                         ["15.00", "13.35", "2.50", "0.1234"])

    def test_default_prefix(self):
        self.assertEqual(default_prefix(datetime(2026, 1, 2)), "K0102")

    def test_rejects(self):
        cases = [("PA NW", "LONG", 1, ">="), ("ABCD", "LO-NG", 1, ">="), ("ABCD", "LONG", 0, ">="),
                 ("ABCD", "LONG", "x", ">="), ("ABCD", "LONG", float("nan"), ">="),
                 ("ABCD", "LONG", 1, "=>"), ("1ABC", "LONG", 1, ">="),
                 ("ABCD", "LONG", 0.00001, ">="), ("ABCD", "LONG", True, ">=")]
        for c in cases:
            with self.subTest(c), self.assertRaises(AlertError):
                make_alert(*c, prefix="K0102")

    def test_prefix_with_quote_rejected(self):
        with self.assertRaises(AlertError):
            make_alert("ABCD", "LONG", 1, ">=", 'K"1')

    def test_field_allowlist(self):
        self.assertEqual(make_alert("SPY", "X", 1, "<", "K", field="L1 BID").field, "L1 BID")
        with self.assertRaises(AlertError):
            make_alert("SPY", "X", 1, "<", "K", field="L2 BID")


class Plan(unittest.TestCase):
    def write(self, data) -> Path:
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(data, f)
        f.close()
        return Path(f.name)

    def test_plan_loads(self):
        p = self.write({"prefix": "K0102", "alerts": [
            {"symbol": "WXYZ", "tag": "PRIOR_LO", "level": 50.07, "op": "<="}]})
        self.assertEqual([a.name for a in load_plan(p, None)], ["K0102 WXYZ PRIOR_LO 50.07"])

    def test_plan_rejects_duplicate_names(self):
        row = {"symbol": "WXYZ", "tag": "X", "level": 1, "op": "<="}
        with self.assertRaises(AlertError):
            load_plan(self.write({"alerts": [row, row]}), "K1")

    def test_plan_bad_shapes_are_refused_not_crashes(self):
        for data in ([1, 2], {"alerts": "x"}, {"alerts": [5]}):
            with self.subTest(data), self.assertRaises(AlertError):
                load_plan(self.write(data), "K1")
        bad = Path(tempfile.mkdtemp()) / "bad.json"
        bad.write_text("{not json")
        with self.assertRaises(AlertError):
            load_plan(bad, "K1")

    def test_plan_reports_every_bad_row(self):
        with self.assertRaises(AlertError) as cm:
            load_plan(self.write({"alerts": [{"symbol": "A"}, {"symbol": "B"}]}), "K1")
        self.assertIn("alert 1", str(cm.exception))
        self.assertIn("alert 2", str(cm.exception))


class Safety(unittest.TestCase):
    def test_screen_passes_alert_payloads(self):
        screen(LIVE_0901)
        screen(check_payload("K0102 ABCD LONG 101.25", "alr1"))

    def test_screen_refuses_orders_and_reset(self):
        for bad in ("$a.Reset(); $a.save();", "BUY=Send", "Panic", "CXL ALLSYMB"):
            with self.subTest(bad), self.assertRaises(AlertError):
                screen(bad)

    def test_order_words_inside_a_name_are_not_code(self):
        # "K0102 WXYZ SHORT 49.65" was made by an earlier game plan.
        screen(create_payload(make_alert("WXYZ", "SHORT", 49.65, "<=", "K0102")))
        screen(create_payload(make_alert("SPY", "RESET", 1, "<=", "K0102")))
        screen(check_payload("K0102 WXYZ SHORT 49.65", "t"))

    def test_check_payload_guards_with_isobj(self):
        p = check_payload("K0102 X Y 1.00", "t")
        self.assertIn("if (IsObj($q))", p)
        self.assertLess(p.index("IsObj"), p.index("$q.Symb"))

    def test_check_payload_rejects_quote(self):
        with self.assertRaises(AlertError):
            check_payload('a"b', "t")


class Audit(unittest.TestCase):
    LINES = [
        "09:01:48,CMDAPILog,SCRIPT\tGLOBALSCRIPT\t" + LIVE_0901,
        '09:02:02,CMDAPILog,SCRIPT\tGLOBALSCRIPT\t$x = GetAlertObj("K0102 ABCD LONG 101.25");',
        "09:02:30,Error,ScriptError:100  Line:1  Error:Function return is not Object at "
        'Line:MsgLog("t=", GetAlertObj("NO").Symb); acct TRABC123',
        "09:03:00,Log,unrelated",
    ]

    def test_audit_counts(self):
        r = audit(self.LINES)
        self.assertEqual(r["created"], [("09:01:48", "K0102 ABCD LONG 101.25", "ABCD",
                                         "L1 LAST", ">=", "101.25")])
        self.assertEqual(r["checks"], [("09:02:02", "K0102 ABCD LONG 101.25")])
        self.assertEqual(len(r["errors"]), 1)

    def test_audit_redacts_accounts(self):
        self.assertNotIn("TRABC123", audit(self.LINES)["errors"][0])


if __name__ == "__main__":
    unittest.main()
