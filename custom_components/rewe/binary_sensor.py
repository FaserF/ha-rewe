"""REWE Discounts binary sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
)
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_MARKET_ID, DOMAIN
from .coordinator import ReweDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up REWE Discounts binary sensor from a config entry."""
    coordinator: ReweDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug(
        "Setting up REWE Discounts binary sensors for market %s", coordinator.market_id
    )
    async_add_entities(
        [
            ReweDeliveryAvailableSensor(coordinator),
            RewePickupAvailableSensor(coordinator),
        ],
        update_before_add=False,
    )


class ReweDeliveryAvailableSensor(
    CoordinatorEntity[ReweDataUpdateCoordinator], BinarySensorEntity
):
    """Represents delivery availability for the local market ZIP code."""

    _attr_icon = "mdi:truck-delivery"
    _attr_has_entity_name = True
    _attr_name = "Delivery Available"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}_delivery_available"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        _LOGGER.debug(
            "Initialized ReweDeliveryAvailableSensor for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if delivery is available."""
        if not self.coordinator.data:
            return None
        portfolio = self.coordinator.data.get("service_portfolio", {})
        # If deliveryMarket exists and has a wwIdent, delivery is available
        delivery_market = portfolio.get("deliveryMarket")
        return bool(delivery_market and delivery_market.get("wwIdent"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return delivery metadata."""
        if not self.coordinator.data:
            return {ATTR_ATTRIBUTION: ATTRIBUTION}

        portfolio = self.coordinator.data.get("service_portfolio", {})
        delivery_market = portfolio.get("deliveryMarket") or {}

        return {
            CONF_MARKET_ID: self._market_id,
            "delivery_market_id": delivery_market.get("wwIdent"),
            "delivery_market_name": delivery_market.get("name"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has data."""
        return (
            self.coordinator.last_update_success and self.coordinator.data is not None
        )


class RewePickupAvailableSensor(
    CoordinatorEntity[ReweDataUpdateCoordinator], BinarySensorEntity
):
    """Represents pickup availability for the local market."""

    _attr_icon = "mdi:store-pickup"
    _attr_has_entity_name = True
    _attr_name = "Pickup Available"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}_pickup_available"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        _LOGGER.debug(
            "Initialized RewePickupAvailableSensor for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if pickup is available in the current market."""
        if not self.coordinator.data:
            return None
        portfolio = self.coordinator.data.get("service_portfolio", {})
        pickup_markets = portfolio.get("pickupMarkets", []) or []
        for market in pickup_markets:
            if str(market.get("wwIdent")) == self._market_id:
                return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return pickup metadata."""
        if not self.coordinator.data:
            return {ATTR_ATTRIBUTION: ATTRIBUTION}

        portfolio = self.coordinator.data.get("service_portfolio", {})
        pickup_markets = portfolio.get("pickupMarkets", []) or []

        # Find current pickup market info if matching
        info = {}
        for market in pickup_markets:
            if str(market.get("wwIdent")) == self._market_id:
                info = market
                break

        return {
            CONF_MARKET_ID: self._market_id,
            "display_name": info.get("displayName"),
            "company_name": info.get("companyName"),
            "is_pickup_station": info.get("isPickupStation"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has data."""
        return (
            self.coordinator.last_update_success and self.coordinator.data is not None
        )
