"""tools/gen_htk.py on synthetic records. The live .htk files hold ACCOUNT= strings and
stay out of the repo; `gen_htk.py selftest` covers them on the trading machine."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from gen_htk import (HtkError, Record, make_button, make_record, parse,  # noqa: E402
                     parse_cbf, select_block, serialize, serialize_cbf, stamp_build, strip_comments)


class Format(unittest.TestCase):
    def roundtrip(self, raw: bytes) -> list[Record]:
        recs = parse(raw)
        self.assertEqual(serialize(recs), raw)
        return recs

    def test_short_form_keeps_colons_in_script(self):
        r = self.roundtrip(b"Shift+L:buy:ROUTE=X;TriggerOrder=RT:STOP ACT:SELL\r\n")[0]
        self.assertEqual((r.key, r.name, r.prefixed), ("Shift+L", "buy", False))
        self.assertIn("RT:STOP", r.script)

    def test_empty_record(self):
        self.assertEqual(self.roundtrip(b"::\r\n")[0], Record("", "", "", False))

    def test_wrap_at_51_raw_characters(self):
        raw = b"K:n:~ 60:" + b"a" * 51 + b"\r\n" + b"b" * 9 + b"\r\n"
        self.assertEqual(self.roundtrip(raw)[0].script, "a" * 51 + "b" * 9)

    def test_escape_counts_once_and_is_never_split(self):
        # 50 plain + ~0D reaches 53 raw, so the wrap falls after the escape.
        raw = b"K:n:~ 53:" + b"a" * 50 + b"~0D\r\n~0Ab\r\n"
        r = self.roundtrip(raw)[0]
        self.assertEqual(r.script, "a" * 50 + "\r\nb")
        self.assertEqual(len(r.script), 53)

    def test_tilde_and_utf8_bytes_are_hex_escaped(self):
        r = self.roundtrip(b"K:n:~ 5:~7Ex~E2~80~94\r\n")[0]
        self.assertEqual(r.script, "~x\xe2\x80\x94")

    def test_no_trailing_wrap_when_script_ends_on_the_boundary(self):
        self.roundtrip(b"K:n:~ 51:" + b"a" * 51 + b"\r\n")

    def test_truncated_record_is_an_error(self):
        with self.assertRaises(HtkError):
            parse(b"K:n:~ 99:abc\r\n")


class Build(unittest.TestCase):
    def test_make_record_picks_the_form(self):
        self.assertFalse(make_record("", "a", "x" * 95).prefixed)
        self.assertTrue(make_record("", "a", "x" * 96).prefixed)
        self.assertTrue(make_record("", "a", "x;\r\ny;").prefixed)

    def test_make_record_rejects_bad_fields(self):
        for key, name, script in (("", "a:b", "x"), ("K:", "a", "x"), ("", "a", "—")):
            with self.assertRaises(HtkError):
                make_record(key, name, script)

    def test_strip_comments_keeps_strings(self):
        src = 'MsgLog("http://x"); // gone\n/* gone\n too */\n\n$a = 1;  \n'
        self.assertEqual(strip_comments(src), 'MsgLog("http://x");\r\n$a = 1;')

    def test_select_block(self):
        src = ("// ====\n// BLOCK A - LONG\n// ====\n$a = 1;\n\n"
               "// ====\n// BLOCK B - SHORT\n// ====\n$b = 2;\n")
        self.assertEqual(strip_comments(select_block(src, "A")), "$a = 1;")
        self.assertEqual(strip_comments(select_block(src, "B")), "$b = 2;")
        with self.assertRaises(HtkError):
            select_block(src, "C")

    def test_long_script_roundtrips(self):
        rec = make_record("", "dash.x", "\r\n".join(f"$v{i} = {i};" for i in range(40)))
        self.assertEqual(parse(serialize([rec])), [rec])


# A 4-button panel exported from DAS 5.8.4.8 on 2026-11-19 (no account data in it).
EXPORT = bytes.fromhex(
    "63626666696c650024000000bf00000000000000040000000000000064617368"
    "5f626f7800535059204c5348572031323a30300045786563486f746b65792822"
    "6d332e70696e6722293b000000000064000000ffffff00ff0000000000000042"
    "7574746f6e3000427574746f6e300000000000006400000000000000c8c8c800"
    "00000000427574746f6e3000427574746f6e3000000000000064000000000000"
    "00c8c8c80000000000427574746f6e3000427574746f6e300000000000006400"
    "000000000000c8c8c800001400000028000000")


class Cbf(unittest.TestCase):
    def test_export_roundtrips(self):
        buttons, tail = parse_cbf(EXPORT)
        self.assertEqual([b.name for b in buttons], ["dash_box", "Button0", "Button0", "Button0"])
        self.assertEqual(buttons[0].script, 'ExecHotkey("m3.ping");')
        self.assertEqual((buttons[0].fg, buttons[0].bg), (0xFFFFFF, 0x0000FF))
        self.assertEqual(serialize_cbf(buttons, tail), EXPORT)

    def test_generated_panel_parses(self):
        b = [make_button("m3_long", "LONG 1ATR", 'ExecHotkey("m3.long_1atr");', "white", "green")]
        data = serialize_cbf(b)
        self.assertEqual(parse_cbf(data)[0], b)
        self.assertEqual(len(data) - 20, int.from_bytes(data[12:16], "little"))

    def test_bad_buttons(self):
        for args in (("a b", "x"), ("ok", "two\nlines"), ("ok", "x", "", "purple")):
            with self.subTest(args), self.assertRaises(HtkError):
                make_button(*args)


    # the operator's two-row export, 2026-11-21: 7 buttons, the last on row 1
    EXPORT2 = bytes.fromhex(
        "63626666696c6500240000009f010000080000000700000000000000646173685f626f7800424f583a20554e415641494c41424c4500000000000064000000ffffff0080808000000000006d335f6c6f6e67004c4f4e4720314154520045786563486f746b657928226d332e6c6f6e675f3161747222293b000000000064000000ffffff0000ff0000000000006d335f73686f72740053484f525420314154520045786563486f746b657928226d332e73686f72745f3161747222293b000000000064000000ffffff00ff000000000000006d335f70696e670050494e470045786563486f746b657928226d332e70696e6722293b00000000006400000000000000c8c8c800000000006d335f63616e63656c0043414e43454c0045786563486f746b657928226d332e63616e63656c22293b00000000006400000000000000ffff0000000000006d335f666c617474656e00464c415454454e0045786563486f746b657928226d332e666c617474656e22293b000000000064000000ffffff000000ff0000000000427574746f6e3600427574746f6e360000010000006400000000000000c8c8c800001400000028000000")

    def test_two_row_export_round_trip(self):
        buttons, tail = parse_cbf(self.EXPORT2)
        self.assertEqual([b.kind for b in buttons], [0, 0, 0, 0, 0, 0, 1])
        self.assertEqual(serialize_cbf(buttons, tail), self.EXPORT2)

    def test_row_flag_and_limits(self):
        one = serialize_cbf([make_button("a", "A")])
        two = serialize_cbf([make_button("a", "A"), make_button("b", "B", row=1)])
        self.assertEqual((one[16], two[16]), (0, 8))
        self.assertEqual(parse_cbf(two)[0][1].kind, 1)
        with self.assertRaises(HtkError):
            make_button("c", "C", row=2)


class BuildStamp(unittest.TestCase):
    def test_token_replaced_everywhere(self):
        body = 'MsgLog("ping, build @BUILD@"); $b.text = "PING @BUILD@";'
        out = stamp_build(body, "11-21 16:20:05")
        self.assertNotIn("@BUILD@", out)
        self.assertEqual(out.count("11-21 16:20:05"), 2)
        self.assertEqual(stamp_build("MsgLog(1);", "x"), "MsgLog(1);")
        self.assertEqual(stamp_build('"PING @BUILDHM@"', "11-21 16:20:05"), '"PING 16:20"')

if __name__ == "__main__":
    unittest.main()
