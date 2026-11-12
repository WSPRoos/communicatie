import io
import json
import unittest
import urllib.error
from unittest import mock

from tv_vpn.api import ApiError, TeamViewerApi, filter_devices, normalize_device

DEVICES_PAYLOAD = {
    "devices": [
        {"remotecontrol_id": "123456789", "alias": "Server-01", "online_state": "Online"},
        {"teamviewer_id": "987654321", "alias": "Laptop-Support", "online_state": "Offline"},
        {"device_id": "555000111", "alias": "werkPlek-03", "online_state": "Online"},
    ]
}


def fake_response(payload, status=200):
    body = json.dumps(payload).encode("utf-8")
    resp = mock.Mock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = lambda s, *a: False
    return resp


class FetchDevicesTest(unittest.TestCase):
    def setUp(self):
        self.api = TeamViewerApi("test-token", base_url="https://example.test/api/v1")

    def test_fetch_devices_normaliseert_velden(self):
        with mock.patch("urllib.request.urlopen", return_value=fake_response(DEVICES_PAYLOAD)) as m:
            devices = self.api.fetch_devices()
        self.assertEqual(len(devices), 3)
        self.assertEqual(devices[0], {
            "alias": "Server-01",
            "teamviewer_id": "123456789",
            "online": True,
            "online_state": "Online",
        })
        self.assertEqual(devices[1]["teamviewer_id"], "987654321")
        self.assertFalse(devices[1]["online"])
        request = m.call_args[0][0]
        self.assertEqual(request.full_url, "https://example.test/api/v1/devices")
        self.assertEqual(request.headers["Authorization"], "Bearer test-token")

    def test_unauthorized(self):
        err = urllib.error.HTTPError("https://x", 401, "Unauthorized", {}, io.BytesIO(b""))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(ApiError) as ctx:
                self.api.fetch_devices()
        self.assertEqual(ctx.exception.kind, ApiError.KIND_UNAUTHORIZED)
        self.assertNotIn("test-token", str(ctx.exception))
        err.close()

    def test_rate_limited(self):
        err = urllib.error.HTTPError("https://x", 429, "Too Many Requests", {}, io.BytesIO(b""))
        with mock.patch("urllib.request.urlopen", side_effect=err):
            with self.assertRaises(ApiError) as ctx:
                self.api.fetch_devices()
        self.assertEqual(ctx.exception.kind, ApiError.KIND_RATE_LIMITED)
        err.close()

    def test_network_error(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no route")):
            with self.assertRaises(ApiError) as ctx:
                self.api.fetch_devices()
        self.assertEqual(ctx.exception.kind, ApiError.KIND_NETWORK)

    def test_invalid_json(self):
        resp = mock.Mock()
        resp.read.return_value = b"<html>not json</html>"
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: False
        with mock.patch("urllib.request.urlopen", return_value=resp):
            with self.assertRaises(ApiError) as ctx:
                self.api.fetch_devices()
        self.assertEqual(ctx.exception.kind, ApiError.KIND_PARSE)

    def test_leeg_token_gooit_fout(self):
        with self.assertRaises(ApiError):
            TeamViewerApi("")


class FilterDevicesTest(unittest.TestCase):
    def setUp(self):
        self.devices = [normalize_device(d) for d in DEVICES_PAYLOAD["devices"]]

    def test_leeg_query_geeft_alles(self):
        self.assertEqual(len(filter_devices(self.devices, "")), 3)
        self.assertEqual(len(filter_devices(self.devices, "   ")), 3)

    def test_partiele_case_insensitive_match(self):
        result = filter_devices(self.devices, "server")
        self.assertEqual([d["alias"] for d in result], ["Server-01"])
        result = filter_devices(self.devices, "WERK")
        self.assertEqual([d["alias"] for d in result], ["werkPlek-03"])
        result = filter_devices(self.devices, "p")
        self.assertEqual(len(result), 2)

    def test_geen_match(self):
        self.assertEqual(filter_devices(self.devices, "bestaat-niet"), [])


if __name__ == "__main__":
    unittest.main()
