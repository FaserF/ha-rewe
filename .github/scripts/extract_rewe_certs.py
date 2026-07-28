"""
Script to extract mTLS certificates from REWE APK.
Extracts PKCS#12, PEM or keystore assets and outputs certs/client.pem and certs/client.key.
"""

import os
import sys
import zipfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

# PKCS12 password usually used in the APK (if standard / hardcoded in the app)
PKCS12_PASSWORDS = [
    b"NC3hDTstMX9waPPV",
    b"",
    b"rewe",
    b"mobile",
    b"prod",
    b"client",
    b"cert",
    b"password",
]


def extract_certs_from_zip(z, out_pem_path, out_key_path):
    p12_files = []
    pem_files = []

    file_list = z.namelist()
    print(f"Total files in APK zip: {len(file_list)}")

    for name in file_list:
        name_lower = name.lower()
        if name_lower.endswith((".p12", ".pfx", ".bks", ".jks", ".keystore")):
            print(f"Found potential certificate/keystore file: {name}")
            p12_files.append((name, z.read(name)))
        elif (
            "cert" in name_lower
            or "key" in name_lower
            or "mtls" in name_lower
            or "rewe" in name_lower
        ):
            if name_lower.endswith((".pem", ".key", ".crt", ".der", ".dat")):
                print(f"Found potential PEM/CRT asset: {name}")
                pem_files.append((name, z.read(name)))

    # Handle PKCS12 files first
    if p12_files:
        for name, data in p12_files:
            # Try to decode with common passwords
            for pw in PKCS12_PASSWORDS:
                try:
                    private_key, certificate, _additional_certificates = (
                        pkcs12.load_key_and_certificates(data, pw)
                    )
                    print(f"Successfully decoded {name}")

                    # Serialize private key
                    pem_key = private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.TraditionalOpenSSL,
                        encryption_algorithm=serialization.NoEncryption(),
                    )

                    # Serialize certificate
                    pem_cert = certificate.public_bytes(
                        encoding=serialization.Encoding.PEM
                    )

                    with open(out_pem_path, "wb") as f:
                        f.write(pem_cert)
                    with open(out_key_path, "wb") as f:
                        f.write(pem_key)

                    print(
                        f"Written certificate to {out_pem_path} and key to {out_key_path}"
                    )
                    return True
                except Exception:  # noqa: BLE001, S112
                    continue

    # If no PKCS12 or decryption failed, look at PEM files
    if pem_files:
        cert_data = b""
        key_data = b""
        for name, data in pem_files:
            if "key" in name.lower():
                key_data = data
            elif (
                "cert" in name.lower() or "crt" in name.lower() or "pem" in name.lower()
            ):
                cert_data = data

        if cert_data and key_data:
            with open(out_pem_path, "wb") as f:
                f.write(cert_data)
            with open(out_key_path, "wb") as f:
                f.write(key_data)
            print("Successfully extracted certificates directly from PEM assets.")
            return True

    return False


def extract_certs_from_apk(apk_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    out_pem_path = os.path.join(out_dir, "client.pem")
    out_key_path = os.path.join(out_dir, "client.key")

    # Clean pre-existing certificates in output folder if they exist
    for p in (out_pem_path, out_key_path):
        if os.path.exists(p):
            try:
                os.remove(p)
                print(f"Removed pre-existing certificate file: {p}")
            except OSError as e:
                print(f"Warning: could not remove {p}: {e}")

    print(f"Extracting assets from APK: {apk_path}")

    import io

    with zipfile.ZipFile(apk_path, "r") as z:
        # 1. Try extracting directly from top-level zip
        if extract_certs_from_zip(z, out_pem_path, out_key_path):
            return True

        # 2. If top-level search failed, check for nested split APKs (XAPK / APKM / APKS)
        apk_entries = [name for name in z.namelist() if name.endswith(".apk")]
        if apk_entries:
            print(f"Detected APK bundle / XAPK containing split APKs: {apk_entries}")
            for apk_entry in apk_entries:
                print(f"Checking nested APK: {apk_entry}...")
                sub_data = z.read(apk_entry)
                with zipfile.ZipFile(io.BytesIO(sub_data)) as sub_zip:
                    if extract_certs_from_zip(sub_zip, out_pem_path, out_key_path):
                        return True

    print("Could not find or decode any certificates from APK.")
    return False


def main():
    if len(sys.argv) < 3:
        print("Usage: extract_rewe_certs.py <path_to_apk> <output_dir>")
        sys.exit(1)

    apk_path = sys.argv[1]
    out_dir = sys.argv[2]

    success = extract_certs_from_apk(apk_path, out_dir)
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
