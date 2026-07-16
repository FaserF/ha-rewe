"""REWE Discounts – Home Assistant Custom Component."""

from __future__ import annotations

import logging

from homeassistant import config_entries, core
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import CONF_MARKET_ID, DOMAIN, PLATFORMS
from .coordinator import ReweDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Set up REWE Discounts from a config entry."""
    _LOGGER.debug(
        "Setting up REWE Discounts entry: %s (market_id: %s)",
        entry.entry_id,
        entry.data.get(CONF_MARKET_ID),
    )
    hass.data.setdefault(DOMAIN, {})

    coordinator = ReweDataUpdateCoordinator(hass, entry)
    await coordinator.async_load_cache()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    try:
        await coordinator.async_config_entry_first_refresh()
    except UpdateFailed as err:
        if not coordinator.data:
            raise ConfigEntryNotReady(
                f"Cannot connect to REWE API for market {coordinator.market_id}: {err}"
            ) from err
        _LOGGER.warning(
            "Initial REWE update failed for market %s, using cached data. Error: %s",
            coordinator.market_id,
            err,
        )

    entry.async_on_unload(entry.add_update_listener(_async_update_options))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _LOGGER.debug("Finished setting up REWE Discounts entry: %s", entry.entry_id)
    return True


async def _async_update_options(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> None:
    """Reload the entry when options change."""
    _LOGGER.debug(
        "Reloading REWE entry %s due to option updates. New options: %s",
        entry.entry_id,
        entry.options,
    )
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(
    hass: core.HomeAssistant, entry: config_entries.ConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading REWE Discounts entry: %s", entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    _LOGGER.debug(
        "Unload result for REWE entry %s: %s", entry.entry_id, unload_ok
    )
    return unload_ok

