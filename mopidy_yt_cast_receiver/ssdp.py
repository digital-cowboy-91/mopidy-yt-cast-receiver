"""Lightweight SSDP responder for DIAL discovery."""

from __future__ import annotations

import socket
import threading
from dataclasses import dataclass

DIAL_ST = "urn:dial-multiscreen-org:service:dial:1"


def _build_response(location: str, udn: str) -> bytes:
    return (
        "HTTP/1.1 200 OK\r\n"
        "CACHE-CONTROL: max-age=1800\r\n"
        "EXT:\r\n"
        f"LOCATION: {location}\r\n"
        "SERVER: Mopidy/1.0 UPnP/1.0 yt-cast-receiver/0.1\r\n"
        f"ST: {DIAL_ST}\r\n"
        f"USN: uuid:{udn}::{DIAL_ST}\r\n\r\n"
    ).encode()


@dataclass
class _SSDPConfig:
    location: str
    udn: str
    port: int


class SSDPServer:
    """Minimal SSDP responder that announces the DIAL service."""

    def __init__(self, *, location: str, friendly_name: str, udn: str, port: int = 1900) -> None:
        self.config = _SSDPConfig(location=location, udn=udn, port=port)
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = threading.Event()

    def start(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except OSError:
            pass
        sock.bind(("", self.config.port))
        self._socket = sock
        self._running.set()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running.clear()
        if self._socket:
            try:
                self._socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self._socket.close()
        if self._thread:
            self._thread.join()

    def _serve(self) -> None:
        assert self._socket is not None
        response = _build_response(self.config.location, self.config.udn)
        while self._running.is_set():
            try:
                data, addr = self._socket.recvfrom(1024)
            except OSError:
                break
            message = data.decode(errors="ignore")
            if "M-SEARCH" in message and DIAL_ST in message:
                try:
                    self._socket.sendto(response, addr)
                except OSError:
                    continue
