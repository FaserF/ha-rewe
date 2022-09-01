"""Rewe.de sensor platform."""
from datetime import datetime, timedelta
import logging
import re
import json
from typing import Any, Callable, Dict, Optional

import async_timeout
import sys
import argparse
import time
import traceback
import cloudscraper

from homeassistant import config_entries, core
#rom homeassistant.helpers import aiohttp_client
from homeassistant.components.sensor import PLATFORM_SCHEMA
from homeassistant.const import ATTR_ATTRIBUTION
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.typing import (
    ConfigType,
    HomeAssistantType,
)
import voluptuous as vol

from .const import (
    ATTRIBUTION,
    CONF_MARKET_ID,
    CONF_SCAN_INTERVAL,
    ATTR_DISCOUNTS,

    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigType, async_add_entities
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Sensor async_setup_entry")
    if entry.options:
        config.update(entry.options)
    sensors = ReweSensor(config, hass)
    async_add_entities(sensors, update_before_add=True)
    async_add_entities(
        [
            ReweSensor(config, hass)
        ],
        update_before_add=True
    )

class ReweSensor(Entity):
    """Collects and represents rewe discounts based on given market id"""

    def __init__(self, config, hass: HomeAssistantType):
        super().__init__()

        self.update_interval=timedelta(minutes=config[CONF_SCAN_INTERVAL]),
        self.market_id = config[CONF_MARKET_ID]
        self.hass = hass
        self.attrs: Dict[str, Any] = {CONF_MARKET_ID: self.market_id}
        self.updated = datetime.now()
        self._name = f"Rewe {self.market_id}"
        self._state = None
        self._available = True
        self._session = cloudscraper.create_scraper()

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        #return self._name
        return f"Rewe-{self.market_id}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def icon(self) -> str:
        return "mdi:basket-unfill"

    @property
    def state(self) -> Optional[str]:
        if self._state is not None:
            return self._state
        else:
            return "Error"

    @property
    def unit_of_measurement(self):
        """Return unit of measurement."""
        return "date"

    @property
    def session(self):
        return self._session

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        return self.attrs

    async def async_wait_session(self, hass):
        url = 'https://mobile-api.rewe.de/api/v3/all-offers?marketCode=' + market_id
        data = await hass.async_add_executor_job(self._session.get(url).json())
        _LOGGER.debug(f"Fetching URL: '{url}'")
        _LOGGER.debug(f"Getting Discounts: '{response}")

        # Reformat categories for easier access. ! are highlighted products, and ? are uncategorized ones.
        # Order of definition here determines printing order later on.
        categories = data['categories']
        categories_id_mapping = {'!': 'Vorgemerkte Produkte'}
        categorized_products = {'!': []}
        for n in range(0, len(categories)):
            if 'PAYBACK' in categories[n]['title']:  # ignore payback offers
                continue
            categories_id_mapping.update({n: categories[n]['title']})
            categorized_products.update({n: []})
        categories_id_mapping.update({'?': 'Unbekannte Kategorie'})
        categorized_products.update({'?': []})

        # Get maximum valid date of offers
        offers_valid_date = time.strftime('%Y-%m-%d', time.localtime(data['untilDate'] / 1000))

        # Stores product data in a dict with categories as keys for a sorted printing experience.
        # Sometimes the data from Rewe is mixed/missing, so that's why we need all those try/excepts.
        n = 0
        for category in data['categories']:
            if 'PAYBACK' in category['title']:  # ignore payback offers
                n += 1
                continue
            for item in category['offers']:
                NewProduct = Product()
                try:
                    NewProduct.name = item['title']
                    NewProduct.price = item['priceData']['price']
                    NewProduct.base_price = item['subtitle']
                except KeyError:  # sometimes an item is blank or does not contain price information, skip it
                    continue
                try:
                    NewProduct.category = n
                except KeyError:  # if category not defined in _meta, assign to unknown category
                    NewProduct.category = '?'

                # Move product into the respective category list ...
                try:
                    categorized_products[n].append(NewProduct)
                except KeyError:
                    categorized_products['?'].append(NewProduct)
                # ... but highlighted products are the only ones in two categories
                if any(x in NewProduct.name for x in product_highlights):
                    categorized_products['!'].append(NewProduct)
            n += 1

            #name = name.replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
            #price = price.replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
            #discount = discount.replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
            #discount_valid = discount_valid.replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
            #base_price = base_price.replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
            category = category.replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
            #currency = currency.replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
            #description = description.replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()

            self.attrs[ATTR_DISCOUNTS] = categorized_products
            self.attrs[ATTR_ATTRIBUTION] = f"last updated {datetime.now()} \n{ATTRIBUTION}"
            self._state = offers_valid_date
            self._available = True

    async def async_update(self):

        try:
            market_id = self.market_id
            hass = self.hass

            # Below taken from https://github.com/foo-git/rewe-discounts/blob/master/rewe_discounts/rewe_discounts.py and modified to work as a HA Integration:
            # Here we differentiate between mode "print market IDs" and mode "print offers of selected market"
            try:
                assert int(market_id)
                assert len(market_id) >= 6
                assert len(market_id) <= 7
            except (ValueError, AssertionError):
                self._available = False
                _LOGGER.exception(f"Wrong market ID. Please provide a 6 or 7 digit market ID instead of: {self.market_id}")

            # Craft query and load JSON stuff.
            try:
                with async_timeout.timeout(30):
                    response = self.async_wait_session(hass)
            except:
                self._available = False
                _LOGGER.exception(f"Cannot retrieve discounts for: {self.market_id} - Maybe a typo or the server rejected the request.")

        except:
            self._available = False
            _LOGGER.exception(f"Cannot retrieve data for: '{self.market_id}'")

