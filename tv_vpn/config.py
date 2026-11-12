"""Instellingen laden en opslaan via settings.json naast main.py."""

import json
from pathlib import Path

DEFAULT_SETTINGS = {
    "api_base_url": "https://webapi.teamviewer.com/api/v1",
    "api_timeout_seconds": 15,
    "teamviewer_exe": r"C:\Program Files\TeamViewer\TeamViewer.exe",
    "simulate": False,
    "fake_teamviewer_script": "",
    "api_token": "",
}

DEFAULT_SETTINGS_PATH = Path(__file__).resolve().parent.parent / "settings.json"


def load_settings(path=DEFAULT_SETTINGS_PATH):
    path = Path(path)
    settings = dict(DEFAULT_SETTINGS)
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            user_settings = json.load(f)
        settings.update(user_settings)
    return settings


def save_settings(settings, path=DEFAULT_SETTINGS_PATH):
    path = Path(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    try:
        path.chmod(0o600)
    except OSError:
        pass
