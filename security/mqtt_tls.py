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
Mosoro MQTT TLS/mTLS Client Factory
====================================

Provides a factory function to create paho-mqtt clients with proper
TLS 1.3 and mutual TLS (mTLS) configuration for secure communication
between Mosoro components and the Mosquitto broker.

Usage:
    from security.mqtt_tls import create_mqtt_client

    client = create_mqtt_client(
        client_id="mosoro-gateway",
        ca_cert="/certs/ca.crt",
        client_cert="/certs/gateway.crt",
        client_key="/certs/gateway.key",
    )
    client.connect("mosquitto", 8883)
"""

import logging
import os
import ssl
from typing import Optional

import paho.mqtt.client as mqtt

logger = logging.getLogger("mosoro.security.mqtt_tls")


def create_ssl_context(
    ca_cert: str,
    client_cert: Optional[str] = None,
    client_key: Optional[str] = None,
) -> ssl.SSLContext:
    """
    Create an SSL context enforcing TLS 1.3 with optional mTLS.

    Args:
        ca_cert: Path to the CA certificate file.
        client_cert: Path to the client certificate file (for mTLS).
        client_key: Path to the client private key file (for mTLS).

    Returns:
        Configured ssl.SSLContext instance.
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

    # Enforce TLS 1.3 minimum
    context.minimum_version = ssl.TLSVersion.TLSv1_3

    # Load CA certificate for server verification
    context.load_verify_locations(ca_cert)

    # Load client certificate and key for mTLS
    if client_cert and client_key:
        context.load_cert_chain(certfile=client_cert, keyfile=client_key)
        logger.info(f"mTLS enabled with client cert: {client_cert}")
    else:
        logger.info("TLS enabled (server verification only, no client cert)")

    # Security hardening
    context.check_hostname = False  # Mosquitto uses CN for auth, not hostname
    context.verify_mode = ssl.CERT_REQUIRED

    return context


def create_mqtt_client(
    client_id: str,
    ca_cert: Optional[str] = None,
    client_cert: Optional[str] = None,
    client_key: Optional[str] = None,
    use_tls: bool = True,
    broker_host: str = "localhost",
    broker_port: int = 8883,
    username: Optional[str] = None,
    password: Optional[str] = None,
) -> mqtt.Client:
    """
    Create a paho-mqtt client with TLS/mTLS configuration.

    Reads configuration from environment variables if not provided:
        MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_USE_TLS,
        MQTT_CA_CERT, MQTT_CLIENT_CERT, MQTT_CLIENT_KEY,
        MQTT_USERNAME, MQTT_PASSWORD

    Args:
        client_id: Unique MQTT client identifier.
        ca_cert: Path to CA certificate.
        client_cert: Path to client certificate (mTLS).
        client_key: Path to client private key (mTLS).
        use_tls: Whether to enable TLS.
        broker_host: MQTT broker hostname.
        broker_port: MQTT broker port.
        username: MQTT username (for password auth, not needed with mTLS).
        password: MQTT password.

    Returns:
        Configured paho.mqtt.client.Client instance.
    """
    # Read from environment variables as fallback
    broker_host = os.environ.get("MQTT_BROKER_HOST", broker_host)
    broker_port = int(os.environ.get("MQTT_BROKER_PORT", broker_port))
    use_tls = os.environ.get("MQTT_USE_TLS", str(use_tls)).lower() in ("true", "1", "yes")
    ca_cert = ca_cert or os.environ.get("MQTT_CA_CERT", "/run/secrets/mqtt_ca_cert")
    client_cert = client_cert or os.environ.get("MQTT_CLIENT_CERT")
    client_key = client_key or os.environ.get("MQTT_CLIENT_KEY")
    username = username or os.environ.get("MQTT_USERNAME")
    password = password or os.environ.get("MQTT_PASSWORD")

    client = mqtt.Client(client_id=client_id)

    if use_tls:
        try:
            ssl_context = create_ssl_context(ca_cert, client_cert, client_key)
            client.tls_set_context(ssl_context)
            logger.info(
                f"MQTT client '{client_id}' configured with TLS 1.3 "
                f"(broker={broker_host}:{broker_port})"
            )
        except FileNotFoundError as e:
            logger.error(f"TLS certificate file not found: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to configure TLS for MQTT client: {e}")
            raise

    if username:
        client.username_pw_set(username, password)
        logger.info(f"MQTT client '{client_id}' using password authentication")

    # Store connection params for convenience
    client._mosoro_broker_host = broker_host
    client._mosoro_broker_port = broker_port

    return client


def connect_mqtt_client(
    client: mqtt.Client,
    broker_host: Optional[str] = None,
    broker_port: Optional[int] = None,
    keepalive: int = 60,
):
    """
    Connect an MQTT client to the broker.

    Uses stored connection params if host/port not provided.

    Args:
        client: The MQTT client to connect.
        broker_host: Override broker hostname.
        broker_port: Override broker port.
        keepalive: Keepalive interval in seconds.
    """
    host = broker_host or getattr(client, "_mosoro_broker_host", "localhost")
    port = broker_port or getattr(client, "_mosoro_broker_port", 8883)

    logger.info(f"Connecting MQTT client to {host}:{port}...")
    client.connect(host, port, keepalive=keepalive)
