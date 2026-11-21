"""Settings, read from the environment with development defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return int(raw) if raw else default


@dataclass
class Settings:
    service_name: str
    # Largest raw message accepted from the provider, in bytes.
    max_bytes: int
    # How many message summaries are kept in memory before the oldest is dropped.
    keep: int
    # The address customers write to. Shown on /health so a wrong deployment is easy to spot.
    inbox_address: str


def load_settings() -> Settings:
    """Build the settings from MAIL_INTAKE_* environment variables."""
    return Settings(
        service_name=os.environ.get("MAIL_INTAKE_SERVICE_NAME", "mail-intake"),
        max_bytes=_int("MAIL_INTAKE_MAX_BYTES", 2_000_000),
        keep=_int("MAIL_INTAKE_KEEP", 1000),
        inbox_address=os.environ.get("MAIL_INTAKE_INBOX_ADDRESS", "support@example.test"),
    )
