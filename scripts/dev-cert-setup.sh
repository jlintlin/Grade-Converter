#!/usr/bin/env bash
# Generate local-trusted TLS certificates for frontend/backend using mkcert.
# Run from repo root: scripts/dev-cert-setup.sh

set -euo pipefail

CERT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/certs"
mkdir -p "$CERT_DIR"

if ! command -v mkcert >/dev/null 2>&1; then
  echo "mkcert is required to generate locally trusted certs."
  echo "Install instructions: https://github.com/FiloSottile/mkcert#installation"
  echo "After installing mkcert, re-run: scripts/dev-cert-setup.sh"
  exit 1
fi

echo "Using cert directory: $CERT_DIR"

# Generate a local CA if not present
if [ ! -f "$(mkcert -CAROOT)/rootCA.pem" ]; then
  echo "Creating local CA via mkcert (you may be prompted for admin consent to trust it)..."
  mkcert -install
fi

echo "Generating localhost certificate for frontend/backend..."
mkcert -key-file "$CERT_DIR/server.key" -cert-file "$CERT_DIR/server.crt" localhost 127.0.0.1 ::1

echo "Done. Certificates placed in $CERT_DIR"
echo "Restart services: ./start.sh rebuild"
