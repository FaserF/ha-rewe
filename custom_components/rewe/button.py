"""REWE Discounts button platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import ReweDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up REWE Discounts button from a config entry."""
    coordinator: ReweDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug(
        "Setting up REWE Discounts button for market %s", coordinator.market_id
    )
    async_add_entities([ReweForceUpdateButton(coordinator)], update_before_add=False)


class ReweForceUpdateButton(ButtonEntity):
    """Button to force update REWE weekly offers."""

    _attr_icon = "mdi:refresh"
    _attr_has_entity_name = True
    _attr_name = "Force Update"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        """Initialize the button."""
        self.coordinator = coordinator
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}_force_update"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        _LOGGER.debug(
            "Initialized ReweForceUpdateButton for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    async def async_press(self) -> None:
        """Press the button."""
        _LOGGER.info("Forcing REWE weekly offers update for market %s", self._market_id)
        self.coordinator._force_update = True
        await self.coordinator.async_request_refresh()
