import stat
import sys
import tempfile
import unittest
from pathlib import Path

from tv_vpn.credentials import CredentialStore, FileCredentialStore


class FileCredentialStoreTest(unittest.TestCase):
    def test_roundtrip_en_verwijderen(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = FileCredentialStore(Path(tmp) / "creds.json")
            self.assertIsNone(store.get("TeamViewerVPN/device/123"))
            store.set("TeamViewerVPN/device/123", "geheim-wachtwoord")
            self.assertEqual(store.get("TeamViewerVPN/device/123"), "geheim-wachtwoord")
            store.delete("TeamViewerVPN/device/123")
            self.assertIsNone(store.get("TeamViewerVPN/device/123"))

    @unittest.skipIf(sys.platform == "win32", "posix-permissies alleen op niet-Windows")
    def test_bestand_heeft_beperkende_rechten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "creds.json"
            store = FileCredentialStore(path)
            store.set("x", "y")
            mode = stat.S_IMODE(path.stat().st_mode)
            self.assertEqual(mode, 0o600)


class CredentialStoreApiTest(unittest.TestCase):
    @unittest.skipIf(sys.platform == "win32", "op Windowsdraait dit tegen de echte Credential Manager")
    def test_api_token_via_file_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = CredentialStore(file_path=Path(tmp) / "creds.json")
            store.set_api_token("token-abc")
            self.assertEqual(store.get_api_token(), "token-abc")
            store.set_device_password("42", "pw-42")
            self.assertEqual(store.get_device_password("42"), "pw-42")


if __name__ == "__main__":
    unittest.main()
