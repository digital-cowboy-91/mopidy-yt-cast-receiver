"""DIAL service implementation that exposes a YouTube cast endpoint for Mopidy."""

from __future__ import annotations

import json
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict
from urllib.parse import parse_qs, urlparse

from .mopidy import MopidyClient
from .pairing import PairingCode
from .ssdp import SSDPServer
from .youtube import YouTubeCastApp


def _build_device_descriptor(application_url: str, friendly_name: str, udn: str) -> str:
    """Return an XML descriptor that advertises the device to DIAL clients."""

    return f"""<?xml version="1.0"?>
<root xmlns="urn:schemas-upnp-org:device-1-0">
  <specVersion>
    <major>1</major>
    <minor>0</minor>
  </specVersion>
  <device>
    <deviceType>urn:schemas-upnp-org:device:dial:1</deviceType>
    <friendlyName>{friendly_name}</friendlyName>
    <manufacturer>Mopidy</manufacturer>
    <modelName>Mopidy YouTube Cast Receiver</modelName>
    <UDN>uuid:{udn}</UDN>
    <serviceList>
      <service>
        <serviceType>urn:dial-multiscreen-org:service:dial:1</serviceType>
        <serviceId>urn:dial-multiscreen-org:device:dial</serviceId>
        <controlURL></controlURL>
        <eventSubURL></eventSubURL>
        <SCPDURL></SCPDURL>
      </service>
    </serviceList>
    <presentationURL>{application_url}</presentationURL>
  </device>
  <URLBase>{application_url}</URLBase>
</root>
"""


class DialService:
    """Controller wiring SSDP discovery and HTTP DIAL endpoints."""

    def __init__(
        self,
        *,
        host: str = "0.0.0.0",
        port: int = 8009,
        friendly_name: str = "Mopidy YouTube Music",
        app_name: str = "YouTube",
        mopidy_rpc_url: str = "http://127.0.0.1:6680/mopidy/rpc",
        ssdp_port: int = 1900,
        pairing_code: str | None = None,
        require_pairing_code: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.friendly_name = friendly_name
        self.app_name = app_name
        self.application_url = f"http://{self.host}:{self.port}"
        self.udn = str(uuid.uuid4())
        self.ssdp_port = ssdp_port

        self._youtube_app = YouTubeCastApp(app_name)
        self._mopidy = MopidyClient(mopidy_rpc_url)
        self._pairing = PairingCode(pairing_code) if pairing_code else PairingCode.generate()
        self._require_pairing_code = require_pairing_code

        self._httpd: ThreadingHTTPServer | None = None
        self._http_thread: threading.Thread | None = None
        self._ssdp: SSDPServer | None = None

    def start(self) -> None:
        """Start the HTTP server and the SSDP responder."""

        handler = self._build_handler()
        self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
        bound_port = self._httpd.server_address[1]
        self.port = bound_port
        self.application_url = f"http://{self.host}:{bound_port}"

        self._http_thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._http_thread.start()

        self._ssdp = SSDPServer(
            location=f"{self.application_url}/ssdp/device-desc.xml",
            friendly_name=self.friendly_name,
            udn=self.udn,
            port=self.ssdp_port,
        )
        self._ssdp.start()

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._http_thread:
            self._http_thread.join()

        if self._ssdp:
            self._ssdp.stop()

    def _build_handler(self):
        service = self

        class DialHTTPRequestHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):  # noqa: A003
                return

            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path in ("/", ""):
                    self._send_response(
                        200,
                        "\n".join(
                            [
                                f"Mopidy YouTube Cast Receiver ({service.friendly_name})",
                                "This endpoint serves the YouTube DIAL namespace.",
                                "SSDP descriptor: /ssdp/device-desc.xml",
                                f"App status: /apps/{service.app_name}",
                                "TV code (use Link with TV code if discovery fails):",
                                f"  {service._pairing.formatted}",
                                "Pairing code API: /pairing/code",
                            ]
                        ),
                    )
                    return

                if parsed.path == "/ssdp/device-desc.xml":
                    descriptor = _build_device_descriptor(
                        application_url=service.application_url,
                        friendly_name=service.friendly_name,
                        udn=service.udn,
                    )
                    self._send_response(200, descriptor, "application/xml")
                    return

                if parsed.path == "/pairing/code":
                    code_payload = {
                        "code": service._pairing.normalized,
                        "formatted": service._pairing.formatted,
                    }
                    self._send_response(200, json.dumps(code_payload), "application/json")
                    return

                if parsed.path == f"/apps/{service.app_name}":
                    status = service._youtube_app.application_status(service.application_url)
                    self._send_response(200, status, "application/xml")
                    return

                self.send_error(404)

            def do_DELETE(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != f"/apps/{service.app_name}":
                    self.send_error(404)
                    return
                service._youtube_app.stop()
                self._send_response(200, "")

            def do_POST(self):  # noqa: N802
                parsed = urlparse(self.path)
                if parsed.path != f"/apps/{service.app_name}":
                    self.send_error(404)
                    return

                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length) if length else b""
                params = self._parse_params(raw_body.decode(), self.headers.get("Content-Type"))

                provided_code = params.get("pairingCode") or params.get("code")
                if (service._require_pairing_code or provided_code) and not service._pairing.matches(
                    provided_code
                ):
                    self.send_error(403, "Invalid or missing pairing code")
                    return

                launch_id = service._youtube_app.launch(params, service._mopidy)
                status_url = f"{service.application_url}/apps/{service.app_name}/{launch_id}"
                self.send_response(201)
                self.send_header("Location", status_url)
                self.end_headers()

            def _parse_params(self, body: str, content_type: str | None) -> Dict[str, str]:
                if not body:
                    return {}

                if content_type and "json" in content_type:
                    try:
                        data = json.loads(body)
                        return {key: str(value) for key, value in data.items()}
                    except json.JSONDecodeError:
                        pass

                parsed = parse_qs(body)
                return {key: values[0] for key, values in parsed.items()}

            def _send_response(self, code: int, payload: str, content_type: str = "text/plain") -> None:
                encoded = payload.encode()
                self.send_response(code)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                if encoded:
                    self.wfile.write(encoded)

        return DialHTTPRequestHandler


__all__ = ["DialService"]
