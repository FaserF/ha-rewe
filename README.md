<div align="center">
  <h1>REWE Discounts (for Home Assistant) 🛒</h1>
  <p><strong>A secure, robust Home Assistant integration that fetches weekly offers, discounts, and REWE Bonus details for your local REWE market directly from the official REWE Mobile API.</strong></p>

  [![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://hacs.xyz)
  [![Downloads (Current release)](https://img.shields.io/github/downloads/FaserF/ha-rewe/latest/rewe.zip?label=Downloads%20(Current%20release)&style=for-the-badge)](https://github.com/FaserF/ha-rewe/releases)
  [![GitHub Release](https://img.shields.io/github/v/release/FaserF/ha-rewe?style=for-the-badge)](https://github.com/FaserF/ha-rewe/releases)
  [![License](https://img.shields.io/github/license/FaserF/ha-rewe?style=for-the-badge)](LICENSE)
</div>

---

## 🧭 Quick Links

| | | | |
| :--- | :--- | :--- | :--- |
| [✨ Features](#-features) | [📦 Installation](#-installation) | [⚙️ Configuration](#️-configuration) | [🛠️ Options](#️-options-flow) |
| [🧑‍💻 Development](#-development) | [💖 Credits](#-credits--acknowledgements) | [📄 License](#-license) | |

### Why use this integration?
Instead of scraping public HTML pages (which constantly break) or using generic web frames, this integration connects directly to the official REWE Mobile GraphQL endpoints. Using curl_cffi for client impersonation and secure mTLS certificates bundled with the integration, it fetches structured, high-fidelity offers data in real-time.

It groups all sensors under a single market device and implements advanced lock-serialisation, random jitter delays, and backoffs to keep your setup secure and prevent bans.

## ✨ Features

- **🛒 Detailed Offers Sensors**:
  - **Offers**: Current week's discounted items count, with attributes detailing titles, base prices, active discount prices, categories, and direct links to product images.
  - **Offers Preview**: Next week's upcoming deals.
- **⭐ REWE Bonus Point Tracking**:
  - **REWE Bonus**: Displays the count of items in the current week that yield loyalty points/cashback. Attributes list detailed bonus values and types (e.g. points/cents).
  - **REWE Bonus Preview**: Upcoming deals next week that will yield bonus points.

> [!NOTE]
> **Offers Preview** and **REWE Bonus Preview** show `0` items during the week (Sunday through Friday) and only populate starting on **Saturdays**, because REWE publishes next week's offers and bonus discounts only on Saturdays.

- **🛡️ Rate-Limiting & Anti-Ban Protections**:
  - **First-Fetch Optimisation**: Skips jitter sleep on initial setup so first refresh completes instantly.
  - **Lock Queueing**: A domain-wide lock ensures concurrent updates (e.g., after a reboot) run sequentially.
  - **Random Jitter**: Introduces a 5–30 second delay between requests.
  - **Restart-Resistance**: Saves parsed data to HA storage cache to survive restarts without hitting the API.
  - **Exponential Backoff**: Backs off for up to 24 hours on 403 or 429 errors.
- **⚙️ Device-Based Grouping**:
  - All sensors and button entities are automatically grouped under a main REWE Market device.
  - **Market Visit Button**: The device registry provides a dynamic configuration URL that takes you straight to your specific market's offers page (e.g., `/angebote/zorneding/440421/...`).
- **🎛️ Manual Force Update**:
  - A **Force Update** button entity allows manually triggering an API update on demand (disabled by default to avoid accidental triggers).
- **🔍 Diagnostic Downloads**:
  - Full support for Home Assistant UI Diagnostics. Download complete configurations with API keys, cert paths, and session tokens automatically redacted.

## ❤️ Support This Project

> I maintain this integration in my **free time alongside my regular job** — debugging, building features, and keeping certificates updated.
>
> **This project is and will always remain 100% free.**
>
> Donations are completely voluntary — but they help me stay motivated and dedicate more time to maintaining open-source tools!

<div align="center">

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor%20on-GitHub-%23EA4AAA?style=for-the-badge&logo=github-sponsors&logoColor=white)](https://github.com/sponsors/FaserF)&nbsp;&nbsp;
[![PayPal](https://img.shields.io/badge/Donate%20via-PayPal-%2300457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/FaserF)

</div>

## 📦 Installation

### HACS (Recommended)

This integration is fully compatible with [HACS](https://hacs.xyz/).

1. Open HACS in Home Assistant.
2. Click on the three dots in the top right corner and select **Custom repositories**.
3. Add `FaserF/ha-rewe` with category **Integration**.
4. Search for "REWE Discounts".
5. Install and restart Home Assistant.

[![Open HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=FaserF&repository=ha-rewe&category=integration)

### Manual Installation

1. Download the latest release zip file.
2. Extract the `custom_components/rewe` folder into your Home Assistant's `custom_components` directory.
3. Restart Home Assistant.

## ⚙️ Configuration

1. Navigate to **Settings > Devices & Services** in Home Assistant.
2. Click **Add Integration** and search for **REWE Discounts**.

[![Add Integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=rewe)
3. Enter your ZIP code or city name to search for nearby REWE markets.
4. Select your specific market from the dropdown list.
5. Submit to create the device and entities.

## 🛠️ Options Flow

You can customise the poll interval of the integration at any time:

1. Go to **Settings > Devices & Services**.
2. Find **REWE Discounts** and click **Configure**.
3. Set the **Update Interval** in hours (default is 24 hours, minimum is 1 hour).

## 🃏 Lovelace Cards

The community has built dedicated cards to display REWE discounts beautifully in your dashboard.

### Custom REWE Discounts Card
A dedicated Lovelace card maintained by the community:

[![REWE Discounts Card](https://img.shields.io/badge/Lovelace-REWE%20Discounts%20Card-brightgreen?style=for-the-badge&logo=home-assistant)](https://github.com/schblondie/ha-rewe-discounts-card)

---

## 🧑‍💻 Development

### Ruff Linter
Ensure formatting and import order matches:
```bash
ruff check . --fix
```

### Type Checking
Ensure all files pass strict type checking:
```bash
mypy .
```

## 🛒 Other Supermarket Integrations

If you like this integration, you might also be interested in my other supermarket integrations for Home Assistant:

- [EDEKA Offers](https://github.com/FaserF/ha-edeka)
- [Lidl Offers](https://github.com/FaserF/ha-lidl)
- [Aldi Offers](https://github.com/FaserF/ha-aldi)

## 💖 Credits & Acknowledgements

This integration relies on reverse-engineering work and community research from the following projects:

- **[ByteSizedMarius/rewerse-engineering](https://github.com/ByteSizedMarius/rewerse-engineering)**: For mapping out the REWE mobile API and providing Go/Python wrappers.
- **[foo-git/rewe-discounts](https://github.com/foo-git/rewe-discounts)**: For GraphQL endpoint structures and headers.
- **[torbenpfohl/rewe-discounts](https://github.com/torbenpfohl/rewe-discounts)**: For certificate extraction documentation.

## 📄 License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.
