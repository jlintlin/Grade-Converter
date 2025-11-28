#!/bin/bash
# Generate self-signed SSL certificates for local development
# These certificates are for development use only - do not use in production

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_ROOT/certs"

# Certificate configuration
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
echo "This script generates self-signed certificates for local development."
echo "These certificates will trigger browser warnings - this is expected."
echo ""

# Create certs directory if it doesn't exist
mkdir -p "$CERTS_DIR"

# Generate private key
echo "[1/3] Generating private key..."
openssl genrsa -out "$CERTS_DIR/server.key" $KEY_SIZE 2>/dev/null

# Generate certificate signing request (CSR)
echo "[2/3] Generating certificate signing request..."
openssl req -new -key "$CERTS_DIR/server.key" -out "$CERTS_DIR/server.csr" \
    -subj "/C=$COUNTRY/ST=$STATE/L=$LOCALITY/O=$ORGANIZATION/OU=$ORGANIZATIONAL_UNIT/CN=$COMMON_NAME" \
    2>/dev/null

# Generate self-signed certificate with SAN (Subject Alternative Names)
echo "[3/3] Generating self-signed certificate..."
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

openssl x509 -req -days $DAYS_VALID \
    -in "$CERTS_DIR/server.csr" \
    -signkey "$CERTS_DIR/server.key" \
    -out "$CERTS_DIR/server.crt" \
    -extfile "$CERTS_DIR/openssl.cnf" \
    -extensions v3_req \
    2>/dev/null

# Clean up temporary files
rm -f "$CERTS_DIR/server.csr" "$CERTS_DIR/openssl.cnf"

# Set appropriate permissions
chmod 600 "$CERTS_DIR/server.key"
chmod 644 "$CERTS_DIR/server.crt"

echo ""
echo "=== Certificate Generation Complete ==="
echo ""
echo "Generated files:"
echo "  - $CERTS_DIR/server.key (private key)"
echo "  - $CERTS_DIR/server.crt (certificate)"
echo ""
echo "Certificate valid for: $DAYS_VALID days"
echo "Subject Alternative Names: localhost, backend, frontend, 127.0.0.1, ::1"
echo ""
echo "NOTE: Since this is a self-signed certificate, browsers will show"
echo "      a security warning. You can proceed by accepting the certificate"
echo "      or adding it to your system's trusted certificates."
echo ""

