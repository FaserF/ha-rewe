# REWE Discounts for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![CI](https://github.com/FaserF/ha-rewe/actions/workflows/ci-orchestrator.yml/badge.svg)](https://github.com/FaserF/ha-rewe/actions/workflows/ci-orchestrator.yml)

A custom Home Assistant integration that fetches weekly offers (discounts) for a specific REWE market using the official REWE Mobile API via `rewerse`.

## Features

- **JSON API only**: Direct data fetch via the REWE Mobile API (no fragile HTML parsing or scraping).
- **Automated Certificate Updates**: Utilises mTLS client certificates automatically extracted from the official REWE APK via GitHub Actions.
- **Anti-ban / Throttling Protections**: Random jitter delays, sequential rate-limiting lock, exponential backoff on block, and persistent storage restart-resistance.
- **Configurable Update Interval**: Set your own scan frequency (minimum 10 minutes, default 180 minutes).

## Installation

### Via HACS (Recommended)

1. Open HACS in your Home Assistant instance.
2. Click on **Integrations** -> **3 dots in top right** -> **Custom repositories**.
3. Paste the URL of this repository: `https://github.com/FaserF/ha-rewe` and select category **Integration**.
4. Click **Add** and then **Install** the integration.
5. Restart Home Assistant.

## Configuration

1. In Home Assistant, go to **Settings** -> **Devices & Services**.
2. Click **Add Integration** and search for **REWE Discounts**.
3. Enter your numeric **REWE Market ID** (e.g. `440421`). You can find this ID in the URL when searching for your market on [rewe.de](https://www.rewe.de).
4. Enjoy your new weekly offers sensor!
