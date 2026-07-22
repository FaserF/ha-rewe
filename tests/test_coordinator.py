"""Test the REWE Discounts coordinator."""

from datetime import timedelta
from unittest.mock import MagicMock, patch
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry
from custom_components.rewe.coordinator import ReweDataUpdateCoordinator
from custom_components.rewe.const import DOMAIN, CONF_MARKET_ID

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_coordinator_fetch_success(hass: HomeAssistant, caplog) -> None:
    """Test successful data update and storage caching."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MARKET_ID: "440421"},
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = ReweDataUpdateCoordinator(hass, entry)

    mock_data = {
        "categories": [
            {
                "title": "Top-Angebote",
                "offers": [
                    {
                        "title": "Pringles",
                        "subtitle": "185g",
                        "priceData": {"price": "1.49 €"},
                    }
                ],
            }
        ],
        "untilDate": 1752969600000,
    }

    mock_client = MagicMock()
    mock_client.get_discounts.return_value = mock_data
    mock_client.get_market_details.return_value = {
        "wwIdent": "440421",
        "zipCode": "85604",
    }
    mock_client.get_recalls.return_value = [
        {
            "subjectProduct": "Raffelberger Mineralbrunnen",
            "subjectReason": "Verunreinigung",
            "url": "https://url",
        }
    ]
    mock_client.get_service_portfolio.return_value = {
        "customerZipCode": "85604",
        "deliveryMarket": {"wwIdent": "320530"},
    }
    mock_client.get_recipe_hub.return_value = {
        "recipeOfTheDay": {"title": "Zucchinigemüse"}
    }

    with (
        patch("os.path.exists", return_value=True),
        patch(
            "custom_components.rewe.coordinator.ReweAPIClient", return_value=mock_client
        ),
        patch("homeassistant.helpers.storage.Store.async_save") as mock_save,
        patch("asyncio.sleep"),
    ):
        res = await coordinator._async_update_data()
        assert res["valid_until"] == "2025-07-20"
        assert len(res["discounts"]) == 1
        assert res["discounts"][0]["product"] == "Pringles"
        assert res["market_details"]["wwIdent"] == "440421"
        assert len(res["recalls"]) == 1
        assert res["service_portfolio"]["customerZipCode"] == "85604"
        assert res["recipe_hub"]["recipeOfTheDay"]["title"] == "Zucchinigemüse"
        mock_save.assert_called_once()


async def test_coordinator_missing_certs(hass: HomeAssistant) -> None:
    """Test runtime error when certificates are missing."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MARKET_ID: "440421"},
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = ReweDataUpdateCoordinator(hass, entry)

    with (
        patch("os.path.exists", return_value=False),
        patch("asyncio.sleep"),
    ):
        with pytest.raises(UpdateFailed) as exc_info:
            await coordinator._async_update_data()
        assert "REWE mTLS certificate files not found" in str(exc_info.value)


async def test_coordinator_backoff_on_rate_limit(hass: HomeAssistant) -> None:
    """Test that consecutive failures trigger exponential backoffs."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MARKET_ID: "440421"},
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = ReweDataUpdateCoordinator(hass, entry)

    # Force a 403 HTTP block
    mock_client = MagicMock()
    error = RuntimeError("Status 403: Blocked by Cloudflare")
    mock_client.get_discounts.side_effect = error

    with (
        patch("os.path.exists", return_value=True),
        patch(
            "custom_components.rewe.coordinator.ReweAPIClient", return_value=mock_client
        ),
        patch("asyncio.sleep"),
    ):
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        assert coordinator._backoff_until is not None
        assert coordinator._consecutive_failures == 1


async def test_bonus_classification_via_loyalty_bonus(hass: HomeAssistant) -> None:
    """REWE Bonus offers are identified by loyaltyBonus field, not category title."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MARKET_ID: "440421"},
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = ReweDataUpdateCoordinator(hass, entry)

    categories = [
        {
            "title": "Top-Angebote",
            "offers": [
                {
                    "title": "Normal Offer",
                    "subtitle": "",
                    "priceData": {"price": "1.99 €"},
                    # no loyaltyBonus → regular offer
                },
                {
                    "title": "REWE Bonus Offer",
                    "subtitle": "",
                    "priceData": {"price": "2.99 €"},
                    "loyaltyBonus": {"bonusValue": 50, "bonusType": "cent"},
                },
            ],
        }
    ]

    regular = coordinator._parse_categories(
        categories, "2025-07-20", include_bonus=False
    )
    bonus = coordinator._parse_categories(categories, "2025-07-20", include_bonus=True)

    assert len(regular) == 1
    assert regular[0]["product"] == "Normal Offer"

    assert len(bonus) == 1
    assert bonus[0]["product"] == "REWE Bonus Offer"
    assert bonus[0]["loyalty_bonus_value"] == 50
    assert bonus[0]["loyalty_bonus_type"] == "cent"


async def test_configuration_url_slug_generation(hass: HomeAssistant) -> None:
    """Test that configuration_url is correctly slugified from city/street/name."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_MARKET_ID: "440421",
            "city": "Zorneding",
            "street": "Georg-Wimmer-Ring 6",
            "name": "REWE Markt",
        },
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = ReweDataUpdateCoordinator(hass, entry)

    assert "zorneding" in coordinator.configuration_url
    assert "440421" in coordinator.configuration_url
    assert "rewe-markt" in coordinator.configuration_url
    assert coordinator.configuration_url.startswith("https://www.rewe.de/angebote/")


async def test_configuration_url_fallback(hass: HomeAssistant) -> None:
    """Test that configuration_url falls back to marketId query param when no city data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MARKET_ID: "440421"},
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = ReweDataUpdateCoordinator(hass, entry)

    assert "440421" in coordinator.configuration_url
    assert "marketId=440421" in coordinator.configuration_url


async def test_coordinator_cookie_persistence(hass: HomeAssistant) -> None:
    """Test that coordinator persists session cookies in the config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MARKET_ID: "440421", "cookies": {"old_session": "123"}},
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = ReweDataUpdateCoordinator(hass, entry)

    mock_client = MagicMock()
    mock_client.get_discounts.return_value = {
        "categories": [],
        "untilDate": 1752969600000,
    }
    mock_client.cookies = {"old_session": "123", "new_session": "456"}

    with (
        patch("os.path.exists", return_value=True),
        patch(
            "custom_components.rewe.coordinator.ReweAPIClient", return_value=mock_client
        ) as mock_client_class,
        patch("homeassistant.helpers.storage.Store.async_save"),
        patch("asyncio.sleep"),
    ):
        await coordinator._async_update_data()

        mock_client_class.assert_called_once_with(
            cert_path=coordinator._cert_path,
            key_path=coordinator._key_path,
            cookies={"old_session": "123"},
        )

        assert entry.data.get("cookies") == {"old_session": "123", "new_session": "456"}


async def test_coordinator_is_data_valid(hass: HomeAssistant, freezer) -> None:
    """Test coordinator is_data_valid property behavior."""
    freezer.move_to("2026-07-22 12:00:00")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MARKET_ID: "440421"},
        options={},
    )
    entry.add_to_hass(hass)

    coordinator = ReweDataUpdateCoordinator(hass, entry)

    # No data/no last success -> False
    assert coordinator.is_data_valid is False

    # Mock data and success timestamp
    coordinator.data = {"discounts": []}

    # 1. Success was yesterday (in current week) -> True
    now = dt_util.now()
    coordinator._last_success = now - timedelta(days=1)
    assert coordinator.is_data_valid is True

    # 2. Success was 10 days ago (previous week) -> False
    coordinator._last_success = now - timedelta(days=10)
    assert coordinator.is_data_valid is False
