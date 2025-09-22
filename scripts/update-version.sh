#!/bin/bash

# Version update script for ytdl-sub Config Manager
# Usage: ./scripts/update-version.sh <new-version>

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if version argument is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Please provide a version number${NC}"
    echo "Usage: $0 <version>"
    echo "Example: $0 0.2.0"
    exit 1
fi

NEW_VERSION="$1"

# Validate version format (basic semver check)
if [[ ! $NEW_VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
    echo -e "${RED}Error: Invalid version format${NC}"
    echo "Please use semantic versioning format: X.Y.Z or X.Y.Z-suffix"
    echo "Examples: 1.0.0, 0.2.1, 1.0.0-beta"
    exit 1
fi

echo -e "${YELLOW}Updating version to: ${NEW_VERSION}${NC}"

# Update package version
echo "Updating src/ytdl_sub_config_manager/__init__.py..."
sed -i.bak "s/__version__ = \".*\"/__version__ = \"${NEW_VERSION}\"/" src/ytdl_sub_config_manager/__init__.py

# Update GitHub workflow
echo "Updating .github/workflows/ytdl-sub-config-manager-build-and-push.yaml..."
sed -i.bak "s/VERSION: \".*\"/VERSION: \"${NEW_VERSION}\"/" .github/workflows/ytdl-sub-config-manager-build-and-push.yaml

# Update Docker documentation
echo "Updating docs/docker.md..."
sed -i.bak "s/ytdl-sub-config-manager:[0-9]\+\.[0-9]\+\.[0-9]\+/ytdl-sub-config-manager:${NEW_VERSION}/g" docs/docker.md

# Update docker-compose.yml
echo "Updating docker-compose.yml..."
sed -i.bak "s/ytdl-sub-config-manager:[0-9]\+\.[0-9]\+\.[0-9]\+/ytdl-sub-config-manager:${NEW_VERSION}/g" docker-compose.yml

# Clean up backup files
rm -f src/ytdl_sub_config_manager/__init__.py.bak
rm -f .github/workflows/ytdl-sub-config-manager-build-and-push.yaml.bak
rm -f docs/docker.md.bak
rm -f docker-compose.yml.bak

echo -e "${GREEN}Version updated successfully to ${NEW_VERSION}${NC}"
echo ""
echo "Files updated:"
echo "  - src/ytdl_sub_config_manager/__init__.py"
echo "  - .github/workflows/ytdl-sub-config-manager-build-and-push.yaml"
echo "  - docs/docker.md"
echo "  - docker-compose.yml"
echo ""
echo "Next steps:"
echo "  1. Review the changes: git diff"
echo "  2. Commit the changes: git add . && git commit -m \"Bump version to ${NEW_VERSION}\""
echo "  3. Create a tag: git tag v${NEW_VERSION}"
echo "  4. Push changes and tag: git push && git push --tags"
