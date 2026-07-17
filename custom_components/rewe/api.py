"""Pure Python client for REWE Mobile API using curl_cffi and mTLS."""

from __future__ import annotations

import logging
from typing import Any
from curl_cffi import requests

_LOGGER = logging.getLogger(__name__)


class ReweAPIClient:
    """API client that interacts directly with REWE mobile endpoints using mTLS."""

    def __init__(
        self,
        cert_path: str,
        key_path: str,
        cookies: dict[str, str] | None = None,
    ) -> None:
        """Initialize the client with mTLS certificate paths and optional cookies."""
        self.cert_path = cert_path
        self.key_path = key_path
        self.cookies: dict[str, str] = cookies or {}

    def _request(self, url: str, params: dict[str, Any] | None = None) -> Any:
        """Perform a secure GET request using curl_cffi with mTLS."""
        # User-Agent matching the official REWE Mobile Client
        headers = {
            "User-Agent": "REWE-Mobile-Client/3.17.1.32270 Android/11 Phone/Google_sdk_gphone_x86_64",
            "Accept": "application/json",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        _LOGGER.debug("Sending GET request to url: %s (params: %s)", url, params)
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                cert=(self.cert_path, self.key_path),
                cookies=self.cookies,
                timeout=30.0,
            )
            # Update cookies with any new ones returned in the response
            if response.cookies:
                if hasattr(response.cookies, "get_dict"):
                    self.cookies.update(response.cookies.get_dict())
                else:
                    self.cookies.update(dict(response.cookies))
            _LOGGER.debug(
                "Received response from %s: status_code=%s, content_length=%s",
                url,
                response.status_code,
                len(response.content) if response.content else 0,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            _LOGGER.error("REWE API request failed for %s: %s", url, exc)
            raise RuntimeError(f"REWE API request failed: {exc}") from exc

    def market_search(self, query: str) -> list[dict[str, Any]]:
        """Search for REWE markets using ZIP code, city name, or market name."""
        _LOGGER.debug("Searching for market with query '%s'", query)
        url = "https://mobile-clients-api.rewe.de/api/stationary-markets"
        data = self._request(url, params={"search": query})

        # Return list of found markets
        if isinstance(data, dict):
            # GraphQL structure: data -> marketSearch -> markets
            markets = data.get("data", {}).get("marketSearch", {}).get("markets", [])
            _LOGGER.debug(
                "Market search query '%s' returned %d markets", query, len(markets)
            )
            return markets
        _LOGGER.debug(
            "Market search query '%s' returned empty/invalid response format", query
        )
        return []

    def get_discounts(self, market_id: str) -> dict[str, Any]:
        """Fetch stationary offers (discounts) for the given market ID."""
        _LOGGER.debug("Fetching discounts for market_id: %s", market_id)
        url = f"https://mobile-clients-api.rewe.de/api/stationary-offers/{market_id}"
        data = self._request(url)

        if isinstance(data, dict):
            # GraphQL structure: data -> offers -> current / next
            offers_data = data.get("data", {}).get("offers", {})
            current_week = offers_data.get("current", {})
            categories = current_week.get("categories", [])
            valid_until = current_week.get("untilDate", "")

            next_week = offers_data.get("next", {})
            next_categories = next_week.get("categories", [])
            next_valid_until = next_week.get("untilDate", "")

            # Map to the format returned by the old native library
            parsed_data = {
                "categories": categories,
                "validUntil": valid_until,
                "next_categories": next_categories,
                "next_validUntil": next_valid_until,
            }
            _LOGGER.debug(
                "Discounts parsed successfully for market_id %s: current (%d cats, valid until %s), next (%d cats, valid until %s)",
                market_id,
                len(categories),
                valid_until,
                len(next_categories),
                next_valid_until,
            )
            return parsed_data

        _LOGGER.warning(
            "Discounts request for market_id %s did not return a dictionary", market_id
        )
        return {}

    def get_market_details(self, market_id: str) -> dict[str, Any]:
        """Fetch details (opening hours, address, name) for the given market ID."""
        _LOGGER.debug("Fetching market details for market_id: %s", market_id)
        url = f"https://mobile-clients-api.rewe.de/api/stationary-markets/{market_id}"
        data = self._request(url)

        if isinstance(data, dict):
            return data.get("data", {}).get("market", {})

        _LOGGER.warning(
            "Market details request for market_id %s did not return a dictionary",
            market_id,
        )
        return {}
