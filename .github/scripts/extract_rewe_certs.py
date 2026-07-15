"""
Script to extract mTLS certificates from REWE APK.
Extracts PKCS#12, PEM or keystore assets and outputs certs/client.pem and certs/client.key.
"""

import sys
import os
import zipfile
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization

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

    for name in z.namelist():
        if name.endswith(".p12") or name.endswith(".pfx"):
            print(f"Found PKCS12 file: {name}")
            p12_files.append((name, z.read(name)))
        elif (
            "cert" in name.lower()
            or "key" in name.lower()
            or "mtls" in name.lower()
        ):
            if (
                name.endswith(".pem")
                or name.endswith(".key")
                or name.endswith(".crt")
            ):
                print(f"Found potential PEM/CRT file: {name}")
                pem_files.append((name, z.read(name)))

    # Handle PKCS12 files first
    if p12_files:
        for name, data in p12_files:
            # Try to decode with common passwords
            for pw in PKCS12_PASSWORDS:
                try:
                    private_key, certificate, additional_certificates = (
                        pkcs12.load_key_and_certificates(data, pw)
                    )
                    print(f"Successfully decoded {name} using password '{pw.decode()}'")

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
                except Exception:
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

    print(f"Extracting assets from APK: {apk_path}")

    import io
    with zipfile.ZipFile(apk_path, "r") as z:
        # Check if this is an APK Bundle (contains base.apk)
        if "base.apk" in z.namelist():
            print("Detected APKM / Split APK bundle. Opening base.apk...")
            base_data = z.read("base.apk")
            with zipfile.ZipFile(io.BytesIO(base_data)) as base_zip:
                if extract_certs_from_zip(base_zip, out_pem_path, out_key_path):
                    return True
        else:
            if extract_certs_from_zip(z, out_pem_path, out_key_path):
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
