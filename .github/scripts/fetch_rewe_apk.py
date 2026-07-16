"""
Script to fetch the latest REWE APK from APKPure.
"""

import sys
import os
from curl_cffi import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def main():
    output_path = "rewe.apk" if len(sys.argv) < 2 else sys.argv[1]
    pkg = "de.rewe.app.mobile"
    
    urls = [
        f"https://d.apkpure.net/b/APK/{pkg}?version=latest",
        f"https://d.apkpure.com/b/APK/{pkg}?version=latest"
    ]
    
    last_error = None
    success = False
    
    for url in urls:
        print(f"Downloading latest REWE APK: {url}")
        try:
            r = requests.get(
                url,
                headers=headers,
                impersonate="chrome",
                stream=True,
                allow_redirects=True,
            )
            if r.status_code == 200:
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(
                    f"Successfully downloaded APK to {output_path} (size: {os.path.getsize(output_path)} bytes)"
                )
                success = True
                break
            else:
                print(f"Failed to download from {url}: HTTP Status {r.status_code}")
                last_error = f"HTTP Status {r.status_code}"
        except Exception as e:
            print(f"Error fetching from {url}: {e}")
            last_error = e

    if not success:
        print(f"Error executing APK downloader: All mirrors failed. Last error: {last_error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
