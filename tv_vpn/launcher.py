"""Start de lokale TeamViewer Classic-client via command-line parameters.

VPN via command line werkt alleen met TeamViewer Classic op Windows:
    TeamViewer.exe -i <teamviewer_id> --Password <wachtwoord> --VPN

In simulatiemodus wordt een nep-client gestart zodat de end-to-end flow
getest kan worden zonder echte TeamViewer-installatie.
"""

import subprocess
import sys
from pathlib import Path

DEFAULT_FAKE_SCRIPT = Path(__file__).resolve().parent.parent / "simulate" / "fake_teamviewer.py"


class LaunchError(Exception):
    pass


def build_command(exe_path, teamviewer_id, password, vpn=True):
    cmd = [str(exe_path), "-i", str(teamviewer_id), "--Password", str(password)]
    if vpn:
        cmd.append("--VPN")
    return cmd


class SessionResult:
    def __init__(self, pid, vpn, simulated):
        self.pid = pid
        self.vpn = vpn
        self.simulated = simulated

    @property
    def mode(self):
        return "VPN" if self.vpn else "Remote"


def start_session(exe_path, teamviewer_id, password, vpn=True, simulate=False, fake_script=None):
    if not teamviewer_id:
        raise LaunchError("Geen TeamViewer ID bekend voor dit systeem.")
    if simulate:
        script = Path(fake_script) if fake_script else DEFAULT_FAKE_SCRIPT
        if not script.exists():
            raise LaunchError(f"Simulatiescript niet gevonden: {script}")
        cmd = [sys.executable, str(script), "-i", str(teamviewer_id), "--Password", str(password)]
        if vpn:
            cmd.append("--VPN")
        simulated = True
    else:
        exe = Path(exe_path)
        if not exe.exists():
            raise LaunchError(f"TeamViewer.exe niet gevonden op: {exe}")
        cmd = build_command(exe, teamviewer_id, password, vpn=vpn)
        simulated = False

    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except OSError as e:
        raise LaunchError(f"Starten van de TeamViewer-client mislukt: {e}")
    return SessionResult(pid=proc.pid, vpn=vpn, simulated=simulated)
