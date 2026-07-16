"""Diagnostics support for REWE weekly offers."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {
    "api_key",
    "password",
    "token",
    "session",
    "cert",
    "key",
    "webhook_id",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    diagnostics_data = {
        "entry": {
            "entry_id": entry.entry_id,
            "version": entry.version,
            "domain": entry.domain,
            "title": entry.title,
            "data": async_redact_data(entry.data, TO_REDACT),
            "options": async_redact_data(entry.options, TO_REDACT),
        },
        "coordinator": {
            "market_id": coordinator.market_id,
            "consecutive_failures": coordinator._consecutive_failures,
            "last_success": coordinator._last_success.isoformat()
            if coordinator._last_success
            else None,
            "backoff_until": coordinator._backoff_until.isoformat()
            if coordinator._backoff_until
            else None,
            "has_data": coordinator.data is not None,
            "offers_count": len(coordinator.data.get("discounts", []))
            if coordinator.data
            else 0,
            "next_offers_count": len(coordinator.data.get("next_discounts", []))
            if coordinator.data
            else 0,
            "bonus_offers_count": len(coordinator.data.get("bonus_discounts", []))
            if coordinator.data
            else 0,
            "next_bonus_offers_count": len(
                coordinator.data.get("next_bonus_discounts", [])
            )
            if coordinator.data
            else 0,
        },
    }

    return diagnostics_data
