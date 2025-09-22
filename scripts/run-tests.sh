#!/bin/bash
"""Test runner script for ytdl-sub config manager."""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running tests for ytdl-sub config manager${NC}"
echo "=" * 50

# Check if we're in the right directory
if [ ! -f "pytest.ini" ]; then
    echo -e "${RED}Error: pytest.ini not found. Please run from project root.${NC}"
    exit 1
fi

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found. Please install requirements:${NC}"
    echo "pip install -r requirements.txt"
    exit 1
fi

# Run different test suites based on argument
case "${1:-all}" in
    "unit")
        echo -e "${YELLOW}Running unit tests only...${NC}"
        pytest tests/ -m "unit" -v
        ;;
    "integration")
        echo -e "${YELLOW}Running integration tests only...${NC}"
        pytest tests/ -m "integration" -v
        ;;
    "io")
        echo -e "${YELLOW}Running IO tests only...${NC}"
        pytest tests/io/ -v
        ;;
    "core")
        echo -e "${YELLOW}Running core tests only...${NC}"
        pytest tests/core/ -v
        ;;
    "coverage")
        echo -e "${YELLOW}Running tests with coverage...${NC}"
        pytest tests/ --cov=src/ytdl_sub_config_manager --cov-report=html --cov-report=term-missing -v
        echo -e "${GREEN}Coverage report generated in htmlcov/index.html${NC}"
        ;;
    "fast")
        echo -e "${YELLOW}Running fast tests only (excluding slow tests)...${NC}"
        pytest tests/ -m "not slow" -v
        ;;
    "all"|*)
        echo -e "${YELLOW}Running all tests...${NC}"
        pytest tests/ -v
        ;;
esac

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed!${NC}"
fi

exit $exit_code
