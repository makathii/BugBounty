#!/bin/bash
# Run all tests inside the Docker backend container
# Usage: ./run_tests.sh [extra pytest args]

set -e

cd "$(dirname "$0")"

echo "Running all tests..."
echo "===================="

docker compose exec \
    -e DJANGO_SETTINGS_MODULE=config.test_settings \
    backend \
    pytest --create-db -q "$@"

echo ""
echo "===================="
echo "Tests complete!"
