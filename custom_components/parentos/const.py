"""Constants for ParentOS integration."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "parentos"
ATTRIBUTION = "Data provided by ParentOS — parentos.ai"

# Config keys
CONF_API_URL = "api_url"
CONF_API_TOKEN = "api_token"

# Defaults
DEFAULT_SCAN_INTERVAL = 300  # 5 minutes
DEFAULT_API_URL = "https://api.parentos.ai"

# Day states (mapped from HA API)
DAY_STATES = ["calm", "moderate", "busy", "full"]
