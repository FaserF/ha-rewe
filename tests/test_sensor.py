"""Test the REWE Discounts sensor platform."""

from unittest.mock import MagicMock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rewe.const import DOMAIN, CONF_MARKET_ID
from custom_components.rewe.sensor import (
    async_setup_entry,
    ReweSensor,
    ReweNextSensor,
    ReweBonusSensor,
    ReweNextBonusSensor,
    ReweMarketStatusSensor,
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
        "discounts": [{"product": "Pringles", "price": "1.49 €", "category": "Snacks"}],
        "bonus_discounts": [
            {
                "product": "Beer",
                "price": "2.49 €",
                "category": "Bier",
                "loyalty_bonus_value": 10,
                "loyalty_bonus_type": "cent",
            }
        ],
        "next_discounts": [
            {"product": "Apples", "price": "0.99 €", "category": "Obst"}
        ],
        "next_bonus_discounts": [
            {
                "product": "Bread",
                "price": "1.99 €",
                "category": "Frühstück",
                "loyalty_bonus_value": 20,
                "loyalty_bonus_type": "cent",
            }
        ],
        "valid_until": "2025-07-20",
        "next_valid_until": "2025-07-27",
        "market_details": {
            "wwIdent": "440421",
            "name": "REWE Markt Georg Wimmer",
            "companyName": "REWE Georg Wimmer oHG",
            "phone": "08106-12345",
            "street": "Georg-Wimmer-Ring 6",
            "zipCode": "85604",
            "city": "Zorneding",
            "location": {"latitude": 48.083, "longitude": 11.823},
            "openingStatus": {
                "openState": "OPEN",
                "infoText": "bis 20:00 Uhr",
                "statusText": "Geöffnet",
            },
            "openingInfo": [{"days": "Mo - Sa", "hours": "07:00 - 20:00"}],
            "category": {"marketTypeDisplayName": "REWE Markt"},
            "serviceFlags": {"hasPickup": True},
        },
    }
    return coordinator


async def test_sensors_setup(hass: HomeAssistant) -> None:
    """Test that four sensors are registered."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    async_add_entities = MagicMock()
    await async_setup_entry(hass, entry, async_add_entities)

    assert async_add_entities.called
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 5
    types = {type(e) for e in entities}
    assert types == {
        ReweSensor,
        ReweNextSensor,
        ReweBonusSensor,
        ReweNextBonusSensor,
        ReweMarketStatusSensor,
    }


async def test_offers_sensor(hass: HomeAssistant) -> None:
    """Test current offers sensor values and attributes."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    sensor = ReweSensor(coordinator)
    assert sensor.native_value == 1
    attrs = sensor.extra_state_attributes
    assert attrs["discounts"][0]["product"] == "Pringles"
    assert attrs["valid_until"] == "2025-07-20"


async def test_next_sensor(hass: HomeAssistant) -> None:
    """Test offers preview sensor values and attributes."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    sensor = ReweNextSensor(coordinator)
    assert sensor.native_value == 1
    attrs = sensor.extra_state_attributes
    assert attrs["discounts"][0]["product"] == "Apples"
    assert attrs["valid_until"] == "2025-07-27"


async def test_bonus_sensor(hass: HomeAssistant) -> None:
    """Test REWE Bonus offers sensor values and attributes."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    sensor = ReweBonusSensor(coordinator)
    assert sensor.native_value == 1
    attrs = sensor.extra_state_attributes
    assert attrs["discounts"][0]["product"] == "Beer"
    assert attrs["discounts"][0]["loyalty_bonus_value"] == 10


async def test_next_bonus_sensor(hass: HomeAssistant) -> None:
    """Test next week REWE Bonus offers sensor values and attributes."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    sensor = ReweNextBonusSensor(coordinator)
    assert sensor.native_value == 1
    attrs = sensor.extra_state_attributes
    assert attrs["discounts"][0]["product"] == "Bread"
    assert attrs["discounts"][0]["loyalty_bonus_value"] == 20


async def test_configuration_url_propagated(hass: HomeAssistant) -> None:
    """Test that the market-specific configuration_url is set on the device."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    sensor = ReweSensor(coordinator)
    device_info = sensor.device_info
    assert device_info is not None
    url = device_info.get("configuration_url")
    assert url is not None
    assert "440421" in str(url)


async def test_sensor_unavailable_when_no_data(hass: HomeAssistant) -> None:
    """Test sensors return None when coordinator has no data."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    coordinator.data = None
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    sensor = ReweSensor(coordinator)
    assert sensor.native_value is None


async def test_market_status_sensor(hass: HomeAssistant) -> None:
    """Test market status sensor values and attributes."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_MARKET_ID: "440421"}, options={})
    entry.add_to_hass(hass)

    coordinator = _make_coordinator(hass, entry)
    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    sensor = ReweMarketStatusSensor(coordinator)
    assert sensor.native_value == "Geöffnet"
    attrs = sensor.extra_state_attributes
    assert attrs["company_name"] == "REWE Georg Wimmer oHG"
    assert attrs["phone"] == "08106-12345"
    assert attrs["street"] == "Georg-Wimmer-Ring 6"
    assert attrs["zip_code"] == "85604"
    assert attrs["city"] == "Zorneding"
    assert attrs["latitude"] == 48.083
    assert attrs["longitude"] == 11.823
    assert attrs["open_state"] == "OPEN"
    assert attrs["info_text"] == "bis 20:00 Uhr"
    assert attrs["market_type"] == "REWE Markt"
    assert attrs["has_pickup"] is True
