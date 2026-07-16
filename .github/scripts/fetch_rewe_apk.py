"""
Script to fetch the latest REWE APK from APKPure.
"""

import sys
import os
from curl_cffi import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

def main():
    output_path = "rewe.apk" if len(sys.argv) < 2 else sys.argv[1]
    pkg = "de.rewe.app.mobile"
    url = f"https://d.apkpure.com/b/APK/{pkg}?version=latest"
    print(f"Downloading latest REWE APK from APKPure: {url}")
    try:
        r = requests.get(url, headers=headers, impersonate="chrome", stream=True, allow_redirects=True)
        if r.status_code != 200:
            print(f"Failed to download APK: HTTP Status {r.status_code}")
            sys.exit(1)
        
        with open(output_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print(f"Successfully downloaded APK to {output_path} (size: {os.path.getsize(output_path)} bytes)")
    except Exception as e:
        print(f"Error fetching APK from APKPure: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
