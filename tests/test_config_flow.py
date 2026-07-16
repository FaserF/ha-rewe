"""Test the REWE Discounts config flow."""

from unittest.mock import MagicMock, patch
import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from custom_components.rewe.const import DOMAIN, CONF_MARKET_ID

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_flow_direct_id(hass: HomeAssistant) -> None:
    """Test direct numeric market ID entry (length > 5)."""
    with patch(
        "custom_components.rewe.config_flow.ReweConfigFlow._check_certs_valid",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    with patch(
        "custom_components.rewe.config_flow.ReweConfigFlow._check_certs_valid",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"search_or_id": "440421"},
        )
    assert result["type"] == "create_entry"
    assert result["title"] == "REWE 440421"
    assert result["data"] == {CONF_MARKET_ID: "440421"}


async def test_flow_zip_search_and_select(hass: HomeAssistant) -> None:
    """Test entering a postal code/city search and selecting a market."""
    with patch(
        "custom_components.rewe.config_flow.ReweConfigFlow._check_certs_valid",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    mock_client = MagicMock()
    mock_client.market_search.return_value = [
        {
            "wwIdent": 123456,
            "name": "REWE Markt Garching",
            "street": "Einsteinstr. 1",
            "city": "Garching",
        }
    ]

    with (
        patch(
            "custom_components.rewe.config_flow.ReweConfigFlow._check_certs_valid",
            return_value=True,
        ),
        patch(
            "custom_components.rewe.config_flow.ReweAPIClient", return_value=mock_client
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"search_or_id": "85748"},
        )

    # Should take us to the selection step
    assert result["type"] == "form"
    assert result["step_id"] == "select_market"

    # Select the market
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_MARKET_ID: "123456"},
    )

    assert result["type"] == "create_entry"
    assert "REWE Markt Garching" in result["title"]
    assert result["data"] == {
        CONF_MARKET_ID: "123456",
        "name": "REWE Markt Garching",
        "street": "Einsteinstr. 1",
        "city": "Garching",
    }


async def test_flow_blocking_invalid_certs(hass: HomeAssistant) -> None:
    """Test that missing/invalid certs immediately blocks setup flow."""
    # Force _check_certs_valid to return False
    with patch(
        "custom_components.rewe.config_flow.ReweConfigFlow._check_certs_valid",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    # Must be redirected to invalid_certs blocking step
    assert result["type"] == "form"
    assert result["step_id"] == "invalid_certs"
    assert result["errors"] == {"base": "missing_certificates"}

    # Attempting to submit while still invalid keeps us on the same screen
    with patch(
        "custom_components.rewe.config_flow.ReweConfigFlow._check_certs_valid",
        return_value=False,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
    assert result["type"] == "form"
    assert result["step_id"] == "invalid_certs"

    # Correcting the certs and submitting lets us proceed
    with patch(
        "custom_components.rewe.config_flow.ReweConfigFlow._check_certs_valid",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {},
        )
    assert result["type"] == "form"
    assert result["step_id"] == "user"


async def test_flow_search_error(hass: HomeAssistant) -> None:
    """Test handling of search API failures."""
    with patch(
        "custom_components.rewe.config_flow.ReweConfigFlow._check_certs_valid",
        return_value=True,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )

    with (
        patch(
            "custom_components.rewe.config_flow.ReweConfigFlow._check_certs_valid",
            return_value=True,
        ),
        patch(
            "custom_components.rewe.config_flow.ReweAPIClient",
            side_effect=Exception("API failure"),
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"search_or_id": "München"},
        )

    assert result["type"] == "form"
    assert result["errors"] == {"base": "search_failed"}


async def test_options_flow(hass: HomeAssistant) -> None:
    """Test the options flow."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_MARKET_ID: "440421"},
        options={},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"update_interval": 60},
    )

    assert result["type"] == "create_entry"
    assert result["data"] == {"update_interval": 60}
