"""Constants for the REWE Discounts integration."""

DOMAIN = "rewe"
ATTRIBUTION = "Data provided by REWE mobile API"
PLATFORMS = ["sensor", "button", "binary_sensor"]

# Configuration keys
CONF_MARKET_ID = "market_id"
CONF_UPDATE_INTERVAL = "update_interval"

# Defaults
DEFAULT_UPDATE_INTERVAL = 24  # hours
MIN_UPDATE_INTERVAL = 1  # hours
MAX_UPDATE_INTERVAL = 24  # hours

# Auto-discovery
DISCOVERY_RADIUS_KM = 20.0

# Sensor attributes
ATTR_DISCOUNTS = "discounts"
ATTR_DISCOUNT_TITLE = "product"
ATTR_DISCOUNT_PRICE = "price"
ATTR_BASE_PRICE = "base_price"
ATTR_PICTURE = "picture_link"
ATTR_VALID_DATE = "valid_until"
ATTR_CATEGORY = "category"

# Cert paths (relative to this file's directory, bundled with the integration)
CERT_RELATIVE_PATH = "certs/client.pem"
KEY_RELATIVE_PATH = "certs/client.key"

# Issue IDs for HA Repairs
ISSUE_ID_CONNECTION = "connection_error"
ISSUE_ID_NO_CERTS = "missing_certificates"
