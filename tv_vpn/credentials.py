"""Veilige opslag van TeamViewer-wachtwoorden en het API-token.

Primair wordt de Windows Credential Manager gebruikt (via ctypes, geen extra
dependencies). Op niet-Windows systemen (alleen voor development/tests) valt de
store terug op een lokaal bestand met beperkende rechten (0600). Wachtwoorden
worden nooit hardcoded of gelogd.
"""

import ctypes
import ctypes.wintypes as wt
import json
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

TARGET_PREFIX = "TeamViewerVPN"
API_TOKEN_TARGET = f"{TARGET_PREFIX}/api_token"

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2


class CREDENTIAL(ctypes.Structure):
    _fields_ = [
        ("Flags", wt.DWORD),
        ("Type", wt.DWORD),
        ("TargetName", wt.LPWSTR),
        ("Comment", wt.LPWSTR),
        ("LastWritten", wt.FILETIME),
        ("CredentialBlobSize", wt.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_char)),
        ("Persist", wt.DWORD),
        ("AttributeCount", wt.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wt.LPWSTR),
        ("UserName", wt.LPWSTR),
    ]


class CredentialError(Exception):
    pass


def _cred_write(target, secret):
    cred = CREDENTIAL()
    cred.Type = CRED_TYPE_GENERIC
    cred.TargetName = target
    cred.Persist = CRED_PERSIST_LOCAL_MACHINE
    blob = secret.encode("utf-8")
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(ctypes.create_string_buffer(blob, len(blob)), ctypes.POINTER(ctypes.c_char))
    if not ctypes.windll.advapi32.CredWriteW(ctypes.byref(cred), 0):
        raise CredentialError(f"Wachtwoord opslaan mislukt voor '{target}'.")


def _cred_read(target):
    ptr = ctypes.POINTER(CREDENTIAL)()
    if not ctypes.windll.advapi32.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(ptr)):
        return None
    try:
        cred = ptr.contents
        blob = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
        return blob.decode("utf-8")
    finally:
        ctypes.windll.advapi32.CredFree(ptr)


class FileCredentialStore:
    """Fallback voor niet-Windows omgevingen (development/tests)."""

    def __init__(self, path):
        self._path = Path(path)

    def _load(self):
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, data):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        try:
            self._path.chmod(0o600)
        except OSError:
            pass

    def get(self, target):
        return self._load().get(target)

    def set(self, target, secret):
        data = self._load()
        data[target] = secret
        self._save(data)

    def delete(self, target):
        data = self._load()
        if target in data:
            del data[target]
            self._save(data)


class CredentialStore:
    """Wachtwoorden per TeamViewer-ID + het API-token veilig bewaren."""

    def __init__(self, file_path=None):
        if IS_WINDOWS:
            self._backend = "windows"
            self._file_store = None
        else:
            self._backend = "file"
            path = file_path or (Path(__file__).resolve().parent.parent / "data" / "credentials.local.json")
            self._file_store = FileCredentialStore(path)

    @staticmethod
    def _device_target(teamviewer_id):
        return f"{TARGET_PREFIX}/device/{teamviewer_id}"

    def get_secret(self, target):
        if self._backend == "windows":
            return _cred_read(target)
        return self._file_store.get(target)

    def set_secret(self, target, secret):
        if self._backend == "windows":
            _cred_write(target, secret)
        else:
            self._file_store.set(target, secret)

    def delete_secret(self, target):
        if self._backend == "windows":
            ctypes.windll.advapi32.CredDeleteW(target, CRED_TYPE_GENERIC, 0)
        else:
            self._file_store.delete(target)

    def get_api_token(self):
        return self.get_secret(API_TOKEN_TARGET)

    def set_api_token(self, token):
        self.set_secret(API_TOKEN_TARGET, token)

    def get_device_password(self, teamviewer_id):
        return self.get_secret(self._device_target(teamviewer_id))

    def set_device_password(self, teamviewer_id, password):
        self.set_secret(self._device_target(teamviewer_id), password)
