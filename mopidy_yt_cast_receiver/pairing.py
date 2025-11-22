"""Utility to generate and verify TV-style pairing codes."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass


_DIGITS = "0123456789"


@dataclass
class PairingCode:
    """Represents a TV code used to authorize launches."""

    value: str

    @classmethod
    def generate(cls) -> "PairingCode":
        return cls("".join(random.choices(_DIGITS, k=12)))

    @property
    def normalized(self) -> str:
        return re.sub(r"\D", "", self.value)

    @property
    def formatted(self) -> str:
        digits = self.normalized
        return "-".join(digits[i : i + 3] for i in range(0, len(digits), 3))

    def matches(self, candidate: str | None) -> bool:
        if candidate is None:
            return False
        return self.normalized == re.sub(r"\D", "", candidate)
