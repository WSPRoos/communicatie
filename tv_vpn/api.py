"""TeamViewer REST API: Computers & Contacts-lijst ophalen.

De API kan zelf geen VPN-tunnel opzetten; deze module levert alleen de apparatenlijst.
Het token wordt nooit in excepties, logs of foutmeldingen opgenomen.
"""

import json
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://webapi.teamviewer.com/api/v1"


class ApiError(Exception):
    KIND_UNAUTHORIZED = "unauthorized"
    KIND_RATE_LIMITED = "rate_limited"
    KIND_NETWORK = "network"
    KIND_HTTP = "http"
    KIND_PARSE = "parse"

    def __init__(self, kind, message):
        self.kind = kind
        super().__init__(message)


def normalize_device(raw):
    """Breng een API-apparaat terug tot de velden die de app gebruikt."""
    tv_id = raw.get("remotecontrol_id") or raw.get("teamviewer_id") or raw.get("device_id") or ""
    online_state = str(raw.get("online_state", ""))
    return {
        "alias": str(raw.get("alias") or raw.get("name") or "(zonder naam)"),
        "teamviewer_id": str(tv_id),
        "online": online_state.lower() == "online",
        "online_state": online_state or "Onbekend",
    }


def filter_devices(devices, query):
    """Case-insensitive partieel zoeken op alias; lege query geeft alles terug."""
    q = (query or "").strip().lower()
    if not q:
        return list(devices)
    return [d for d in devices if q in d["alias"].lower()]


class TeamViewerApi:
    def __init__(self, token, base_url=DEFAULT_BASE_URL, timeout=15):
        if not token:
            raise ApiError(ApiError.KIND_UNAUTHORIZED, "Geen API-token geconfigureerd.")
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def fetch_devices(self):
        url = f"{self._base_url}/devices"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise ApiError(ApiError.KIND_UNAUTHORIZED, "API-token ongeldig of verlopen (HTTP %d)." % e.code)
            if e.code == 429:
                raise ApiError(ApiError.KIND_RATE_LIMITED, "Te veel API-aanroepen (rate limit, HTTP 429). Probeer het straks opnieuw.")
            raise ApiError(ApiError.KIND_HTTP, "API-fout: HTTP %d." % e.code)
        except urllib.error.URLError as e:
            raise ApiError(ApiError.KIND_NETWORK, "Geen netwerkverbinding met de TeamViewer API (%s)." % e.reason)
        except TimeoutError:
            raise ApiError(ApiError.KIND_NETWORK, "Time-out bij het ophalen van de apparatenlijst.")

        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, ValueError):
            raise ApiError(ApiError.KIND_PARSE, "Ongeldig JSON-antwoord van de TeamViewer API.")

        raw_devices = payload.get("devices", [])
        if not isinstance(raw_devices, list):
            raise ApiError(ApiError.KIND_PARSE, "Onverwachte structuur in API-antwoord.")
        return [normalize_device(d) for d in raw_devices]
