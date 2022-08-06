[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
# Rewe.de Homeassistant Discounts Sensor
Gets discounts and highlights from the [rewe.de API](https://shop.rewe.de/mc/api/markets-stationary).

<img src="images/sensor.png" alt="Rewe.de Sensor" width="300px">




This integration provides the following informations with a refresh rate of 30 minutes until now:


Sensors: 

- sensor.marketid: Discount Date

Sensor Attributes: 

- market_id: Your rewe market id
- discounts: Discounts currently valid
- highlights: Highlights from rewe

## Installation
### 1. Using HACS (recommended way)

Open your HACS Settings and add

https://github.com/faserf/ha-rewe

as custom repository URL.

Then install the "rewe discounts" integration.

If you use this method, your component will always update to the latest version.

### 2. Manual
Place a copy of:

[`__init__.py`](custom_components/rewe) at `<config>/custom_components/`  

where `<config>` is your Home Assistant configuration directory.

>__NOTE__: Do not download the file by using the link above directly. Rather, click on it, then on the page that comes up use the `Raw` button.

## Configuration 

Go to Configuration -> Integrations and click on "add integration". Then search for Rewe.

### Getting the rewe market ID

<img src="images/market_id.png" alt="Rewe.de Sensor" width="300px">

### Configuration Variables
- **market_id**: Enter your rewe market id
- **refresh time**: Custom refresh time interval in minutes (doesnt work until now!!!)

## Bug reporting
Open an issue over at [github issues](https://github.com/FaserF/ha-rewe/issues). Please prefer sending over a log with debugging enabled.

To enable debugging enter the following in your configuration.yaml

```yaml
logs:
    custom_components.rewe: debug
```

## Thanks to
This integration uses the great python code from [Foo-Git Rewe-discounts](https://github.com/foo-git/rewe-discounts)