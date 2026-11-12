"""Eenvoudige desktop-GUI (tkinter, alleen Python-standaardbibliotheek).

Live zoeken op systeemnaam, per systeem een VPN- en Remote-knop, en
statusfeedback onderin. De apparatenlijst wordt in een achtergrondthread
opgehaald zodat de UI niet blokkeert.
"""

import queue
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from .api import ApiError, filter_devices
from .credentials import CredentialStore
from .launcher import LaunchError, start_session

STATUS_COLORS = {
    "info": "#333333",
    "ok": "#1a7f37",
    "warn": "#9a6700",
    "error": "#cf222e",
}


class TeamViewerVpnApp(tk.Tk):
    def __init__(self, settings, api, cred_store):
        super().__init__()
        self.title("TeamViewer VPN Prototype")
        self.geometry("760x480")
        self.minsize(640, 360)

        self._settings = settings
        self._api = api
        self._creds = cred_store
        self._devices = []
        self._load_queue = queue.Queue()

        self._build_widgets()
        self._poll_load_queue()
        self._load_devices()

    def _build_widgets(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Zoeken op systeemnaam:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._render_rows())
        search_entry = ttk.Entry(top, textvariable=self.search_var, width=40)
        search_entry.pack(side=tk.LEFT, padx=(8, 8))
        search_entry.focus_set()
        ttk.Button(top, text="Vernieuwen", command=self._load_devices).pack(side=tk.LEFT)

        header = ttk.Frame(self, padding=(8, 0, 8, 0))
        header.pack(fill=tk.X)
        for text, width in (("Systeemnaam", 260), ("TeamViewer ID", 130), ("Status", 90)):
            ttk.Label(header, text=text, font=("TkDefaultFont", 9, "bold"), width=width // 8).pack(side=tk.LEFT)
        ttk.Label(header, text="").pack(side=tk.LEFT, fill=tk.X, expand=True)

        body_container = ttk.Frame(self)
        body_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self.canvas = tk.Canvas(body_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.rows_frame = ttk.Frame(self.canvas)
        self.rows_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_var = tk.StringVar(value="Apparatenlijst wordt opgehaald...")
        self.status_label = ttk.Label(self, textvariable=self.status_var, padding=8, foreground=STATUS_COLORS["info"])
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)

    def _set_status(self, message, kind="info"):
        self.status_var.set(message)
        self.status_label.configure(foreground=STATUS_COLORS.get(kind, STATUS_COLORS["info"]))

    def _load_devices(self):
        self._set_status("Apparatenlijst wordt opgehaald...", "info")

        def worker():
            try:
                devices = self._api.fetch_devices()
                self._load_queue.put(("ok", devices, None))
            except ApiError as e:
                self._load_queue.put(("error", None, e))

        threading.Thread(target=worker, daemon=True).start()

    def _poll_load_queue(self):
        try:
            while True:
                kind, devices, error = self._load_queue.get_nowait()
                if kind == "ok":
                    self._devices = devices
                    self._set_status(f"{len(devices)} systeem(en) geladen.", "ok")
                    self._render_rows()
                else:
                    self._set_status(str(error), "error")
        except queue.Empty:
            pass
        self.after(150, self._poll_load_queue)

    def _render_rows(self):
        for child in self.rows_frame.winfo_children():
            child.destroy()
        results = filter_devices(self._devices, self.search_var.get())
        if not results:
            ttk.Label(self.rows_frame, text="Geen systemen gevonden.", padding=8).pack(anchor=tk.W)
            return
        for device in results:
            self._build_row(device)

    def _build_row(self, device):
        row = ttk.Frame(self.rows_frame, padding=(0, 2))
        row.pack(fill=tk.X)

        ttk.Label(row, text=device["alias"], width=32).pack(side=tk.LEFT)
        ttk.Label(row, text=device["teamviewer_id"], width=16).pack(side=tk.LEFT)
        status_text = "Online" if device["online"] else "Offline"
        status_label = ttk.Label(row, text=status_text, width=10)
        status_label.configure(foreground=STATUS_COLORS["ok"] if device["online"] else STATUS_COLORS["error"])
        status_label.pack(side=tk.LEFT)

        ttk.Button(row, text="Remote", width=8, command=lambda d=device: self._connect(d, vpn=False)).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(row, text="VPN", width=8, command=lambda d=device: self._connect(d, vpn=True)).pack(side=tk.RIGHT)

    def _connect(self, device, vpn):
        if not device["online"]:
            self._set_status(
                f"Waarschuwing: '{device['alias']}' is offline; VPN-sessie wordt toch gestart.",
                "warn",
            )
        password = self._creds.get_device_password(device["teamviewer_id"])
        if password is None:
            password = simpledialog.askstring(
                "Wachtwoord",
                f"TeamViewer-wachtwoord voor {device['alias']} ({device['teamviewer_id']}):",
                show="*",
                parent=self,
            )
            if not password:
                self._set_status("Verbinding geannuleerd: geen wachtwoord opgegeven.", "warn")
                return
            self._creds.set_device_password(device["teamviewer_id"], password)

        try:
            result = start_session(
                self._settings["teamviewer_exe"],
                device["teamviewer_id"],
                password,
                vpn=vpn,
                simulate=bool(self._settings.get("simulate")),
                fake_script=self._settings.get("fake_teamviewer_script") or None,
            )
        except LaunchError as e:
            self._set_status(str(e), "error")
            messagebox.showerror("Verbinding mislukt", str(e), parent=self)
            return

        mode = result.mode
        if result.simulated:
            self._set_status(f"{mode}-sessie (simulatie) gestart naar {device['alias']} (pid {result.pid}).", "ok")
        else:
            self._set_status(f"{mode}-sessie gestart naar {device['alias']} (pid {result.pid}).", "ok")


def run_app(settings, api, cred_store=None):
    cred_store = cred_store or CredentialStore()
    app = TeamViewerVpnApp(settings, api, cred_store)
    app.mainloop()
