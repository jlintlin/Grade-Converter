#!/bin/bash
# Generate SSL certificates for local development
# Supports two modes:
#   1. mkcert (if installed on host) - creates browser-trusted certificates
#   2. OpenSSL fallback - creates self-signed certificates (browser warning expected)
#
# This script is designed to work in Docker-first environments.
# Run this on the HOST machine before starting Docker containers.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_ROOT/certs"

# Certificate configuration for OpenSSL fallback
DAYS_VALID=365
KEY_SIZE=2048
COUNTRY="US"
STATE="Florida"
LOCALITY="Orlando"
ORGANIZATION="Canvas Grade Converter"
ORGANIZATIONAL_UNIT="Development"
COMMON_NAME="localhost"

echo "=== Canvas Grade Converter - SSL Certificate Generator ==="
echo ""

# Create certs directory if it doesn't exist
mkdir -p "$CERTS_DIR"

# Check if mkcert is available (try common locations)
MKCERT_CMD=""
if command -v mkcert &> /dev/null; then
    MKCERT_CMD="mkcert"
elif [ -x "/opt/homebrew/bin/mkcert" ]; then
    MKCERT_CMD="/opt/homebrew/bin/mkcert"
elif [ -x "/usr/local/bin/mkcert" ]; then
    MKCERT_CMD="/usr/local/bin/mkcert"
fi

if [ -n "$MKCERT_CMD" ]; then
    # === MKCERT MODE: Browser-trusted certificates ===
    echo "✅ mkcert detected: $MKCERT_CMD"
    echo "   Using mkcert to generate browser-trusted certificates."
    echo ""

    echo "[1/2] Installing local Certificate Authority..."
    echo "      (You may be prompted for your password)"
    $MKCERT_CMD -install

    echo ""
    echo "[2/2] Generating certificates..."
    $MKCERT_CMD -key-file "$CERTS_DIR/server.key" \
                -cert-file "$CERTS_DIR/server.crt" \
                localhost 127.0.0.1 ::1 backend frontend

    # Set permissions
    chmod 600 "$CERTS_DIR/server.key"
    chmod 644 "$CERTS_DIR/server.crt"

    echo ""
    echo "=== Certificate Generation Complete (mkcert) ==="
    echo ""
    echo "Generated files:"
    echo "  - $CERTS_DIR/server.key (private key)"
    echo "  - $CERTS_DIR/server.crt (certificate)"
    echo ""
    echo "CA Root location: $($MKCERT_CMD -CAROOT)"
    echo "Domains: localhost, 127.0.0.1, ::1, backend, frontend"
    echo ""
    echo "✅ Your browser will trust these certificates WITHOUT warnings!"
    echo ""
else
    # === OPENSSL MODE: Self-signed certificates (fallback) ===
    echo "ℹ️  mkcert not found. Using OpenSSL to generate self-signed certificates."
    echo "   (Browser will show a security warning - this is expected)"
    echo ""
    echo "   To eliminate browser warnings, install mkcert:"
    echo "     macOS:   brew install mkcert && brew install nss"
    echo "     Linux:   sudo apt install mkcert libnss3-tools"
    echo "     Windows: choco install mkcert"
    echo ""

    echo "[1/3] Generating private key..."
    openssl genrsa -out "$CERTS_DIR/server.key" $KEY_SIZE 2>/dev/null

    echo "[2/3] Creating certificate configuration..."
    cat > "$CERTS_DIR/openssl.cnf" << EOF
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = $COUNTRY
ST = $STATE
L = $LOCALITY
O = $ORGANIZATION
OU = $ORGANIZATIONAL_UNIT
CN = $COMMON_NAME

[v3_req]
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = backend
DNS.3 = frontend
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

    echo "[3/3] Generating self-signed certificate..."
    openssl req -new -x509 -nodes \
        -key "$CERTS_DIR/server.key" \
        -out "$CERTS_DIR/server.crt" \
        -days $DAYS_VALID \
        -config "$CERTS_DIR/openssl.cnf" \
        -extensions v3_req \
        2>/dev/null

    # Clean up config file
    rm -f "$CERTS_DIR/openssl.cnf"

    # Set permissions
    chmod 600 "$CERTS_DIR/server.key"
    chmod 644 "$CERTS_DIR/server.crt"

    echo ""
    echo "=== Certificate Generation Complete (OpenSSL) ==="
    echo ""
    echo "Generated files:"
    echo "  - $CERTS_DIR/server.key (private key)"
    echo "  - $CERTS_DIR/server.crt (self-signed certificate)"
    echo ""
    echo "Certificate valid for: $DAYS_VALID days"
    echo "Domains: localhost, backend, frontend, 127.0.0.1, ::1"
    echo ""
    echo "⚠️  BROWSER WARNING EXPECTED"
    echo "   Since this is a self-signed certificate, your browser will show"
    echo "   a security warning. To proceed:"
    echo "     Chrome: Click 'Advanced' → 'Proceed to localhost (unsafe)'"
    echo "     Firefox: Click 'Advanced' → 'Accept the Risk and Continue'"
    echo "     Safari: Click 'Show Details' → 'visit this website'"
    echo ""
fi

echo "Next steps:"
echo "  1. Start Docker: cd config && docker compose up -d"
echo "  2. Open https://localhost:5173 in your browser"
echo ""

