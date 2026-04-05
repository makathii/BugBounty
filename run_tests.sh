#!/bin/bash
# Run all tests with pytest
# Usage: ./run_tests.sh

cd "$(dirname "$0")/Backend"

echo "Running all tests..."
echo "===================="

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "pytest not found. Installing from requirements.txt..."
    pip install -r requirements.txt
fi

# Run all tests
pytest tests/ -v --tb=short

echo ""
echo "===================="
echo "Tests complete!"
