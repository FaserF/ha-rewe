"""Test the REWE Discounts button platform."""

from unittest.mock import AsyncMock, MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rewe.const import DOMAIN, CONF_MARKET_ID
from custom_components.rewe.button import async_setup_entry, ReweForceUpdateButton


def _make_coordinator(entry: MockConfigEntry) -> MagicMock:
    coordinator = MagicMock()
    coordinator.market_id = "440421"
    coordinator.config_entry = entry
    coordinator._force_update = False
    coordinator.configuration_url = (
        "https://www.rewe.de/angebote/zorneding/440421/rewe-markt-georg-wimmer-ring-6/"
    )
    coordinator.async_request_refresh = AsyncMock()
    return coordinator


async def test_button_setup(hass: HomeAssistant) -> None:
    """Test that the force update button is registered."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)

    assert async_add_entities.called
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], ReweForceUpdateButton)


async def test_button_disabled_by_default(hass: HomeAssistant) -> None:
    """Force Update button must be disabled by default to avoid accidental triggers."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    button = ReweForceUpdateButton(coordinator)
    assert button.entity_registry_enabled_default is False


async def test_button_press(hass: HomeAssistant) -> None:
    """Test pressing the force update button triggers coordinator refresh."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    button = ReweForceUpdateButton(coordinator)
    await button.async_press()

    assert coordinator._force_update is True
    coordinator.async_request_refresh.assert_called_once()


async def test_button_configuration_url(hass: HomeAssistant) -> None:
    """Test that the button device uses the market-specific configuration_url."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    button = ReweForceUpdateButton(coordinator)
    device_info = button.device_info
    assert device_info is not None
    url = device_info.get("configuration_url")
    assert url is not None
    assert "440421" in str(url)
