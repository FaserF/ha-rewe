"""Test the REWE Discounts diagnostics."""

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rewe.const import DOMAIN, CONF_MARKET_ID
from custom_components.rewe.diagnostics import async_get_config_entry_diagnostics
from custom_components.rewe.coordinator import ReweDataUpdateCoordinator


async def test_diagnostics(hass: HomeAssistant) -> None:
    """Test retrieving diagnostic information."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MARKET_ID: "440421"},
        options={"update_interval": 30},
    )
    entry.add_to_hass(hass)

    coordinator = ReweDataUpdateCoordinator(hass, entry)
    coordinator.data = {
        "discounts": [{"product": "Pringles", "price": "1.49 €"}],
        "bonus_discounts": [],
        "next_discounts": [],
        "next_bonus_discounts": [],
        "valid_until": "2025-07-20",
    }
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"]["entry_id"] == entry.entry_id
    assert diagnostics["entry"]["data"] == {CONF_MARKET_ID: "440421"}
    assert diagnostics["entry"]["options"] == {"update_interval": 30}
    assert diagnostics["coordinator"]["market_id"] == "440421"
    assert diagnostics["coordinator"]["offers_count"] == 1
    assert diagnostics["coordinator"]["next_offers_count"] == 0
    assert diagnostics["coordinator"]["bonus_offers_count"] == 0
    assert diagnostics["coordinator"]["next_bonus_offers_count"] == 0
    assert diagnostics["coordinator"]["has_data"] is True
