"""tools/install.py against temporary folders. Nothing here touches a DAS install: the
build step and the running-process check are replaced."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
import install  # noqa: E402


def run(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = fn(*a, **k)
    return rc, buf.getvalue()


class Config(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def write(self, **kv) -> Path:
        p = self.tmp / "install.local.json"
        p.write_text(json.dumps(kv))
        return p

    def test_missing_config_says_how_to_make_one(self):
        with self.assertRaisesRegex(install.InstallError, "Copy install.example.json"):
            install.load_config(self.tmp / "install.local.json")

    def test_empty_das_dir_is_refused(self):
        with self.assertRaisesRegex(install.InstallError, "das_dir"):
            install.load_config(self.write(das_dir="", manifest="m.json", hotkey_file="a.htk"))

    def test_file_names_cannot_carry_a_path(self):
        with self.assertRaisesRegex(install.InstallError, "bare file name"):
            install.load_config(self.write(das_dir="x", manifest="m.json", hotkey_file="../a.htk"))

    def test_example_config_is_valid_and_vendor_neutral(self):
        cfg = install.load_config(install.EXAMPLE)
        self.assertIn("DAS Trader", cfg["das_dir"])

    def test_folder_without_config_cfg_is_refused(self):
        with self.assertRaisesRegex(install.InstallError, "no Config.cfg"):
            install.check_das_dir(self.tmp)

    def test_windows_path_is_translated_only_off_windows(self):
        with mock.patch.object(install.os, "name", "posix"):
            self.assertEqual(install.to_local("C:\\DAS Trader Pro_x64").as_posix(),
                             "/mnt/c/DAS Trader Pro_x64")


class Copy(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.das = self.tmp / "das"
        self.das.mkdir()
        (self.das / "Config.cfg").write_text("CMDAPI:PORT:1\n")
        (self.das / "m.htk").write_bytes(b"old")
        stage = self.tmp / "stage"
        stage.mkdir()
        (stage / "m.htk").write_bytes(b"new hotkeys")
        (stage / "m-win.cbf").write_bytes(b"panel")
        self.cfg = {"das_dir": str(self.das), "manifest": "x", "hotkey_file": "m.htk",
                    "base_hotkeys": "m.htk"}
        for target, value in (("build", lambda cfg, das: ([stage / "m.htk", stage / "m-win.cbf"],
                                                         "11-21 23:45:50")),
                              ("running_dir", lambda: None), ("STAGE", stage)):
            self.enterContext(mock.patch.object(install, target, value))

    def test_dry_run_copies_nothing(self):
        rc, out = run(install.install, self.cfg, False)
        self.assertEqual(rc, 0)
        self.assertEqual((self.das / "m.htk").read_bytes(), b"old")
        self.assertFalse((self.das / "m-win.cbf").exists())
        self.assertIn("Dry run", out)

    def test_write_backs_up_then_copies(self):
        rc, out = run(install.install, self.cfg, True, datetime(2026, 1, 2, 3, 4, 5))
        self.assertEqual(rc, 0)
        self.assertEqual((self.das / "m.htk").read_bytes(), b"new hotkeys")
        self.assertEqual((self.das / "m-win.cbf").read_bytes(), b"panel")
        self.assertEqual((install.STAGE / "backup" / "20260102-030405" / "m.htk").read_bytes(), b"old")
        self.assertIn("PING 23:45", out)

    def test_a_different_running_install_is_noted_not_refused(self):
        with mock.patch.object(install, "running_dir", lambda: self.tmp / "other"):
            rc, out = run(install.install, self.cfg, False)
        self.assertEqual(rc, 0)
        self.assertIn("not this folder", out)

    def test_main_stops_without_a_config_and_lists_without_choosing(self):
        with mock.patch.object(install, "candidates", lambda: [self.das, self.tmp / "b"]):
            rc, out = run(install.main, ["--config", str(self.tmp / "none.json")])
        self.assertEqual(rc, 2)
        self.assertIn("STOPPED", out)
        self.assertIn("does not choose", out)
        self.assertEqual((self.das / "m.htk").read_bytes(), b"old")


if __name__ == "__main__":
    unittest.main()
