import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

from tv_vpn.launcher import LaunchError, build_command, start_session

FAKE_SCRIPT = Path(__file__).resolve().parent.parent / "simulate" / "fake_teamviewer.py"


class BuildCommandTest(unittest.TestCase):
    def test_vpn_command(self):
        cmd = build_command(r"C:\TeamViewer\TeamViewer.exe", "123456789", "geheim", vpn=True)
        self.assertEqual(cmd, [r"C:\TeamViewer\TeamViewer.exe", "-i", "123456789", "--Password", "geheim", "--VPN"])

    def test_remote_command_zonder_vpn_flag(self):
        cmd = build_command("TeamViewer.exe", "123", "pw", vpn=False)
        self.assertNotIn("--VPN", cmd)
        self.assertEqual(cmd, ["TeamViewer.exe", "-i", "123", "--Password", "pw"])


class StartSessionSimulatedTest(unittest.TestCase):
    def test_simulated_vpn_writes_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "fake.log"
            env = dict(os.environ, FAKE_TV_LOG=str(log))
            old = os.environ.get("FAKE_TV_LOG")
            os.environ["FAKE_TV_LOG"] = str(log)
            try:
                result = start_session(None, "123456789", "geheim", vpn=True, simulate=True, fake_script=FAKE_SCRIPT)
                self.assertTrue(result.vpn)
                self.assertTrue(result.simulated)
                deadline = time.time() + 5
                while not (log.exists() and log.read_text(encoding="utf-8").strip()):
                    if time.time() > deadline:
                        self.fail("Simulatiescript heeft geen logregel geschreven binnen 5 seconden.")
                    time.sleep(0.05)
                entries = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()]
            finally:
                if old is None:
                    os.environ.pop("FAKE_TV_LOG", None)
                else:
                    os.environ["FAKE_TV_LOG"] = old
            self.assertEqual(len(entries), 1)
            argv = entries[0]["argv"]
            self.assertIn("-i", argv)
            self.assertIn("123456789", argv)
            self.assertIn("--VPN", argv)
            self.assertIn("geheim", argv)

    def test_missing_id_raises(self):
        with self.assertRaises(LaunchError):
            start_session("x.exe", "", "pw", simulate=True, fake_script=FAKE_SCRIPT)

    def test_missing_exe_raises(self):
        with self.assertRaises(LaunchError):
            start_session(r"C:\bestaat-niet\TeamViewer.exe", "123", "pw", simulate=False)


if __name__ == "__main__":
    unittest.main()
