"""tools/gen_cst.py offline, on a synthetic file (a real .cst holds an account ID).

Record layout as decoded 2026-11-21: u32 LEN, u32 2, 20-byte TYPE, NAME\\0, then params
(a moving average: u32 period, u32 type)."""

import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from gen_cst import CstError, parse, parse_ma, parse_name, patch  # noqa: E402

TAIL = b"\xff" * 11 + b"\0" + b"\x80\x80\xff\0" + b"\0" * 40


def record(typ: bytes, name: bytes, params: bytes = b"") -> bytes:
    body = typ.ljust(20, b"\0") + name + b"\0" + params + TAIL
    return struct.pack("<II", len(body) + 7, 2) + body     # LEN need only track the name


SAMPLE = (b"ChartScreenFile\0" + b"\0" * 40
          + record(b"Moving Average", b"StudyMovingAvg", struct.pack("<II", 9, 2))
          + record(b"Moving Average", b"StudyMovingAvg", struct.pack("<II", 21, 2))
          + record(b"Price", b"StudyBar") + record(b"VWAP", b"StudyVWAP"))


class Cst(unittest.TestCase):
    def test_parse(self):
        self.assertEqual([(x.type, x.name, x.period, x.ma_type) for x in parse(SAMPLE)],
                         [("Moving Average", "StudyMovingAvg", 9, 2),
                          ("Moving Average", "StudyMovingAvg", 21, 2),
                          ("Price", "StudyBar", None, None), ("VWAP", "StudyVWAP", None, None)])

    def test_ma_patch_in_place(self):
        out = patch(SAMPLE, [parse_ma("2:sma:34")])
        s = parse(out)
        self.assertEqual((s[1].period, s[1].ma_type), (34, 0))
        diff = [i for i in range(len(SAMPLE)) if out[i] != SAMPLE[i]]
        self.assertTrue(diff and all(s[1].params_at <= i < s[1].params_at + 8 for i in diff))

    def test_rename_adjusts_len_like_das(self):
        before = parse(SAMPLE)
        out = patch(SAMPLE, [parse_ma("2:sma:50")], [parse_name("1:EMA9"), parse_name("2:SMA50")])
        after = parse(out)
        self.assertEqual([(x.name, x.period, x.ma_type) for x in after[:2]],
                         [("EMA9", 9, 2), ("SMA50", 50, 0)])
        self.assertEqual([x.type for x in after], [x.type for x in before])   # TYPE untouched
        for b, a in zip(before[:2], after[:2]):                              # 107 -> 97 rule
            lb = struct.unpack_from("<I", SAMPLE, b.len_at)[0]
            la = struct.unpack_from("<I", out, a.len_at)[0]
            self.assertEqual(la - lb, len(a.name) - len(b.name))
        self.assertEqual(len(out), len(SAMPLE) - 10 - 9)

    def test_rejects(self):
        with self.assertRaises(CstError):
            parse(b"cbffile\0")
        for bad in ("2:wma:34", "2:sma:0", "2:sma:501", "sma:34", "2:ema"):
            with self.assertRaises(CstError):
                parse_ma(bad)
        for bad in ("1:", "x:EMA", "1:" + "A" * 32, '1:a"b', "1:a;b"):
            with self.assertRaises(CstError):
                parse_name(bad)
        with self.assertRaises(CstError):
            patch(SAMPLE, [parse_ma("3:sma:34")])                 # Price is not an MA
        with self.assertRaises(CstError):
            patch(SAMPLE, [], [parse_name("9:X")])
        with self.assertRaises(CstError):
            patch(SAMPLE, [], [parse_name("1:StudyBar")])         # duplicate name


if __name__ == "__main__":
    unittest.main()
