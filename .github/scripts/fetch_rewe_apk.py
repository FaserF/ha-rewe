"""
Script to fetch the latest REWE APK from APKMirror.
Utilises curl_cffi to bypass Cloudflare protection.
"""

import sys
import re
import urllib.parse
from curl_cffi import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

headers = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://www.apkmirror.com/",
}


def get_latest_apk_page():
    url = "https://www.apkmirror.com/apk/rewe-markt-gmbh/rewe-angebote-coupons/"
    print(f"Fetching APKMirror listing page: {url}")
    r = requests.get(url, headers=headers, impersonate="chrome")
    if r.status_code != 200:
        print(f"Failed to fetch listing page: Status {r.status_code}")
        sys.exit(1)

    # Find the link to the latest version page
    # Example: /apk/rewe-markt-gmbh/rewe-angebote-coupons/rewe-angebote-coupons-3-46-1-release/ or rewe-supermarkt-5-15-2-release/
    matches = re.findall(
        r'href="(/apk/rewe-markt-gmbh/rewe-angebote-coupons/(?:rewe-angebote-coupons|rewe-supermarkt)-[^"]+)"',
        r.text,
    )
    if not matches:
        print("No version links found on listing page.")
        sys.exit(1)

    # First match is usually the latest
    latest_href = matches[0]
    return urllib.parse.urljoin("https://www.apkmirror.com", latest_href)


def get_download_page(version_url):
    print(f"Fetching version page: {version_url}")
    r = requests.get(version_url, headers=headers, impersonate="chrome")
    if r.status_code != 200:
        print(f"Failed to fetch version page: Status {r.status_code}")
        sys.exit(1)

    # Find release variant link or the main download button page
    matches = re.findall(
        r'href="(/apk/rewe-markt-gmbh/rewe-angebote-coupons/[^"]+-apk-download/)"',
        r.text,
    )
    if not matches:
        # Check if there is a variant link
        matches_variant = re.findall(
            r'href="(/apk/rewe-markt-gmbh/rewe-angebote-coupons/(?:rewe-angebote-coupons|rewe-supermarkt)-[^"]+-release/[^"]+)"',
            r.text,
        )
        if matches_variant:
            variant_url = urllib.parse.urljoin(
                "https://www.apkmirror.com", matches_variant[0]
            )
            return get_download_page(variant_url)

        print("No download button page link found.")
        sys.exit(1)

    download_page_href = matches[0]
    return urllib.parse.urljoin("https://www.apkmirror.com", download_page_href)


def get_final_download_url(download_page_url):
    print(f"Fetching download page: {download_page_url}")
    r = requests.get(download_page_url, headers=headers, impersonate="chrome")
    if r.status_code != 200:
        print(f"Failed to fetch download page: Status {r.status_code}")
        sys.exit(1)

    # Check if this page contains the direct download.php?key= link
    # (Sometimes we have to request /download/?key= first, which returns HTML containing the download.php link)
    matches_direct = re.findall(r'href="([^"]*download\.php\?[^"]+)"', r.text)
    if matches_direct:
        # Clean &amp; entities to &
        clean_url = matches_direct[0].replace("&amp;", "&")
        return urllib.parse.urljoin("https://www.apkmirror.com", clean_url)

    # Otherwise look for the intermediate /download/?key= link
    if "download/?" not in download_page_url:
        matches = re.findall(r'href="([^"]*download/\?[^"]+)"', r.text)
        if matches:
            intermediate_url = urllib.parse.urljoin(
                "https://www.apkmirror.com", matches[0]
            )
            return get_final_download_url(intermediate_url)

    # Fallback to key in scripts/attributes
    key_matches = re.findall(r'data-key="([^"]+)"', r.text)
    if key_matches:
        return f"https://www.apkmirror.com/wp-content/themes/APKMirror/download.php?key={key_matches[0]}"

    print("No final download link or data-key found.")
    sys.exit(1)


def download_apk(download_url, output_path):
    print(f"Downloading APK from: {download_url}")
    download_headers = {**headers, "Referer": download_url}
    r = requests.get(
        download_url, headers=download_headers, impersonate="chrome", stream=True
    )
    if r.status_code != 200:
        print(f"Failed to download APK: Status {r.status_code}")
        sys.exit(1)

    with open(output_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"Successfully downloaded APK to {output_path}")


def main():
    output_path = "rewe.apk" if len(sys.argv) < 2 else sys.argv[1]
    try:
        latest_url = get_latest_apk_page()
        download_page = get_download_page(latest_url)
        final_url = get_final_download_url(download_page)
        download_apk(final_url, output_path)
    except Exception as e:
        print(f"Error executing APK Mirror downloader: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
