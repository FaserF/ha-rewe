"""Rewe.de sensor platform."""
from datetime import datetime, timedelta
import logging
import re
import json
from typing import Any, Callable, Dict, Optional
from requests import JSONDecodeError, ConnectionError, ConnectTimeout

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
    ATTR_DISCOUNTS,
    ATTR_DISCOUNT_TITLE,
    ATTR_DISCOUNT_PRICE,
    ATTR_BASE_PRICE,
    ATTR_PICTURE,
    ATTR_VALID_DATE,
    ATTR_CATEGORY,

    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(days=1)

async def async_setup_entry(
    hass: HomeAssistantType, entry: ConfigType, async_add_entities
):
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][entry.entry_id]
    _LOGGER.debug("Sensor async_setup_entry")
    if entry.options:
        config.update(entry.options)
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

        self.market_id = config[CONF_MARKET_ID]
        self.hass = hass
        self.attrs: Dict[str, Any] = {CONF_MARKET_ID: self.market_id}
        self.updated = datetime.now()
        self._name = f"Rewe {self.market_id}"
        self._state = None
        self._available = True
        self._session = cloudscraper.create_scraper(ecdhCurve="secp384r1")

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
        return "mdi:cart-percent"

    @property
    def state(self) -> Optional[str]:
        if self._state is not None:
            return self._state
        else:
            return "Error"

    @property
    def unit_of_measurement(self):
        """Return unit of measurement."""
        return "items"

    @property
    def session(self):
        return self._session

    @property
    def extra_state_attributes(self):
        """Return extra attributes."""
        return self.attrs

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
                    data = await hass.async_add_executor_job(
                        fetch_rewe_discounts, hass, self
                    )

                    # Reformat categories for easier access. ! are highlighted products, and ? are uncategorized ones.
                    # Order of definition here determines printing order later on.
                    #categories = data['categories']
                    #categories_id_mapping = {'!': 'Vorgemerkte Produkte'}
                    #categorized_products = {'!': []}
                    #for n in range(0, len(categories)):
                    #    if 'PAYBACK' in categories[n]['title']:  # ignore payback offers
                    #        continue
                    #    categories[n]['title'] = categories[n]['title'].replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
                    #    categories_id_mapping.update({n: categories[n]['title']})
                    #    categorized_products.update({n: []})
                    #categories_id_mapping.update({'?': 'Unbekannte Kategorie'})
                    #categorized_products.update({'?': []})

                    # Get maximum valid date of offers
                    try:
                        if data['untilDate']:
                            offers_valid_date = time.strftime('%Y-%m-%d', time.localtime(data['untilDate'] / 1000))
                        else:
                            offers_valid_date = None
                    except:
                        offers_valid_date = None

                    # Stores product data in a dict with categories as keys for a sorted printing experience.
                    # Sometimes the data from Rewe is mixed/missing, so that's why we need all those try/excepts.
                    discounts = []
                    n = 0
                    for category in data['categories']:
                        _LOGGER.debug(f"Processing category: '{category['title']}")
                        if 'PAYBACK' in category['title']:  # ignore payback offers
                            n += 1
                            continue
                        for item in category['offers']:
                            #_LOGGER.debug(f"Processing item: '{item}")
                            item['title'] = item['title'].replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
                            #item['subtitle'] = item['subtitle'].replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
                            #item['priceData']['price'] = item['priceData']['price'].replace('\n', ' ').replace('\u2028', ' ').replace('\u000A', ' ').rstrip().lstrip()
                            discounts.append(
                                {
                                    ATTR_DISCOUNT_TITLE: item['title'],
                                    #ATTR_DISCOUNT_PRICE: item['priceData']['price'],
                                    ATTR_DISCOUNT_PRICE: item['priceData'],
                                    #ATTR_BASE_PRICE: item['subtitle']
                                    ATTR_PICTURE: item['images'],
                                    ATTR_CATEGORY: category['title']
                                }
                            )
                        n += 1

                    # Get the amount of offers
                    discounts_count = len(discounts)

                    self.attrs[ATTR_VALID_DATE] = offers_valid_date
                    self.attrs[ATTR_DISCOUNTS] = discounts
                    self.attrs[ATTR_ATTRIBUTION] = f"last updated {datetime.now()} \n{ATTRIBUTION}"
                    self._state = discounts_count
                    self._available = True
            except:
                try:
                    with async_timeout.timeout(30):
                        data = await hass.async_add_executor_job(
                            less_elegant_query, hass, self
                        )

                        try:
                            for filter in data['filters']:
                                if filter['id'] == 'no-price-filter':
                                    data_filtered = filter['categories']
                        except:
                            _LOGGER.exception(f"FAIL: In the returned query, no data was found. The API output seems to have changed and the code needs to be adjusted. Please report it to https://github.com/foo-git/rewe-discounts and not the HA integration developer!")

                        # Stores product data in a dict with categories as keys for a sorted printing experience.
                        # Sometimes the data from Rewe is mixed/missing, so that's why we need all those try/excepts.
                        discounts = []
                        for category in data_filtered:
                            _LOGGER.debug(f"Processing category: '{category}")
                            if 'payback' in category['id']:  # ignore payback offers
                                continue
                            for item in category['offers']:
                                _LOGGER.debug(f"Processing item: '{item}")
                                try:
                                    with async_timeout.timeout(30):
                                        product_result = await hass.async_add_executor_job(
                                            get_product_details, item['id'], self
                                        )
                                        _LOGGER.debug(f"Got item details '{product_result}")
                                        price_in_euro = product_result['pricing']['priceInCent'] / 100

                                        discounts.append(
                                            {
                                                ATTR_DISCOUNT_TITLE: product_result['product']['description'],
                                                ATTR_DISCOUNT_PRICE: price_in_euro,
                                                ATTR_PICTURE: product_result['pictures']['productImages'],
                                                ATTR_CATEGORY: category['id']
                                            }
                                        )
                                        try:
                                            if product_result['validUntil']:
                                                offers_valid_date = time.strftime('%Y-%m-%d', time.localtime(product_result['validUntil'] / 1000))
                                            else:
                                                offers_valid_date = None
                                        except:
                                            offers_valid_date = None
                                except:
                                    _LOGGER.debug(f"Cannot retrieve product details for: {item}.")
                                    offers_valid_date = None
                                    #_LOGGER.exception('{}'.format(url, data['error']))

                        # Get the amount of offers
                        discounts_count = len(discounts)

                        self.attrs[ATTR_VALID_DATE] = offers_valid_date
                        self.attrs[ATTR_DISCOUNTS] = discounts
                        self.attrs[ATTR_ATTRIBUTION] = f"last updated {datetime.now()} \n{ATTRIBUTION}"
                        self._state = discounts_count
                        self._available = True
                except:
                    self._available = False
                    _LOGGER.exception(f"Cannot retrieve discounts for: {self.market_id} - Maybe a typo or the server rejected the request.")
                    #_LOGGER.exception('{}'.format(url, data['error']))

        except:
            self._available = False
            _LOGGER.exception(f"Cannot retrieve data for: '{self.market_id}'")


def fetch_rewe_discounts(hass, self):
    market_id = self.market_id
    url = 'https://mobile-api.rewe.de/api/v3/all-offers?marketCode=' + market_id
    _LOGGER.debug(f"Fetching api URL: '{url}'")
    try:
        data = self._session.get(url).json()
    except (JSONDecodeError, ConnectionError, ConnectTimeout):
        _LOGGER.debug(f'FAIL: Unknown error while fetching discounts from {url}, maybe a typo or the server rejected the request.')

    #_LOGGER.debug(f"Getting Discounts: '{data}")
    try:
        if data:
            return data
        else:
            return None
    except:
        return None

def less_elegant_query(hass, self):
    market_id = self.market_id
    # When the single query approach fails...
    url = 'https://www.rewe.de/api/all-stationary-offers/' + market_id
    _LOGGER.debug(f"Fetching with first api URL failed, trying instead now '{url}'")
    try:
        data = self._session.get(url).json()
    except (JSONDecodeError, ConnectionError, ConnectTimeout):
        _LOGGER.debug(f'FAIL: Unknown error while fetching discounts from {url}, maybe a typo or the server rejected the request.')

    #_LOGGER.debug(f"Getting Discounts: '{data}")
    try:
        if data:
            return data
        else:
            return None
    except:
        return None

# If the less elegant approach is used, we get different API output and need to process each product individually
def get_product_details(product_id, self):
    market_id = self.market_id
    url = 'https://www.rewe.de/api/offer-details/{}?wwIdent={}'.format(product_id, market_id)
    try:
        product_result = self._session.get(url).json()
        time.sleep(0.02)  # without any sleep, we run into 429 errors, 0.02 s works for now
    except JSONDecodeError:  # Maye a timeout/load issue, retrying silently
        _LOGGER.debug('INFO: Error while retrieving, possible timeout issue, continuing in 60 seconds...')
        time.sleep(60)
        product_result = self._session.get(url).json()

    try:
        if product_result:
            return product_result
        else:
            return None
    except:
        return None