# Copyright 2026 Mosoro Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
Mosoro TLS Certificate Generator
=================================

Generates self-signed CA, server, and client certificates for development
and testing of mTLS communication between Mosoro components.

Usage:
    python security/scripts/generate_certs.py

Output:
    certs/ca.crt          - CA certificate
    certs/ca.key          - CA private key (keep secure!)
    certs/server.crt      - Server certificate (for Mosquitto)
    certs/server.key      - Server private key
    certs/gateway.crt     - Gateway client certificate
    certs/gateway.key     - Gateway client private key
    certs/api.crt         - API client certificate
    certs/api.key         - API client private key

For production, use a proper PKI or certificate authority.
"""

import datetime
import os
import sys
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError:
    print("Error: 'cryptography' package is required.")
    print("Install it with: pip install cryptography")
    sys.exit(1)


# Certificate validity period
CA_VALIDITY_DAYS = 3650  # 10 years for CA
CERT_VALIDITY_DAYS = 365  # 1 year for server/client certs
KEY_SIZE = 4096  # RSA key size


def generate_private_key() -> rsa.RSAPrivateKey:
    """Generate an RSA private key."""
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=KEY_SIZE,
    )


def generate_ca_certificate(
    key: rsa.RSAPrivateKey,
) -> x509.Certificate:
    """Generate a self-signed CA certificate."""
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Mosoro Inc."),
            x509.NameAttribute(NameOID.COMMON_NAME, "Mosoro CA"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=CA_VALIDITY_DAYS)
        )
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return cert


def generate_server_certificate(
    ca_key: rsa.RSAPrivateKey,
    ca_cert: x509.Certificate,
    server_key: rsa.RSAPrivateKey,
) -> x509.Certificate:
    """Generate a server certificate signed by the CA."""
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Mosoro Inc."),
            x509.NameAttribute(NameOID.COMMON_NAME, "mosoro-mqtt"),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(server_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=CERT_VALIDITY_DAYS)
        )
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("mosquitto"),
                    x509.DNSName("mosoro-mqtt"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                ]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return cert


def generate_client_certificate(
    ca_key: rsa.RSAPrivateKey,
    ca_cert: x509.Certificate,
    client_key: rsa.RSAPrivateKey,
    common_name: str,
) -> x509.Certificate:
    """Generate a client certificate signed by the CA (for mTLS)."""
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Mosoro Inc."),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ]
    )

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(client_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=CERT_VALIDITY_DAYS)
        )
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                ]
            ),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return cert


def save_key(key: rsa.RSAPrivateKey, path: Path):
    """Save a private key to a PEM file with restricted permissions."""
    path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    os.chmod(path, 0o600)
    print(f"  Key:  {path}")


def save_cert(cert: x509.Certificate, path: Path):
    """Save a certificate to a PEM file."""
    path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    os.chmod(path, 0o644)
    print(f"  Cert: {path}")


def main():
    """Generate all certificates for Mosoro development environment."""
    import ipaddress  # noqa: F811 — imported here to keep top-level clean

    # Make ipaddress available in the module scope for generate_server_certificate
    globals()["ipaddress"] = ipaddress

    # Determine output directory
    project_root = Path(__file__).resolve().parent.parent.parent
    certs_dir = project_root / "certs"
    certs_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Mosoro TLS Certificate Generator")
    print("=" * 60)
    print(f"Output directory: {certs_dir}")
    print()

    # 1. Generate CA
    print("[1/5] Generating CA certificate...")
    ca_key = generate_private_key()
    ca_cert = generate_ca_certificate(ca_key)
    save_key(ca_key, certs_dir / "ca.key")
    save_cert(ca_cert, certs_dir / "ca.crt")
    print()

    # 2. Generate server certificate (for Mosquitto)
    print("[2/5] Generating server certificate (Mosquitto)...")
    server_key = generate_private_key()
    server_cert = generate_server_certificate(ca_key, ca_cert, server_key)
    save_key(server_key, certs_dir / "server.key")
    save_cert(server_cert, certs_dir / "server.crt")
    print()

    # 3. Generate gateway client certificate
    print("[3/5] Generating gateway client certificate...")
    gateway_key = generate_private_key()
    gateway_cert = generate_client_certificate(ca_key, ca_cert, gateway_key, "gateway")
    save_key(gateway_key, certs_dir / "gateway.key")
    save_cert(gateway_cert, certs_dir / "gateway.crt")
    print()

    # 4. Generate API client certificate
    print("[4/5] Generating API client certificate...")
    api_key = generate_private_key()
    api_cert = generate_client_certificate(ca_key, ca_cert, api_key, "api")
    save_key(api_key, certs_dir / "api.key")
    save_cert(api_cert, certs_dir / "api.crt")
    print()

    # 5. Generate example agent client certificates
    print("[5/5] Generating agent client certificates...")
    agent_names = ["agent-locus-001", "agent-stretch-001", "agent-geekplus-001"]
    for agent_name in agent_names:
        agent_key = generate_private_key()
        agent_cert = generate_client_certificate(ca_key, ca_cert, agent_key, agent_name)
        save_key(agent_key, certs_dir / f"{agent_name}.key")
        save_cert(agent_cert, certs_dir / f"{agent_name}.crt")
    print()

    print("=" * 60)
    print("All certificates generated successfully!")
    print()
    print("IMPORTANT:")
    print("  - ca.key is the CA private key. Keep it secure!")
    print("  - For production, use a proper PKI or certificate authority.")
    print("  - Add certs/ to .gitignore to avoid committing secrets.")
    print("=" * 60)


# Fix: import ipaddress at module level for generate_server_certificate
import ipaddress  # noqa: E402

if __name__ == "__main__":
    main()
