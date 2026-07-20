"""REWE Discounts – Home Assistant Custom Component."""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

from homeassistant import config_entries, core
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import (
    CERT_RELATIVE_PATH,
    CONF_MARKET_ID,
    DISCOVERY_RADIUS_KM,
    DOMAIN,
    KEY_RELATIVE_PATH,
    PLATFORMS,
)
from .coordinator import ReweDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return distance in km between two GPS coordinates."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def async_setup(hass: core.HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the REWE integration.

    When 'rewe:' is listed in configuration.yaml (zero-entry bootstrap),
    this is the only hook HA calls.
    """
    domain_data = hass.data.setdefault(DOMAIN, {})
    if not domain_data.get("_discovery_scheduled"):
        domain_data["_discovery_scheduled"] = True

        async def _on_ha_started(event: core.Event) -> None:  # noqa: RUF100
            await _async_discover_markets(hass)

        if hass.is_running:
            hass.async_create_task(_async_discover_markets(hass))
        else:
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_ha_started)

    return True


async def _async_discover_markets(hass: core.HomeAssistant) -> None:
    """Search for nearby REWE markets and trigger integration discovery."""
    ha_lat = hass.config.latitude
    ha_lon = hass.config.longitude

    if not ha_lat or not ha_lon:
        _LOGGER.debug("REWE discovery: HA home location not set, skipping")
        return

    # Build search query: ZIP code is most reliable for the market API.
    zip_code: str = getattr(hass.config, "zip_code", "") or ""
    location_name: str = hass.config.location_name or ""
    query = zip_code.strip() or location_name.strip()
    if not query:
        _LOGGER.debug(
            "REWE discovery: no ZIP code or location_name configured, skipping"
        )
        return

    # mTLS certificates required for REWE API
    component_dir = Path(__file__).parent
    cert_path = str(component_dir / CERT_RELATIVE_PATH)
    key_path = str(component_dir / KEY_RELATIVE_PATH)
    if (
        not (component_dir / CERT_RELATIVE_PATH).exists()
        or not (component_dir / KEY_RELATIVE_PATH).exists()
    ):
        _LOGGER.debug("REWE discovery: mTLS certs missing, skipping auto-discovery")
        return

    _LOGGER.debug("REWE discovery: searching markets for '%s'", query)

    from .api import ReweAPIClient

    try:
        client = ReweAPIClient(cert_path=cert_path, key_path=key_path)
        markets: list[dict[str, Any]] = await hass.async_add_executor_job(
            client.market_search, query
        )
    except Exception as exc:
        _LOGGER.debug("REWE discovery: API error during search: %s", exc)
        return

    configured_ids = {
        entry.data.get(CONF_MARKET_ID)
        for entry in hass.config_entries.async_entries(DOMAIN)
    }

    # Collect ALL markets within radius (including already-configured ones)
    # so we can determine the true geographic nearest before deciding.
    candidates: list[tuple[float, dict[str, Any]]] = []
    for market in markets:
        market_id = str(market.get("wwIdent", "")).strip()
        if not market_id:
            continue

        dist = DISCOVERY_RADIUS_KM  # default if no coords available
        market_lat = market.get("latitude") or market.get("lat")
        market_lon = market.get("longitude") or market.get("lng")
        if market_lat is not None and market_lon is not None:
            try:
                dist = _haversine_km(
                    ha_lat, ha_lon, float(market_lat), float(market_lon)
                )
            except (TypeError, ValueError):
                pass  # keep default distance → included

        if dist <= DISCOVERY_RADIUS_KM:
            candidates.append((dist, market))

    if not candidates:
        _LOGGER.debug(
            "REWE discovery: no markets found within %.0f km", DISCOVERY_RADIUS_KM
        )
        return

    candidates.sort(key=lambda t: t[0])
    nearest_dist, nearest = candidates[0]
    nearest_market_id = str(nearest.get("wwIdent", "")).strip()

    # If the geographically nearest market is already configured, stop entirely.
    if nearest_market_id in configured_ids:
        _LOGGER.debug(
            "REWE discovery: nearest market %s is already configured, skipping discovery",
            nearest_market_id,
        )
        return

    market_id = str(nearest.get("wwIdent", "")).strip()
    name = nearest.get("name") or "REWE Markt"
    street = nearest.get("street") or ""
    city = nearest.get("city") or ""

    _LOGGER.debug(
        "REWE discovery: triggering flow for nearest market %s (%s, %.1f km)",
        market_id,
        name,
        nearest_dist,
    )
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_INTEGRATION_DISCOVERY},
            data={
                CONF_MARKET_ID: market_id,
                "name": name,
                "street": street,
                "city": city,
            },
        )
    )


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

    domain_data = hass.data[DOMAIN]
    if not domain_data.get("_discovery_scheduled"):
        domain_data["_discovery_scheduled"] = True

        async def _on_ha_started(event: core.Event) -> None:  # noqa: RUF100
            await _async_discover_markets(hass)

        if hass.is_running:
            hass.async_create_task(_async_discover_markets(hass))
        else:
            hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_ha_started)

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
    _LOGGER.debug("Unload result for REWE entry %s: %s", entry.entry_id, unload_ok)
    return unload_ok
