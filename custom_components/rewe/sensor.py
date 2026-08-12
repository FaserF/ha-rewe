"""REWE Discounts sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_DISCOUNTS,
    ATTR_VALID_DATE,
    ATTRIBUTION,
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
        "Setting up REWE Discounts sensors for market %s", coordinator.market_id
    )
    async_add_entities(
        [
            ReweSensor(coordinator),
            ReweNextSensor(coordinator),
            ReweBonusSensor(coordinator),
            ReweNextBonusSensor(coordinator),
            ReweMarketStatusSensor(coordinator),
            ReweRecallsSensor(coordinator),
        ],
        update_before_add=False,
    )

    if coordinator.user_token:
        created_account_entities = hass.data[DOMAIN].setdefault(
            "_created_account_entities", set()
        )
        if coordinator.account_key not in created_account_entities:
            created_account_entities.add(coordinator.account_key)
            async_add_entities(
                [
                    ReweActivatedCouponsSensor(coordinator),
                    ReweAvailableCouponsSensor(coordinator),
                    ReweLastReceiptSensor(coordinator),
                ],
                update_before_add=False,
            )


class ReweSensor(CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity):
    """Represents current REWE weekly offers for a given market."""

    _attr_icon = "mdi:cart-percent"
    _attr_native_unit_of_measurement = "items"
    _attr_has_entity_name = True
    _attr_name = "Offers"
    # The full discounts list can be hundreds of KB – exclude from recorder
    # while keeping it fully available at runtime for Lovelace/automations.
    _unrecorded_attributes = frozenset({ATTR_DISCOUNTS})

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
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
        """Return offer metadata. The full discounts list is excluded from recorder."""
        data = self.coordinator.data or {}
        return {
            CONF_MARKET_ID: self._market_id,
            ATTR_DISCOUNTS: data.get("discounts", []),
            ATTR_VALID_DATE: data.get("valid_until"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has data."""
        return (
            self.coordinator.last_update_success or self.coordinator.is_data_valid
        ) and self.coordinator.data is not None


class ReweNextSensor(CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity):
    """Represents upcoming (next week) REWE weekly offers for a given market."""

    _attr_icon = "mdi:calendar-arrow-right"
    _attr_native_unit_of_measurement = "items"
    _attr_has_entity_name = True
    _attr_name = "Offers Preview"
    _unrecorded_attributes = frozenset({ATTR_DISCOUNTS})

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}_next"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        _LOGGER.debug(
            "Initialized ReweNextSensor for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    @property
    def native_value(self) -> int | None:
        """Return the number of upcoming offers."""
        if not self.coordinator.data:
            return None
        discounts = self.coordinator.data.get("next_discounts", [])
        return len(discounts)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed offer data as attributes."""
        data = self.coordinator.data or {}
        return {
            CONF_MARKET_ID: self._market_id,
            ATTR_DISCOUNTS: data.get("next_discounts", []),
            ATTR_VALID_DATE: data.get("next_valid_until"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has data."""
        return (
            self.coordinator.last_update_success or self.coordinator.is_data_valid
        ) and self.coordinator.data is not None


class ReweBonusSensor(CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity):
    """Represents current REWE Bonus offers for a given market."""

    _attr_icon = "mdi:star-circle"
    _attr_native_unit_of_measurement = "items"
    _attr_has_entity_name = True
    _attr_name = "REWE Bonus"
    _unrecorded_attributes = frozenset({ATTR_DISCOUNTS})

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}_bonus"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        _LOGGER.debug(
            "Initialized ReweBonusSensor for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    @property
    def native_value(self) -> int | None:
        """Return the number of current REWE Bonus offers."""
        if not self.coordinator.data:
            return None
        discounts = self.coordinator.data.get("bonus_discounts", [])
        return len(discounts)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed offer data as attributes."""
        data = self.coordinator.data or {}
        return {
            CONF_MARKET_ID: self._market_id,
            ATTR_DISCOUNTS: data.get("bonus_discounts", []),
            ATTR_VALID_DATE: data.get("valid_until"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has data."""
        return (
            self.coordinator.last_update_success or self.coordinator.is_data_valid
        ) and self.coordinator.data is not None


class ReweNextBonusSensor(CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity):
    """Represents upcoming (next week) REWE Bonus offers for a given market."""

    _attr_icon = "mdi:star-circle-outline"
    _attr_native_unit_of_measurement = "items"
    _attr_has_entity_name = True
    _attr_name = "REWE Bonus Preview"
    _unrecorded_attributes = frozenset({ATTR_DISCOUNTS})

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}_bonus_next"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        _LOGGER.debug(
            "Initialized ReweNextBonusSensor for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    @property
    def native_value(self) -> int | None:
        """Return the number of upcoming REWE Bonus offers."""
        if not self.coordinator.data:
            return None
        discounts = self.coordinator.data.get("next_bonus_discounts", [])
        return len(discounts)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed offer data as attributes."""
        data = self.coordinator.data or {}
        return {
            CONF_MARKET_ID: self._market_id,
            ATTR_DISCOUNTS: data.get("next_bonus_discounts", []),
            ATTR_VALID_DATE: data.get("next_valid_until"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has data."""
        return (
            self.coordinator.last_update_success or self.coordinator.is_data_valid
        ) and self.coordinator.data is not None


class ReweMarketStatusSensor(
    CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity
):
    """Represents status (open/closed) and metadata of the local REWE market."""

    _attr_icon = "mdi:store"
    _attr_has_entity_name = True
    _attr_name = "Market Status"

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}_status"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        _LOGGER.debug(
            "Initialized ReweMarketStatusSensor for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    @property
    def native_value(self) -> str | None:
        """Return the opening status text (e.g. Geöffnet / Geschlossen)."""
        if not self.coordinator.data:
            return None
        market_details = self.coordinator.data.get("market_details")
        if not market_details:
            return None
        opening_status = market_details.get("openingStatus", {})
        open_state = opening_status.get("openState")
        status_text = opening_status.get("statusText")
        if open_state == "OPEN":
            return status_text or "Geöffnet"
        if open_state == "CLOSED":
            return status_text or "Geschlossen"
        return status_text

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed market metadata."""
        if not self.coordinator.data:
            return {ATTR_ATTRIBUTION: ATTRIBUTION}

        market_details = self.coordinator.data.get("market_details") or {}
        opening_status = market_details.get("openingStatus", {})
        category = market_details.get("category", {})
        service_flags = market_details.get("serviceFlags", {})
        location = market_details.get("location", {})

        content = market_details.get("content", {}) or {}
        services = content.get("services", {}) or {}
        fixed_services = [
            s.get("text") for s in services.get("fixed", []) or [] if s.get("active")
        ]
        editable_services = [
            s.get("text") for s in services.get("editable", []) or [] if s.get("active")
        ]
        all_services = fixed_services + editable_services

        return {
            CONF_MARKET_ID: self._market_id,
            "company_name": market_details.get("companyName"),
            "phone": market_details.get("phone"),
            "street": market_details.get("street"),
            "zip_code": market_details.get("zipCode"),
            "city": market_details.get("city"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "open_state": opening_status.get("openState"),
            "info_text": opening_status.get("infoText"),
            "opening_hours": market_details.get("openingInfo", []),
            "market_type": category.get("marketTypeDisplayName"),
            "has_pickup": service_flags.get("hasPickup"),
            "services": all_services,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has data."""
        return (
            self.coordinator.last_update_success or self.coordinator.is_data_valid
        ) and self.coordinator.data is not None


class ReweRecallsSensor(CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity):
    """Represents current active product recalls."""

    _attr_icon = "mdi:alert-decagram"
    _attr_native_unit_of_measurement = "recalls"
    _attr_has_entity_name = True
    _attr_name = "Product Recalls"

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}_recalls"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        _LOGGER.debug(
            "Initialized ReweRecallsSensor for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    @property
    def native_value(self) -> int | None:
        """Return the number of active product recalls."""
        if not self.coordinator.data:
            return None
        recalls = self.coordinator.data.get("recalls", [])
        return len(recalls)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return list of active recalls with product details and reasons."""
        if not self.coordinator.data:
            return {ATTR_ATTRIBUTION: ATTRIBUTION}

        recalls = self.coordinator.data.get("recalls", [])
        formatted_recalls = []
        for r in recalls:
            formatted_recalls.append(
                {
                    "product": r.get("subjectProduct"),
                    "reason": r.get("subjectReason"),
                    "url": r.get("url"),
                }
            )

        return {
            "recalls": formatted_recalls,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has data."""
        return (
            self.coordinator.last_update_success or self.coordinator.is_data_valid
        ) and self.coordinator.data is not None


class ReweRecipeOfTheDaySensor(
    CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity
):
    """Represents the REWE recipe of the day."""

    _attr_icon = "mdi:silverware-fork-knife"
    _attr_has_entity_name = True
    _attr_name = "Recipe of the Day"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._market_id = coordinator.market_id
        self._attr_unique_id = f"rewe_{self._market_id}_recipe_of_the_day"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        _LOGGER.debug(
            "Initialized ReweRecipeOfTheDaySensor for market %s (unique_id: %s)",
            self._market_id,
            self._attr_unique_id,
        )

    @property
    def native_value(self) -> str | None:
        """Return the recipe title."""
        if not self.coordinator.data:
            return None
        recipe_hub = self.coordinator.data.get("recipe_hub", {})
        recipe = recipe_hub.get("recipeOfTheDay", {})
        return recipe.get("title")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return recipe details."""
        if not self.coordinator.data:
            return {ATTR_ATTRIBUTION: ATTRIBUTION}

        recipe_hub = self.coordinator.data.get("recipe_hub", {})
        recipe = recipe_hub.get("recipeOfTheDay", {})

        return {
            "recipe_id": recipe.get("id"),
            "detail_url": recipe.get("detailUrl"),
            "image_url": recipe.get("imageUrl"),
            "duration": recipe.get("duration"),
            "difficulty_description": recipe.get("difficultyDescription"),
            "difficulty_level": recipe.get("difficultyLevel"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if coordinator has recipe data."""
        if not self.coordinator.data or not self.coordinator.last_update_success:
            return False
        recipe_hub = self.coordinator.data.get("recipe_hub", {})
        recipe = recipe_hub.get("recipeOfTheDay", {})
        return bool(recipe.get("title"))


class ReweActivatedCouponsSensor(
    CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity
):
    """Represents activated REWE Bonus coupons."""

    _attr_icon = "mdi:ticket-confirmation"
    _attr_native_unit_of_measurement = "items"
    _attr_has_entity_name = True
    _attr_name = "Activated Coupons"
    _unrecorded_attributes = frozenset({"coupons"})

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._account_key = coordinator.account_key
        self._attr_unique_id = f"rewe_{self._account_key}_activated_coupons"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._account_key)},
            name="REWE Account (DE)",
            manufacturer="REWE",
            model="REWE Customer Account",
            configuration_url=coordinator.account_configuration_url,
        )

    @property
    def _activated_coupons(self) -> list[dict[str, Any]]:
        if not self.coordinator.data:
            return []
        coupons: list[dict[str, Any]] = self.coordinator.data.get("coupons", [])
        return [c for c in coupons if c.get("activated", False)]

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data:
            return None
        return len(self._activated_coupons)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        coupons = self._activated_coupons
        return {
            "coupons": coupons,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        return (
            self.coordinator.data is not None
            and "coupons" in self.coordinator.data
            and bool(self.coordinator.user_token)
        )


class ReweAvailableCouponsSensor(
    CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity
):
    """Represents available (non-activated) REWE Bonus coupons."""

    _attr_icon = "mdi:ticket-percent"
    _attr_native_unit_of_measurement = "items"
    _attr_has_entity_name = True
    _attr_name = "Available Coupons"
    _unrecorded_attributes = frozenset({"coupons"})

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._account_key = coordinator.account_key
        self._attr_unique_id = f"rewe_{self._account_key}_available_coupons"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._account_key)},
            name="REWE Account (DE)",
            manufacturer="REWE",
            model="REWE Customer Account",
            configuration_url=coordinator.account_configuration_url,
        )

    @property
    def _available_coupons(self) -> list[dict[str, Any]]:
        if not self.coordinator.data:
            return []
        coupons: list[dict[str, Any]] = self.coordinator.data.get("coupons", [])
        return [c for c in coupons if not c.get("activated", False)]

    @property
    def native_value(self) -> int | None:
        if not self.coordinator.data:
            return None
        return len(self._available_coupons)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        coupons = self._available_coupons
        return {
            "coupons": coupons,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        return (
            self.coordinator.data is not None
            and "coupons" in self.coordinator.data
            and bool(self.coordinator.user_token)
        )


class ReweLastReceiptSensor(CoordinatorEntity[ReweDataUpdateCoordinator], SensorEntity):
    """Represents the last REWE purchase receipt."""

    _attr_icon = "mdi:receipt"
    _attr_has_entity_name = True
    _attr_name = "Last Receipt"

    def __init__(self, coordinator: ReweDataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._account_key = coordinator.account_key
        self._attr_unique_id = f"rewe_{self._account_key}_last_receipt"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._account_key)},
            name="REWE Account (DE)",
            manufacturer="REWE",
            model="REWE Customer Account",
            configuration_url=coordinator.account_configuration_url,
        )

    @property
    def native_value(self) -> str | None:
        if not self.coordinator.data:
            return None
        receipt = self.coordinator.data.get("last_receipt")
        if not receipt:
            return None
        total = receipt.get("total")
        currency = receipt.get("currency", "EUR")
        return f"{total} {currency}".strip() if total is not None else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        receipt = data.get("last_receipt") or {}
        return {
            "date": receipt.get("date"),
            "store": receipt.get("store"),
            "total": receipt.get("total"),
            "currency": receipt.get("currency"),
            "articles_count": receipt.get("articles_count"),
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        return (
            self.coordinator.data is not None
            and "last_receipt" in self.coordinator.data
            and bool(self.coordinator.user_token)
        )
