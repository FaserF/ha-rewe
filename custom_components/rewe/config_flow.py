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

_LOGGER = logging.getLogger(__name__)


class ReweConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]
    """Handle a config flow for REWE Discounts."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._search_results: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial user input step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            user_value = user_input["search_or_id"].strip()
            
            # Direct numeric ID check (only for IDs with length > 5, 5 or fewer is treated as ZIP code search)
            if user_value.isdigit() and len(user_value) > 5:
                await self.async_set_unique_id(user_value)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"REWE {user_value}",
                    data={CONF_MARKET_ID: user_value},
                )

            # Search text path (including ZIP codes)
            try:
                # Resolve local cert paths
                component_dir = Path(__file__).parent
                cert_path = str(component_dir / CERT_RELATIVE_PATH)
                key_path = str(component_dir / KEY_RELATIVE_PATH)

                # Check if certs exist
                if not Path(cert_path).exists() or not Path(key_path).exists():
                    errors["base"] = "missing_certificates"
                else:
                    from rewerse import Rewerse

                    # Execute search in executor thread
                    client = Rewerse(cert=cert_path, key=key_path)
                    results = await self.hass.async_add_executor_job(
                        client.market_search, user_value
                    )

                    if not results:
                        errors["base"] = "no_markets_found"
                    else:
                        self._search_results = results
                        return await self.async_step_select_market()

            except ImportError:
                errors["base"] = "missing_rewerse_library"
            except OSError as exc:
                _LOGGER.error("REWE market search system library error (OSError): %s", exc)
                errors["base"] = "search_library_failed"
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

    async def async_step_select_market(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle selecting a market from search results."""
        errors: dict[str, str] = {}

        if user_input is not None:
            market_id = user_input[CONF_MARKET_ID]
            await self.async_set_unique_id(market_id)
            self._abort_if_unique_id_configured()
            
            # Find the selected market name for the title
            selected_name = f"REWE {market_id}"
            for res in self._search_results:
                if str(res.get("wwIdent")) == market_id:
                    selected_name = f"REWE {res.get('name', 'Markt')} ({res.get('street', '')})"
                    break

            return self.async_create_entry(
                title=selected_name,
                data={CONF_MARKET_ID: market_id},
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
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
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
