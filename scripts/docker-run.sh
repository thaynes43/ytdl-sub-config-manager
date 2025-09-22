#!/bin/bash

# Docker run script for ytdl-sub Config Manager
# Usage: ./scripts/docker-run.sh [build|run|debug|shell]

set -e

IMAGE_NAME="ytdl-sub-config-manager"
CONTAINER_NAME="ytdl-sub-config-manager"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [[ ! -f .env ]]; then
    echo -e "${RED}Error: .env file not found!${NC}"
    echo "Please copy env.example to .env and configure your settings:"
    echo "  cp env.example .env"
    exit 1
fi

# Function to build the image
build() {
    echo -e "${GREEN}Building Docker image: ${IMAGE_NAME}${NC}"
    docker build -t ${IMAGE_NAME} .
}

# Function to run the container
run() {
    echo -e "${GREEN}Running ${CONTAINER_NAME}${NC}"
    docker run --rm \
        --name ${CONTAINER_NAME} \
        --env-file .env \
        -v "$(pwd)/media:/media" \
        -v "$(pwd)/subscriptions.yaml:/app/subscriptions.yaml" \
        ${IMAGE_NAME} "$@"
}

# Function to run in debug mode
debug() {
    echo -e "${YELLOW}Running in debug mode${NC}"
    docker run --rm -it \
        --name ${CONTAINER_NAME}-debug \
        --env-file .env \
        -e LOG_LEVEL=DEBUG \
        -e PELOTON_CLASS_LIMIT_PER_ACTIVITY=5 \
        -v "$(pwd)/media:/media" \
        -v "$(pwd)/subscriptions.yaml:/app/subscriptions.yaml" \
        ${IMAGE_NAME} "$@"
}

# Function to open a shell in the container
shell() {
    echo -e "${YELLOW}Opening shell in ${CONTAINER_NAME}${NC}"
    docker run --rm -it \
        --name ${CONTAINER_NAME}-shell \
        --env-file .env \
        -v "$(pwd)/media:/media" \
        -v "$(pwd)/subscriptions.yaml:/app/subscriptions.yaml" \
        --entrypoint /bin/bash \
        ${IMAGE_NAME}
}

# Function to show help
help() {
    echo "Usage: $0 [command] [args...]"
    echo ""
    echo "Commands:"
    echo "  build          Build the Docker image"
    echo "  run [args...]  Run the container (default: scrape)"
    echo "  debug [args...] Run in debug mode with verbose logging"
    echo "  shell          Open a bash shell in the container"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 run"
    echo "  $0 run scrape --activities cycling --limit 10"
    echo "  $0 debug"
    echo "  $0 shell"
}

# Main command handling
case "${1:-help}" in
    build)
        build
        ;;
    run)
        shift
        run "$@"
        ;;
    debug)
        shift
        debug "$@"
        ;;
    shell)
        shell
        ;;
    help|--help|-h)
        help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        help
        exit 1
        ;;
esac
