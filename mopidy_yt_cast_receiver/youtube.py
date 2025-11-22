"""YouTube DIAL application implementation."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, Optional

from .mopidy import MopidyClient


@dataclass
class LaunchState:
    """Track the most recent launch request."""

    launch_id: str
    timestamp: float
    parameters: Dict[str, str] = field(default_factory=dict)


class YouTubeCastApp:
    """Minimal DIAL application facade for the YouTube app."""

    def __init__(self, app_name: str) -> None:
        self.app_name = app_name
        self._is_running = False
        self._launch_state: Optional[LaunchState] = None

    def launch(self, params: Dict[str, str], mopidy: MopidyClient) -> str:
        """Handle a DIAL launch request and instruct Mopidy to play."""

        launch_id = uuid.uuid4().hex
        self._is_running = True
        self._launch_state = LaunchState(launch_id=launch_id, timestamp=time.time(), parameters=params)

        mopidy.handle_launch(params)
        return launch_id

    def stop(self) -> None:
        self._is_running = False

    def application_status(self, base_url: str) -> str:
        state = "running" if self._is_running else "stopped"
        launch_path = (
            f"<link rel=\"run\" href=\"{base_url}/apps/{self.app_name}/{self._launch_state.launch_id}\"/>"
            if self._launch_state
            else ""
        )
        return (
            f"<service xmlns=\"urn:dial-multiscreen-org:schemas:dial\">"
            f"<name>{self.app_name}</name>"
            f"<options allowStop=\"true\"/>"
            f"<state>{state}</state>"
            f"{launch_path}"
            f"</service>"
        )

    @property
    def last_launch(self) -> Optional[LaunchState]:
        return self._launch_state
