"""Entrypoint van het TeamViewer VPN prototype."""

import sys
import tkinter as tk
from tkinter import messagebox

from tv_vpn.api import ApiError, TeamViewerApi
from tv_vpn.config import load_settings
from tv_vpn.credentials import CredentialStore
from tv_vpn.gui import run_app


def resolve_api_token(settings, cred_store):
    token = cred_store.get_api_token()
    if token:
        return token
    return settings.get("api_token", "")


def main():
    settings = load_settings()
    cred_store = CredentialStore()
    token = resolve_api_token(settings, cred_store)
    if not token:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Geen API-token",
            "Configureer het TeamViewer API-token: via de Windows Credential Manager "
            "(target 'TeamViewerVPN/api_token') of via 'api_token' in settings.json.",
        )
        root.destroy()
        return 1
    api = TeamViewerApi(token, base_url=settings["api_base_url"], timeout=settings["api_timeout_seconds"])
    run_app(settings, api, cred_store)
    return 0


if __name__ == "__main__":
    sys.exit(main())
