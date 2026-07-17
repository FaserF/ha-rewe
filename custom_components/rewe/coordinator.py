"""Data Update Coordinator for the REWE Discounts integration.

Fetches weekly offer data from REWE's mobile API via the `rewerse` library,
which handles mTLS authentication using client certificates bundled with this
integration (extracted from the REWE Android APK).

Anti-ban strategies (ported from ha-kadermanager):
- Random jitter delay (5–30 s) before each request
- Domain-wide asyncio.Lock to serialise concurrent fetches
- Exponential backoff on 403/429 (2 h per failure, max 24 h)
- Restart-resistance: last_success persisted via HA Storage
- Rotates User-Agent for curl_cffi impersonation
"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import issue_registry as ir, storage
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_BASE_PRICE,
    ATTR_CATEGORY,
    ATTR_DISCOUNT_PRICE,
    ATTR_DISCOUNT_TITLE,
    ATTR_PICTURE,
    ATTR_VALID_DATE,
    CERT_RELATIVE_PATH,
    CONF_MARKET_ID,
    CONF_UPDATE_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    ISSUE_ID_CONNECTION,
    ISSUE_ID_NO_CERTS,
    KEY_RELATIVE_PATH,
    MIN_UPDATE_INTERVAL,
)
from .api import ReweAPIClient

_LOGGER = logging.getLogger(__name__)

# curl_cffi impersonation profiles to rotate for anti-fingerprinting
_IMPERSONATE_PROFILES = [
    "chrome",
    "chrome110",
    "chrome120",
    "chrome124",
    "edge99",
    "edge101",
]


class ReweDataUpdateCoordinator(DataUpdateCoordinator):
    """Manage fetching REWE offer data from the mobile API."""

    config_entry: config_entries.ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: config_entries.ConfigEntry) -> None:
        config = {**entry.data, **entry.options}
        self.market_id: str = config[CONF_MARKET_ID]
        self.config_entry = entry

        # Anti-ban state
        self._backoff_until: datetime | None = None
        self._consecutive_failures: int = 0
        self._last_success: datetime | None = None
        self._issue_created: bool = False
        self._force_update: bool = False

        # HA persistent storage for restart-resistance
        self.store: storage.Store = storage.Store(hass, 1, f"{DOMAIN}_{self.market_id}")

        # Cert paths (bundled with the integration)
        component_dir = Path(__file__).parent
        self._cert_path = str(component_dir / CERT_RELATIVE_PATH)
        self._key_path = str(component_dir / KEY_RELATIVE_PATH)

        interval_hours = max(
            MIN_UPDATE_INTERVAL,
            config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        )
        if interval_hours < MIN_UPDATE_INTERVAL:
            _LOGGER.warning(
                "Update interval %d h is below minimum %d h; enforcing minimum",
                interval_hours,
                MIN_UPDATE_INTERVAL,
            )
            interval_hours = MIN_UPDATE_INTERVAL
        interval_minutes = interval_hours * 60

        _LOGGER.debug(
            "Initializing REWE update coordinator for market %s (interval: %d h)",
            self.market_id,
            interval_hours,
        )

        # Construct configuration URL dynamically
        city = entry.data.get("city")
        street = entry.data.get("street")
        name = entry.data.get("name", "REWE Markt")

        if city and street:

            def _slugify(text: str) -> str:
                text = text.lower()
                text = (
                    text.replace("\u00e4", "ae")
                    .replace("\u00f6", "oe")
                    .replace("\u00fc", "ue")
                    .replace("\u00df", "ss")
                )
                text = re.sub(r"[^a-z0-9\s-]", "", text)
                text = re.sub(r"[\s-]+", "-", text)
                return text.strip("-")

            city_slug = _slugify(city)
            name_slug = _slugify(name)
            street_slug = _slugify(street)
            self.configuration_url = f"https://www.rewe.de/angebote/{city_slug}/{self.market_id}/{name_slug}-{street_slug}/"
        else:
            self.configuration_url = (
                f"https://www.rewe.de/angebote/?marketId={self.market_id}"
            )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"REWE {self.market_id}",
            update_interval=timedelta(minutes=interval_minutes),
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    @property
    def is_data_valid(self) -> bool:
        """Return True if the current cached data is from the current week and valid."""
        if not self.data or not self._last_success:
            return False

        now = dt_util.now()
        current_monday = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return self._last_success >= current_monday

    async def async_load_cache(self) -> None:
        """Load cached data from HA storage (restart-resistance)."""
        _LOGGER.debug(
            "Attempting to load cached REWE data for market %s", self.market_id
        )
        cache = await self.store.async_load()
        if cache:
            # Validate cache schema – discard stale cache if mandatory keys are missing.
            # This handles cases where data-key renames would otherwise serve zeros.
            required_keys = {
                "discounts",
                "bonus_discounts",
                "valid_until",
                "market_details",
                "recalls",
                "service_portfolio",
                "recipe_hub",
            }
            if not required_keys.issubset(cache.keys()):
                _LOGGER.info(
                    "REWE cache for market %s is outdated (missing keys: %s) – discarding",
                    self.market_id,
                    required_keys - cache.keys(),
                )
                await self.store.async_remove()
                return

            _LOGGER.debug(
                "Successfully loaded cached REWE data for market %s", self.market_id
            )
            self.data = cache
            if "last_success" in cache:
                try:
                    self._last_success = dt_util.parse_datetime(cache["last_success"])
                    _LOGGER.debug(
                        "Loaded last success timestamp from cache: %s",
                        self._last_success,
                    )
                except (ValueError, TypeError):
                    self._last_success = None
        else:
            _LOGGER.debug("No cached REWE data found for market %s", self.market_id)

    # ------------------------------------------------------------------
    # Core update loop
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch new offer data – called by DataUpdateCoordinator on schedule."""
        _LOGGER.debug(
            "Starting REWE update cycle for market %s (force_update=%s)",
            self.market_id,
            self._force_update,
        )

        # Backoff guard
        if (
            not self._force_update
            and self._backoff_until
            and dt_util.now() < self._backoff_until
        ):
            _LOGGER.debug(
                "Skipping REWE update for market %s – backoff active until %s",
                self.market_id,
                self._backoff_until,
            )
            return self.data

        # Restart-resistance: skip if last fetch was very recent
        if not self._force_update and self._last_success is not None:
            time_since = dt_util.now() - self._last_success
            effective_interval = self.update_interval or timedelta(
                hours=DEFAULT_UPDATE_INTERVAL
            )
            if time_since < (effective_interval - timedelta(minutes=5)):
                _LOGGER.info(
                    "Skipping REWE update for market %s: last success was %d min ago "
                    "(interval %d min)",
                    self.market_id,
                    int(time_since.total_seconds() / 60),
                    int(effective_interval.total_seconds() / 60),
                )
                return self.data

        try:
            # Domain-wide lock: prevents multiple REWE entries from hitting the
            # API simultaneously (e.g., after HA reboot).
            domain_data = self.hass.data.setdefault(DOMAIN, {})
            fetch_lock: asyncio.Lock = domain_data.setdefault(
                "fetch_lock", asyncio.Lock()
            )

            _LOGGER.debug(
                "REWE market %s: requesting domain-wide fetch lock",
                self.market_id,
            )
            async with fetch_lock:
                _LOGGER.debug(
                    "REWE market %s: acquired domain-wide fetch lock",
                    self.market_id,
                )
                is_first_fetch = self._last_success is None
                if not self._force_update and not is_first_fetch:
                    jitter = random.uniform(5.0, 30.0)
                    _LOGGER.debug(
                        "REWE market %s: waiting %.1f s jitter before fetch to prevent rate limits",
                        self.market_id,
                        jitter,
                    )
                    await asyncio.sleep(jitter)
                elif is_first_fetch:
                    _LOGGER.debug(
                        "REWE market %s: first fetch – skipping jitter",
                        self.market_id,
                    )
                else:
                    _LOGGER.info(
                        "REWE market %s: forced update, skipping jitter",
                        self.market_id,
                    )
                    self._force_update = False

                _LOGGER.debug(
                    "REWE market %s: initiating API call via executor job",
                    self.market_id,
                )
                async with asyncio.timeout(90):
                    existing_cookies = self.config_entry.data.get("cookies", {})
                    data, new_cookies = await self.hass.async_add_executor_job(
                        self._fetch_offers_sync, existing_cookies
                    )

            _LOGGER.debug(
                "REWE market %s: fetch completed, updating success metadata",
                self.market_id,
            )
            self._last_success = dt_util.now()
            self._consecutive_failures = 0
            data["last_success"] = self._last_success.isoformat()
            await self.store.async_save(data)

            if new_cookies != existing_cookies:
                _LOGGER.debug(
                    "REWE market %s: updating session cookies in config entry",
                    self.market_id,
                )
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, "cookies": new_cookies},
                )

            # Clear any active repair issue
            if self._issue_created:
                _LOGGER.debug(
                    "REWE market %s: clearing active connection repair issue",
                    self.market_id,
                )
                ir.async_delete_issue(self.hass, DOMAIN, ISSUE_ID_CONNECTION)
                self._issue_created = False

            return data

        except Exception as err:
            self._consecutive_failures += 1
            _LOGGER.warning(
                "REWE market %s: fetch attempt failed (consecutive failures: %d). Error: %s",
                self.market_id,
                self._consecutive_failures,
                err,
            )

            # Raise a HA Repair issue if we haven't succeeded in 24 h
            if self._last_success and (dt_util.now() - self._last_success) > timedelta(
                hours=24
            ):
                if not self._issue_created:
                    _LOGGER.warning(
                        "REWE market %s: creating connection repair issue as no updates succeeded in 24 hours",
                        self.market_id,
                    )
                    ir.async_create_issue(
                        self.hass,
                        DOMAIN,
                        ISSUE_ID_CONNECTION,
                        is_fixable=False,
                        severity=ir.IssueSeverity.WARNING,
                        translation_key="connection_error",
                        learn_more_url="https://github.com/FaserF/ha-rewe/issues",
                    )
                    self._issue_created = True

            # Exponential backoff on rate-limit / blocked responses
            status = getattr(err, "status", None)
            err_str = str(err).lower()
            if status in (403, 429) or "403" in err_str or "429" in err_str:
                backoff_hours = min(24, self._consecutive_failures * 2)
                self._backoff_until = dt_util.now() + timedelta(hours=backoff_hours)
                _LOGGER.error(
                    "REWE market %s: rate-limited / blocked. Backing off %d h.",
                    self.market_id,
                    backoff_hours,
                )
            else:
                backoff_minutes = min(240, self._consecutive_failures * 30)
                self._backoff_until = dt_util.now() + timedelta(minutes=backoff_minutes)
                _LOGGER.error(
                    "REWE market %s: fetch error (failure #%d). Backing off %d min. "
                    "Error: %s",
                    self.market_id,
                    self._consecutive_failures,
                    backoff_minutes,
                    err,
                )

            raise UpdateFailed(
                f"Error fetching REWE offers for market {self.market_id}: {err}"
            ) from err

    # ------------------------------------------------------------------
    # Synchronous fetch (runs in executor thread)
    # ------------------------------------------------------------------

    def _fetch_offers_sync(
        self, cookies: dict[str, str]
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Fetch and parse REWE offers using ReweAPIClient + mTLS certs."""
        _LOGGER.debug(
            "REWE market %s: starting synchronous fetch sequence", self.market_id
        )
        self._check_certs()

        try:
            _LOGGER.debug(
                "REWE market %s: initializing ReweAPIClient with cert_path=%s, key_path=%s",
                self.market_id,
                self._cert_path,
                self._key_path,
            )
            client = ReweAPIClient(
                cert_path=self._cert_path,
                key_path=self._key_path,
                cookies=cookies,
            )
            raw = client.get_discounts(self.market_id)

            # Fetch market details (opening hours, address, name)
            try:
                market_details = client.get_market_details(self.market_id)
            except Exception as e:
                _LOGGER.warning(
                    "Could not fetch market details for market %s: %s",
                    self.market_id,
                    e,
                )
                market_details = {}

            zip_code = self.config_entry.data.get("zipCode")
            if not zip_code and market_details:
                zip_code = market_details.get("zipCode")

            # Fetch active recalls
            try:
                recalls = client.get_recalls()
            except Exception as e:
                _LOGGER.warning("Could not fetch REWE recalls: %s", e)
                recalls = []

            # Fetch service portfolio
            service_portfolio = {}
            if zip_code:
                try:
                    service_portfolio = client.get_service_portfolio(str(zip_code))
                except Exception as e:
                    _LOGGER.warning("Could not fetch service portfolio: %s", e)

            # Fetch recipe of the day
            try:
                recipe_hub = client.get_recipe_hub()
            except Exception as e:
                _LOGGER.warning("Could not fetch recipe hub: %s", e)
                recipe_hub = {}

        except Exception as exc:
            raise RuntimeError(
                f"ReweAPIClient.get_discounts failed for market {self.market_id}: {exc}"
            ) from exc

        parsed = self._parse_discounts(raw)
        parsed["market_details"] = market_details
        parsed["recalls"] = recalls
        parsed["service_portfolio"] = service_portfolio
        parsed["recipe_hub"] = recipe_hub
        cookies = client.cookies if isinstance(client.cookies, dict) else {}
        return parsed, cookies

    def _check_certs(self) -> None:
        """Raise a clear error if cert files are missing."""
        _LOGGER.debug(
            "REWE market %s: checking certificate presence at paths: cert=%s, key=%s",
            self.market_id,
            self._cert_path,
            self._key_path,
        )
        missing = []
        if not os.path.exists(self._cert_path):
            missing.append(self._cert_path)
        if not os.path.exists(self._key_path):
            missing.append(self._key_path)

        if missing:
            _LOGGER.error(
                "REWE market %s: missing certificate files: %s",
                self.market_id,
                missing,
            )
            # Create a HA Repair issue
            try:

                @callback
                def _create_issue() -> None:
                    ir.async_create_issue(
                        self.hass,
                        DOMAIN,
                        ISSUE_ID_NO_CERTS,
                        is_fixable=False,
                        severity=ir.IssueSeverity.ERROR,
                        translation_key="missing_certificates",
                        learn_more_url="https://github.com/FaserF/ha-rewe#certificates",
                    )

                self.hass.add_job(_create_issue)
            except Exception as e:
                _LOGGER.error(
                    "Failed to create missing certificate repair issue: %s", e
                )

            raise RuntimeError(
                f"REWE mTLS certificate files not found: {missing}. "
                "Please reinstall the integration from HACS to get the latest "
                "certificate bundle, or see the README for manual extraction steps."
            )

    # ------------------------------------------------------------------
    # Data parsing
    # ------------------------------------------------------------------

    def _parse_discounts(self, raw: dict | list) -> dict[str, Any]:
        """Parse the rewerse get_discounts response into HA-friendly format."""
        discounts: list[dict[str, Any]] = []
        bonus_discounts: list[dict[str, Any]] = []
        offers_valid_date: str | None = None
        next_discounts: list[dict[str, Any]] = []
        next_bonus_discounts: list[dict[str, Any]] = []
        next_valid_date: str | None = None

        if isinstance(raw, dict):
            # Parse current week
            until_ts = raw.get("untilDate") or raw.get("validUntil")
            if until_ts:
                offers_valid_date = self._parse_date_field(until_ts)
            categories = raw.get("categories", [])
            discounts = self._parse_categories(
                categories, offers_valid_date, include_bonus=False
            )
            bonus_discounts = self._parse_categories(
                categories, offers_valid_date, include_bonus=True
            )

            # Parse next week if available
            next_until_ts = raw.get("next_validUntil")
            if next_until_ts:
                next_valid_date = self._parse_date_field(next_until_ts)
            next_categories = raw.get("next_categories", [])
            next_discounts = self._parse_categories(
                next_categories, next_valid_date, include_bonus=False
            )
            next_bonus_discounts = self._parse_categories(
                next_categories, next_valid_date, include_bonus=True
            )
        elif isinstance(raw, list):
            discounts = self._parse_categories(raw, None, include_bonus=False)
            bonus_discounts = self._parse_categories(raw, None, include_bonus=True)

        _LOGGER.debug(
            "REWE market %s: parsed %d current offers (%d bonus), %d next offers (%d bonus)",
            self.market_id,
            len(discounts),
            len(bonus_discounts),
            len(next_discounts),
            len(next_bonus_discounts),
        )

        return {
            "discounts": discounts,
            "bonus_discounts": bonus_discounts,
            "valid_until": offers_valid_date,
            "next_discounts": next_discounts,
            "next_bonus_discounts": next_bonus_discounts,
            "next_valid_until": next_valid_date,
            "market_id": self.market_id,
        }

    def _parse_date_field(self, value: Any) -> str | None:
        """Parse timestamp/string into YYYY-MM-DD string."""
        if isinstance(value, (int, float)):
            try:
                return time.strftime("%Y-%m-%d", time.localtime(value / 1000))
            except Exception:
                return None
        if isinstance(value, str):
            if "-" in value:
                return value.split("T")[0]
            try:
                return time.strftime("%Y-%m-%d", time.localtime(int(value) / 1000))
            except Exception:
                return None
        return None

    def _parse_categories(
        self,
        categories: list,
        offers_valid_date: str | None,
        include_bonus: bool = False,
    ) -> list[dict[str, Any]]:
        """Parse categories into a list of offers.

        REWE Bonus offers are NOT in a dedicated category – they live across all
        categories and are identified by the presence of a ``loyaltyBonus`` field
        on the individual offer object.
        """
        discounts: list[dict[str, Any]] = []
        for category in categories:
            cat_title = category.get("title", "Unbekannt")

            for item in category.get("offers", []):
                try:
                    is_bonus = bool(item.get("loyaltyBonus"))
                    if is_bonus != include_bonus:
                        continue

                    title = (
                        item.get("title", "")
                        .replace("\n", " ")
                        .replace("\u2028", " ")
                        .strip()
                    )
                    subtitle = (
                        item.get("subtitle", "")
                        .replace("\n", " ")
                        .replace("\u2028", " ")
                        .strip()
                    )
                    price_data = item.get("priceData", {})
                    price = (
                        price_data.get("price", "")
                        if isinstance(price_data, dict)
                        else str(price_data)
                    )

                    # Per-offer valid date (fallback to global)
                    item_valid = offers_valid_date
                    item_until = item.get("validUntil") or item.get("untilDate")
                    if item_until:
                        item_valid = self._parse_date_field(item_until)

                    # Images
                    images = item.get("images", [])
                    image_url = images[0] if images else None

                    # REWE Bonus points / cents
                    loyalty = item.get("loyaltyBonus")
                    loyalty_value: int | None = None
                    loyalty_type: str | None = None
                    if isinstance(loyalty, dict):
                        loyalty_value = loyalty.get("bonusValue")
                        loyalty_type = loyalty.get("bonusType")

                    entry: dict[str, Any] = {
                        ATTR_DISCOUNT_TITLE: title,
                        ATTR_DISCOUNT_PRICE: price,
                        ATTR_BASE_PRICE: subtitle,
                        ATTR_PICTURE: image_url,
                        ATTR_VALID_DATE: item_valid,
                        ATTR_CATEGORY: cat_title,
                    }
                    if loyalty_value is not None:
                        entry["loyalty_bonus_value"] = loyalty_value
                        entry["loyalty_bonus_type"] = loyalty_type

                    discounts.append(entry)
                except Exception as exc:
                    _LOGGER.debug("Skipping malformed offer item: %s – %s", item, exc)
        return discounts
