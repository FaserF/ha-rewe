"""REWE Discounts image platform for Loyalty Card QR code."""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Any

from homeassistant import config_entries
from homeassistant.components.image import ImageEntity
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import ATTRIBUTION, DOMAIN
from .coordinator import ReweDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up REWE Loyalty Card QR Code image entity from a config entry."""
    coordinator: ReweDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    if coordinator.card_number:
        async_add_entities(
            [ReweLoyaltyCardQrImage(hass, coordinator)], update_before_add=False
        )


class ReweLoyaltyCardQrImage(CoordinatorEntity[ReweDataUpdateCoordinator], ImageEntity):
    """Represents the REWE Bonus loyalty card QR code image entity."""

    _attr_icon = "mdi:qrcode-scan"
    _attr_has_entity_name = True
    _attr_name = "Loyalty Card QR Code"

    def __init__(
        self, hass: HomeAssistant, coordinator: ReweDataUpdateCoordinator
    ) -> None:
        """Initialize loyalty card QR image entity."""
        CoordinatorEntity.__init__(self, coordinator)
        ImageEntity.__init__(self, hass)

        self._account_key = coordinator.account_key
        self._attr_unique_id = f"rewe_{self._account_key}_loyalty_card_qr"

        # Static internal security token derived from unique_id
        self._attr_access_token = hashlib.sha256(
            self._attr_unique_id.encode()
        ).hexdigest()[:32]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.market_id)},
            name=coordinator.config_entry.title,
            manufacturer="REWE",
            model="Market Offers",
            entry_type=None,
            configuration_url=coordinator.configuration_url,
        )
        self._cached_png: bytes | None = None
        self._cached_id: str | None = None

    @property
    def loyalty_id(self) -> str | None:
        """Return loyalty card ID from coordinator configuration."""
        return self.coordinator.card_number

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for loyalty card."""
        return {
            "loyalty_id": self.loyalty_id,
            ATTR_ATTRIBUTION: ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        """Return True if card_number is set."""
        return bool(self.coordinator.card_number)

    def _generate_qr_png(self, text: str) -> bytes:
        """Generate high-contrast PNG bytes of QR code optimized for cashier scanners."""
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=12,
            border=4,
        )
        qr.add_data(text)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    async def async_image(self) -> bytes | None:
        """Return bytes of loyalty card QR code image."""
        lid = self.loyalty_id
        if not lid:
            return None

        if self._cached_png is None or self._cached_id != lid:
            self._cached_png = await self.hass.async_add_executor_job(
                self._generate_qr_png, lid
            )
            self._cached_id = lid
            self._attr_image_last_updated = dt_util.now()

        return self._cached_png
