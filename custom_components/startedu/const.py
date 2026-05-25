from __future__ import annotations

from datetime import timedelta

DOMAIN = "startedu"

CONF_BASE_URL = "base_url"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_BASE_URL = "https://startedu.pl/"
DEFAULT_SCAN_INTERVAL_MINUTES = 240
MIN_SCAN_INTERVAL_MINUTES = 15
MAX_SCAN_INTERVAL_MINUTES = 1440

PLATFORMS = ["calendar", "sensor"]
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=DEFAULT_SCAN_INTERVAL_MINUTES)

