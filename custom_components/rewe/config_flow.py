"""Config flow for REWE Discounts integration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CERT_RELATIVE_PATH,
    CONF_MARKET_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    KEY_RELATIVE_PATH,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)
from .api import ReweAPIClient

_LOGGER = logging.getLogger(__name__)


class ReweConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for REWE Discounts."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._search_results: list[dict[str, Any]] = []

    def _check_certs_valid(self) -> bool:
        """Verify that mTLS certificates exist and can be parsed."""
        component_dir = Path(__file__).parent
        cert_path = component_dir / CERT_RELATIVE_PATH
        key_path = component_dir / KEY_RELATIVE_PATH

        _LOGGER.debug(
            "Verifying certificate presence at paths: cert=%s, key=%s",
            cert_path,
            key_path,
        )

        if not cert_path.exists() or not key_path.exists():
            _LOGGER.warning("One or both mTLS certificate files are missing.")
            return False

        try:
            from cryptography.x509 import load_pem_x509_certificate
            from cryptography.hazmat.primitives.serialization import (
                load_pem_private_key,
            )

            cert_bytes = cert_path.read_bytes()
            key_bytes = key_path.read_bytes()

            # Ensure we can load both PEM blocks successfully
            load_pem_x509_certificate(cert_bytes)
            load_pem_private_key(key_bytes, password=None)
            _LOGGER.debug("mTLS certificates are valid and successfully loaded.")
            return True
        except Exception as exc:
            _LOGGER.error("REWE certificate validation failed: %s", exc)
            return False

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial user input step."""
        _LOGGER.debug("async_step_user called with input: %s", user_input)
        errors: dict[str, str] = {}

        # First verify certificates. If invalid, block user setup
        if not await self.hass.async_add_executor_job(self._check_certs_valid):
            _LOGGER.warning(
                "Certificates invalid; redirecting user to invalid_certs step"
            )
            return await self.async_step_invalid_certs()

        if user_input is not None:
            user_value = user_input["search_or_id"].strip()

            # Direct numeric ID check (only for IDs with length > 5, 5 or fewer is treated as ZIP code search)
            if user_value.isdigit() and len(user_value) > 5:
                _LOGGER.debug("Direct market ID detected: %s", user_value)
                await self.async_set_unique_id(user_value)
                self._abort_if_unique_id_configured()
                _LOGGER.debug(
                    "Creating config entry directly for market ID: %s", user_value
                )
                return self.async_create_entry(
                    title=f"REWE {user_value}",
                    data={CONF_MARKET_ID: user_value},
                )

            # Search text path (including ZIP codes)
            try:
                component_dir = Path(__file__).parent
                cert_path = str(component_dir / CERT_RELATIVE_PATH)
                key_path = str(component_dir / KEY_RELATIVE_PATH)

                # Execute search in executor thread
                _LOGGER.debug("Executing market search for query: '%s'", user_value)
                client = ReweAPIClient(cert_path=cert_path, key_path=key_path)
                results = await self.hass.async_add_executor_job(
                    client.market_search, user_value
                )

                if not results:
                    _LOGGER.info("No markets found matching query '%s'", user_value)
                    errors["base"] = "no_markets_found"
                else:
                    _LOGGER.debug(
                        "Found %d markets matching query '%s'", len(results), user_value
                    )
                    self._search_results = results
                    return await self.async_step_select_market()

            except Exception as exc:
                _LOGGER.error("REWE market search error: %s", exc)
                errors["base"] = "search_failed"

        # Show input form for search queries or direct IDs
        schema = vol.Schema({vol.Required("search_or_id"): str})
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_invalid_certs(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Show blocking certificate error screen."""
        _LOGGER.debug("async_step_invalid_certs called with input: %s", user_input)
        if user_input is not None and self._check_certs_valid():
            # If the user corrected the certificates and clicked submit, proceed to user step
            _LOGGER.info("Certificates are now valid; moving to user step.")
            return await self.async_step_user()

        # Display block message with instructions
        return self.async_show_form(
            step_id="invalid_certs",
            errors={"base": "missing_certificates"},
            description_placeholders={
                "readme_url": "https://github.com/FaserF/ha-rewe#certificates"
            },
        )

    async def async_step_select_market(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle selecting a market from search results."""
        _LOGGER.debug("async_step_select_market called with input: %s", user_input)
        errors: dict[str, str] = {}

        if user_input is not None:
            market_id = user_input[CONF_MARKET_ID]
            await self.async_set_unique_id(market_id)
            self._abort_if_unique_id_configured()

            # Find the selected market name for the title
            selected_name = f"REWE {market_id}"
            entry_data = {CONF_MARKET_ID: market_id}
            for res in self._search_results:
                if str(res.get("wwIdent")) == market_id:
                    selected_name = (
                        f"REWE {res.get('name', 'Markt')} ({res.get('street', '')})"
                    )
                    entry_data["name"] = res.get("name", "REWE Markt")
                    entry_data["street"] = res.get("street", "")
                    entry_data["city"] = res.get("city", "")
                    break

            _LOGGER.info(
                "Creating config entry for market: %s (ID: %s)",
                selected_name,
                market_id,
            )
            return self.async_create_entry(
                title=selected_name,
                data=entry_data,
            )

        # Build dropdown options
        options: dict[str, str] = {}
        for res in self._search_results:
            market_id = str(res.get("wwIdent", ""))
            if market_id:
                name = res.get("name", "REWE Markt")
                street = res.get("street", "")
                city = res.get("city", "")
                options[market_id] = f"{name}, {street}, {city} (ID: {market_id})"

        if not options:
            return self.async_abort(reason="no_markets_found")

        schema = vol.Schema({vol.Required(CONF_MARKET_ID): vol.In(options)})
        return self.async_show_form(
            step_id="select_market",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> ReweOptionsFlowHandler:
        """Return the options flow handler."""
        return ReweOptionsFlowHandler(config_entry)


class ReweOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for REWE Discounts."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        super().__init__()
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        _LOGGER.debug(
            "ReweOptionsFlowHandler async_step_init called with input: %s", user_input
        )
        if user_input is not None:
            _LOGGER.info(
                "Updating options for REWE entry %s: %s",
                self.config_entry.entry_id,
                user_input,
            )
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL
        )

        options_schema = vol.Schema(
            {
                vol.Optional(CONF_UPDATE_INTERVAL, default=current_interval): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL),
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
