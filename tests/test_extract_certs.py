"""Test the certificate extraction script."""

import os
import zipfile
import io
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / ".github" / "scripts"))
from extract_rewe_certs import extract_certs_from_zip


from cryptography.hazmat.primitives.hashes import SHA256

def generate_mock_pfx(password: bytes) -> bytes:
    """Generate a dummy PKCS#12 container with self-signed certificate."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "REWE Test Client"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    ).sign(private_key, SHA256())

    return pkcs12.serialize_key_and_certificates(
        b"rewe-client", private_key, cert, None, serialization.BestAvailableEncryption(password)
    )


def test_extract_certs_from_zip_success(tmp_path) -> None:
    """Test successful PFX extraction with the correct password."""
    pfx_data = generate_mock_pfx(b"NC3hDTstMX9waPPV")
    
    # Create mock zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("res/raw/mtls_prod.pfx", pfx_data)
        
    zip_buffer.seek(0)
    
    out_pem = str(tmp_path / "client.pem")
    out_key = str(tmp_path / "client.key")
    
    with zipfile.ZipFile(zip_buffer, "r") as z:
        success = extract_certs_from_zip(z, out_pem, out_key)
        
    assert success is True
    assert os.path.exists(out_pem)
    assert os.path.exists(out_key)


def test_extract_certs_from_zip_wrong_password(tmp_path) -> None:
    """Test extraction failure with a wrong password."""
    pfx_data = generate_mock_pfx(b"highly-secure-unknown-password")
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as z:
        z.writestr("res/raw/mtls_prod.pfx", pfx_data)
        
    zip_buffer.seek(0)
    
    out_pem = str(tmp_path / "client.pem")
    out_key = str(tmp_path / "client.key")
    
    with zipfile.ZipFile(zip_buffer, "r") as z:
        success = extract_certs_from_zip(z, out_pem, out_key)
        
    assert success is False
    assert not os.path.exists(out_pem)
    assert not os.path.exists(out_key)
