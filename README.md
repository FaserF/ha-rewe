# REWE Discounts (for Home Assistant)

[![GitHub Release](https://img.shields.io/github/release/FaserF/ha-rewe.svg?style=flat-square)](https://github.com/FaserF/ha-rewe/releases)
[![License](https://img.shields.io/github/license/FaserF/ha-rewe.svg?style=flat-square)](LICENSE)
[![hacs](https://img.shields.io/badge/HACS-custom-orange.svg?style=flat-square)](https://hacs.xyz)
[![Add to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=rewe)
[![CI Orchestrator](https://github.com/FaserF/ha-rewe/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-rewe/actions/workflows/ci-orchestrator.yml)

A secure, robust Home Assistant integration that fetches weekly offers, discounts, and REWE Bonus details for your local REWE market directly from the official REWE Mobile API.

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
  - **Offers Preview**: Next week's upcoming deals (automatically populates as soon as REWE publishes them, usually from Saturday onwards).
- **⭐ REWE Bonus Point Tracking**:
  - **REWE Bonus**: Displays the count of items in the current week that yield loyalty points/cashback. Attributes list detailed bonus values and types (e.g. points/cents).
  - **REWE Bonus Preview**: Upcoming deals next week that will yield bonus points.
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

### Manual Installation

1. Download the latest release zip file.
2. Extract the `custom_components/rewe` folder into your Home Assistant's `custom_components` directory.
3. Restart Home Assistant.

## ⚙️ Configuration

Adding a REWE market is done entirely via the UI. **No YAML configuration is required.**

1. Navigate to **Settings > Devices & Services** in Home Assistant.
2. Click **Add Integration** and search for **REWE Discounts**.
3. Enter your ZIP code or city name to search for nearby REWE markets.
4. Select your specific market from the dropdown list.
5. Submit to create the device and entities.

## 🛠️ Options Flow

You can customise the poll interval of the integration at any time:

1. Go to **Settings > Devices & Services**.
2. Find **REWE Discounts** and click **Configure**.
3. Set the **Update Interval** in minutes (default is 180 minutes, minimum is 10 minutes).

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

## 💖 Credits & Acknowledgements

This integration relies on reverse-engineering work and community research from the following projects:

- **[ByteSizedMarius/rewerse-engineering](https://github.com/ByteSizedMarius/rewerse-engineering)**: For mapping out the REWE mobile API and providing Go/Python wrappers.
- **[foo-git/rewe-discounts](https://github.com/foo-git/rewe-discounts)**: For GraphQL endpoint structures and headers.
- **[torbenpfohl/rewe-discounts](https://github.com/torbenpfohl/rewe-discounts)**: For certificate extraction documentation.

## 📄 License

This project is licensed under the Apache 2.0 License. See the [LICENSE](LICENSE) file for details.
