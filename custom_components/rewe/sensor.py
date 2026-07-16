"""REWE Discounts sensor platform."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTRIBUTION,
    ATTR_DISCOUNTS,
    ATTR_VALID_DATE,
    CONF_MARKET_ID,
    DOMAIN,
)
from .coordinator import ReweDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up REWE Discounts sensor from a config entry."""
    coordinator: ReweDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug(
        "Setting up REWE Discounts sensor for market %s", coordinator.market_id
    )
    async_add_entities([ReweSensor(coordinator)], update_before_add=False)


class ReweSensor(CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity):
    """Represents current REWE weekly offers for a given market."""

    _attr_icon = "mdi:cart-percent"
    _attr_native_unit_of_measurement = "items"

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_name = f"REWE {self._market_id}"
        self._attr_unique_id = f"rewe_{self._market_id}"
        _LOGGER.debug(
            "Initialized ReweSensor for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    @property
    def native_value(self) -> int | None:
        """Return the number of current offers."""
        if not self.coordinator.data:
            return None
        discounts = self.coordinator.data.get("discounts", [])
        return len(discounts)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed offer data as attributes."""
        data = self.coordinator.data or {}
        return {
            CONF_MARKET_ID: self._market_id,
            ATTR_DISCOUNTS: data.get("discounts", []),
            ATTR_VALID_DATE: data.get("valid_until"),
            ATTR_ATTRIBUTION: f"Last updated {datetime.now().strftime('%Y-%m-%d %H:%M')} · {ATTRIBUTION}",
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has data."""
        return (
            self.coordinator.last_update_success and self.coordinator.data is not None
        )
