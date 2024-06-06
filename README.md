[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

# CURRENTLY NOT WORKING ANYMORE, SINCE API HAS BEEN TAKEN DOWN! SEE https://github.com/FaserF/ha-rewe/issues/22

# Rewe.de Homeassistant Discounts Sensor
Gets discounts and highlights from the [rewe.de API](https://shop.rewe.de/mc/api/markets-stationary).

<img src="images/sensor.png" alt="Rewe.de Sensor" width="300px">




This integration provides the following informations with a refresh interval of 24 hours until now:


Sensors:

- sensor.marketid: Amount of currently valid offers

Sensor Attributes:

- market_id: Your rewe market id
- valid until: Valid until Discount Date
- discounts: Discounts currently valid
    - attribute product name
    - attribuite discount price
    - attribute picture link

## Installation
### 1. Using HACS (recommended way)

This integration is a official HACS Integration.

Open HACS then install the "Rewe" integration.

If you use this method, your component will always update to the latest version.

### 2. Manual

- Download the latest zip release from [here](https://github.com/FaserF/ha-rewe/releases/latest)
- Extract the zip file
- Copy the folder "rewe" from within custom_components with all of its components to `<config>/custom_components/`

where `<config>` is your Home Assistant configuration directory.

>__NOTE__: Do not download the file by using the link above directly, the status in the "master" branch can be in development and therefore is maybe not working.

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

### Lovelace cards
## Sample Lovelace card from KrizzeOne
Provided by [KrizzeOne](https://github.com/FaserF/ha-rewe/issues/2#issuecomment-1360129338):

<img src="https://user-images.githubusercontent.com/65257000/208757904-665cd0eb-4dd9-4d03-b40a-6cf027d38c86.png" width="400px">

```yaml
# **Süßes und Salziges**
|            |        |       |
| :------------: |:------------- | -----:|
 {%- set product_list_loop =  state_attr('sensor.rewe_440421', 'discounts') -%}

{%- for product in product_list_loop -%} {% if 'Süßes & Salziges' in product.category and product.product != '' %}
| <img src="{{product.picture_link[0] }}" width="50" height="50"/> | {{product.product }}
| ![badge](https://badgen.net/badge/{{ product.price | urlencode }}/€)
|  {%- endif -%}
{%- endfor -%}
```
_Downsides / Considerations:_

- It takes up to 4sec to load the content if you choose multiple product categories
- Price tags are build via https://badgen.net and most of the time you have to reload your lovelace page to get all badges
- Product images aren't square all the time. Sometimes they look a bit distorted
- By using table layout as I do, Lovelace cards looks different if you have short/long product names. This drives me crazy and I hope I will have a more robust solution in the future.

## Sample Lovelace card from schblondie
Provided by [schblondie](https://github.com/schblondie/ha-rewe-discounts-card):

<img src="https://private-user-images.githubusercontent.com/80481720/314297813-5c9525a0-74b0-4e38-96e7-264ba4d619d0.png?jwt=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJnaXRodWIuY29tIiwiYXVkIjoicmF3LmdpdGh1YnVzZXJjb250ZW50LmNvbSIsImtleSI6ImtleTUiLCJleHAiOjE3MTE1MzIxOTgsIm5iZiI6MTcxMTUzMTg5OCwicGF0aCI6Ii84MDQ4MTcyMC8zMTQyOTc4MTMtNWM5NTI1YTAtNzRiMC00ZTM4LTk2ZTctMjY0YmE0ZDYxOWQwLnBuZz9YLUFtei1BbGdvcml0aG09QVdTNC1ITUFDLVNIQTI1NiZYLUFtei1DcmVkZW50aWFsPUFLSUFWQ09EWUxTQTUzUFFLNFpBJTJGMjAyNDAzMjclMkZ1cy1lYXN0LTElMkZzMyUyRmF3czRfcmVxdWVzdCZYLUFtei1EYXRlPTIwMjQwMzI3VDA5MzEzOFomWC1BbXotRXhwaXJlcz0zMDAmWC1BbXotU2lnbmF0dXJlPTJmOWY3MzkwYzA5NWVmYzUyODBjNzllM2IzOGIxMTM4Mzk4NzJjMDM4ZDgxNWUyZTFhMzNjNDJiMjExZTA2Y2UmWC1BbXotU2lnbmVkSGVhZGVycz1ob3N0JmFjdG9yX2lkPTAma2V5X2lkPTAmcmVwb19pZD0wIn0.uJvAQ7_wGWO1Jri6N2Mt4XJaVn5ZQhJsWqQJVkINIkk" width="400px">

### Automations in HA
A full automation example for HA would be:

```yaml
message: >
    Neues Angebot im Rewe Prospekt für
    {%- set product_list_loop =  state_attr('sensor.rewe_440421', 'discounts') -%}
    {%- for product in product_list_loop -%}
    {% if 'Spezi' in product.product or 'Käse' in product.product or 'Nutella' in product.product %}

    {{product.price.price }} € - {{product.product }}

    {{ product.picture_link[0] }}
    {%- endif -%}
    {%- endfor -%}
```

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
