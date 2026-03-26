#!/bin/bash
# Copyright 2026 Mosoro Inc.
# SPDX-License-Identifier: Apache-2.0
#
# Generate Mosquitto password file for MQTT authentication.
# Uses Docker to run mosquitto_passwd if not installed locally.
#
# Usage:
#   ./security/scripts/generate_passwordfile.sh
#
# Output:
#   docker/mosquitto/passwordfile

set -e

OUTPUT_DIR="$(cd "$(dirname "$0")/../../docker/mosquitto" && pwd)"
OUTPUT_FILE="${OUTPUT_DIR}/passwordfile"

echo "============================================"
echo "Mosoro MQTT Password File Generator"
echo "============================================"
echo "Output: ${OUTPUT_FILE}"
echo ""

# Check if mosquitto_passwd is available locally
if command -v mosquitto_passwd &> /dev/null; then
    echo "Using local mosquitto_passwd..."
    mosquitto_passwd -c "${OUTPUT_FILE}" gateway
    mosquitto_passwd -b "${OUTPUT_FILE}" api mosoro-api-password
    echo ""
    echo "NOTE: Change the 'api' password in production!"
else
    echo "mosquitto_passwd not found locally. Using Docker..."
    echo ""

    # Generate via Docker
    docker run --rm -v "${OUTPUT_DIR}:/output" eclipse-mosquitto:2 sh -c "
        mosquitto_passwd -c /output/passwordfile gateway &&
        mosquitto_passwd -b /output/passwordfile api mosoro-api-password
    "
    echo ""
    echo "NOTE: Change the 'api' password in production!"
fi

echo ""
echo "Password file created at: ${OUTPUT_FILE}"
echo ""
echo "Users created:"
echo "  - gateway (you set the password interactively)"
echo "  - api (default: mosoro-api-password — CHANGE IN PRODUCTION)"
echo "============================================"
