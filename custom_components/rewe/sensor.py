"""Rewe.de sensor platform."""
from datetime import datetime, timedelta
import logging
import re
import json
from typing import Any, Callable, Dict, Optional
from rewe_discounts import rewe_discounts

import async_timeout

from homeassistant import config_entries, core
from homeassistant.helpers import aiohttp_client
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    HomeAssistantType,
)
import voluptuous as vol

from .const import (
    ATTRIBUTION,
    CONF_MARKET_ID,
    CONF_SCAN_INTERVAL,
    ATTR_DISCOUNTS,
    ATTR_HIGHLIGHTS,
    ATTR_DISCOUNT_NAME,
    ATTR_DISCOUNT_PRICE,
    ATTR_DISCOUNT_DESCRIPTION,
    ATTR_HIGHLIGHT_NAME,
    ATTR_HIGHLIGHT_PRICE,
    ATTR_HIGHLIGHT_DESCRIPTION,

    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigType, async_add_entities
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Sensor async_setup_entry")
    if entry.options:
        config.update(entry.options)
    sensors = ReweSensor(config, hass)
    async_add_entities(sensors, update_before_add=True)
    async_add_entities(
        [
            ReweSensor(config, hass)
        ],
        update_before_add=True
    )

class ReweSensor(Entity):
    """Collects and represents rewe discounts based on given market id"""

    def __init__(self, config, hass: HomeAssistantType):
        super().__init__()

        self.update_interval=timedelta(minutes=config[CONF_SCAN_INTERVAL]),
        self.market_id = config[CONF_MARKET_ID]
        self.hass = hass
        self.attrs: Dict[str, Any] = {CONF_MARKET_ID: self.market_id}
        self.updated = datetime.now()
        self._name = f"Rewe {self.market_id}"
        self._state = None
        self._available = True

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        #return self._name
        return f"Rewe-{self.market_id}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def icon(self) -> str:
        return "mdi:basket-unfill"

    @property
    def state(self) -> Optional[str]:
        if self._state is not None:
            return self._state
        else:
            return "Error"

    @property
    def unit_of_measurement(self):
        """Return unit of measurement."""
        return "baskets"

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        return self.attrs

    async def async_update(self):
        try:
            discounts = []
            highlights = []

            discounts.append(
                {
                    ATTR_DISCOUNT_NAME: "unavailable",
                    ATTR_DISCOUNT_PRICE: "unavailable",
                    ATTR_DISCOUNT_DESCRIPTION: "unavailable"
                }
            )

            highlights.append(
                {
                    ATTR_HIGHLIGHT_NAME: "unavailable",
                    ATTR_HIGHLIGHT_PRICE: "unavailable",
                    ATTR_HIGHLIGHT_DESCRIPTION: "unavailable"
                }
            )
            self.attrs[ATTR_DISCOUNTS] = discounts
            self.attrs[ATTR_HIGHLIGHTS] = highlights
            self.attrs[ATTR_ATTRIBUTION] = f"last updated {datetime.now()} \n{ATTRIBUTION}"
            self._state = baskets_count
            self._available = True
        except:
            self._available = False
            _LOGGER.exception(f"Cannot retrieve data for: '{self.market_id}'")
