"""Utility client that translates YouTube DIAL requests into Mopidy actions."""

from __future__ import annotations

import json
import urllib.request
from typing import Dict, Optional


class MopidyClient:
    """Send JSON-RPC requests to Mopidy's HTTP frontend."""

    def __init__(self, rpc_url: str) -> None:
        self.rpc_url = rpc_url.rstrip("/")

    def handle_launch(self, params: Dict[str, str]) -> None:
        """Prepare Mopidy to play a YouTube item using parameters from the phone."""

        video_id = params.get("v") or params.get("videoId") or params.get("url", "")
        if not video_id:
            return

        uri = f"ytmusic:video/{video_id}" if "://" not in video_id else video_id
        self.play_uri(uri, params.get("title"))

    def play_uri(self, uri: str, title: Optional[str] = None) -> None:
        payloads = [
            self._rpc_payload("core.tracklist.clear", {}),
            self._rpc_payload("core.tracklist.add", {"uris": [uri]}),
            self._rpc_payload("core.playback.play", {}),
        ]

        for payload in payloads:
            self._post(payload)

    def _post(self, payload: Dict) -> None:
        data = json.dumps(payload).encode()
        request = urllib.request.Request(
            self.rpc_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=2):
                pass
        except OSError:
            # The Mopidy API may be unreachable during tests; fail silently to keep the receiver responsive.
            pass

    def _rpc_payload(self, method: str, params: Dict) -> Dict:
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params,
        }
