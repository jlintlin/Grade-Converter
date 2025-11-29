#!/bin/bash
# Canvas Grade Converter - Start Script
# This script builds and starts all Docker services

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$SCRIPT_DIR/config"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create necessary directories if they don't exist
mkdir -p "$SCRIPT_DIR/data" "$SCRIPT_DIR/uploads" "$SCRIPT_DIR/exports"

# Parse command line arguments
COMMAND="${1:-up}"

case "$COMMAND" in
    "up"|"start")
        print_status "Building and starting Canvas Grade Converter..."
        cd "$CONFIG_DIR" && docker compose up --build -d
        print_status "Services started!"
        echo ""
        echo "  Frontend: https://localhost:5173"
        echo "  Backend:  http://localhost:8000"
        echo "  API Docs: http://localhost:8000/docs"
        echo ""
        ;;
    "down"|"stop")
        print_status "Stopping services..."
        cd "$CONFIG_DIR" && docker compose down
        print_status "Services stopped."
        ;;
    "logs")
        cd "$CONFIG_DIR" && docker compose logs -f
        ;;
    "rebuild")
        print_status "Rebuilding and restarting services..."
        cd "$CONFIG_DIR" && docker compose down
        cd "$CONFIG_DIR" && docker compose up --build -d
        print_status "Services rebuilt and started!"
        ;;
    "test-backend")
        print_status "Running backend tests..."
        cd "$CONFIG_DIR" && docker compose run --rm backend pytest -q
        ;;
    "build-frontend")
        print_status "Building frontend for production..."
        cd "$CONFIG_DIR" && docker compose run --rm frontend npm run build
        ;;
    *)
        echo "Usage: $0 {up|down|logs|rebuild|test-backend|build-frontend}"
        echo ""
        echo "Commands:"
        echo "  up, start     - Build and start all services"
        echo "  down, stop    - Stop all services"
        echo "  logs          - View service logs"
        echo "  rebuild       - Rebuild and restart services"
        echo "  test-backend  - Run backend tests"
        echo "  build-frontend - Build frontend for production"
        exit 1
        ;;
esac
