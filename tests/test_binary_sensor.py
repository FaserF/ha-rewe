"""Test the REWE Discounts binary sensor platform."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rewe.const import DOMAIN, CONF_MARKET_ID
from custom_components.rewe.binary_sensor import (
    async_setup_entry,
    ReweDeliveryAvailableSensor,
    RewePickupAvailableSensor,
)


def _make_coordinator(hass: HomeAssistant, entry: MockConfigEntry) -> MagicMock:
    coordinator = MagicMock()
    coordinator.market_id = "440421"
    coordinator.config_entry = entry
    coordinator.last_update_success = True
    coordinator.configuration_url = (
        "https://www.rewe.de/angebote/zorneding/440421/rewe-markt-georg-wimmer-ring-6/"
    )
    coordinator.data = {
        "service_portfolio": {
            "customerZipCode": "85604",
            "deliveryMarket": {
                "wwIdent": "320530",
                "name": "REWE Lieferdienst",
            },
            "pickupMarkets": [
                {
                    "wwIdent": "440421",
                    "displayName": "REWE Markt Georg Wimmer",
                    "companyName": "REWE Georg Wimmer oHG",
                    "isPickupStation": False,
                }
            ],
        }
    }
    return coordinator


async def test_binary_sensors_setup(hass: HomeAssistant) -> None:
    """Test that binary sensors are registered."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)

    assert async_add_entities.called
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 2
    types = {type(e) for e in entities}
    assert types == {
        ReweDeliveryAvailableSensor,
        RewePickupAvailableSensor,
    }


async def test_delivery_sensor(hass: HomeAssistant) -> None:
    """Test delivery available sensor values and attributes."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    sensor = ReweDeliveryAvailableSensor(coordinator)
    assert sensor.is_on is True
    attrs = sensor.extra_state_attributes
    assert attrs["delivery_market_id"] == "320530"
    assert attrs["delivery_market_name"] == "REWE Lieferdienst"


async def test_pickup_sensor(hass: HomeAssistant) -> None:
    """Test pickup available sensor values and attributes."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    sensor = RewePickupAvailableSensor(coordinator)
    assert sensor.is_on is True
    attrs = sensor.extra_state_attributes
    assert attrs["company_name"] == "REWE Georg Wimmer oHG"
    assert attrs["display_name"] == "REWE Markt Georg Wimmer"
    assert attrs["is_pickup_station"] is False
