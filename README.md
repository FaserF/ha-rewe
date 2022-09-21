[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
# Rewe.de Homeassistant Discounts Sensor
Gets discounts and highlights from the [rewe.de API](https://shop.rewe.de/mc/api/markets-stationary).

<img src="images/sensor.png" alt="Rewe.de Sensor" width="300px">




This integration provides the following informations until now:


Sensors:

- sensor.marketid: Valid until Discount Date

Sensor Attributes:

- market_id: Your rewe market id
- discounts: Discounts currently valid
    - attribute product name
    - attribuite discount price
    - attribute picture link

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
1. Go to the [REWE Marktsuche](https://www.rewe.de/marktsuche)
2. Enter your city or PLZ and choose your desired REWE
3. Select "Marktinfos"
4. Copy the marked id from the URL

<img src="images/market_id.png" alt="Rewe.de Sensor" width="300px">

### Configuration Variables
- **market_id**: Enter your rewe market id
- **update interval**: Custom refresh time interval in minutes (doesnt work until now!!!)

## Bug reporting
Open an issue over at [github issues](https://github.com/FaserF/ha-rewe/issues). Please prefer sending over a log with debugging enabled.

To enable debugging enter the following in your configuration.yaml

```yaml
logger:
    logs:
        custom_components.rewe: debug
```

## Thanks to
This integration uses the great python code from [Foo-Git Rewe-discounts](https://github.com/foo-git/rewe-discounts)