# Scripts Directory

This directory contains helper scripts for development, deployment, and maintenance of the ytdl-sub Config Manager.

## Available Scripts

### `docker-run.sh`
**Purpose**: Docker build and run helper script  
**Usage**: `./scripts/docker-run.sh [build|run|debug|shell]`

**Commands**:
- `build` - Build the Docker image
- `run [args...]` - Run the container (default: scrape)
- `debug [args...]` - Run in debug mode with verbose logging
- `shell` - Open a bash shell in the container

**Features**:
- Automatically checks for `.env` file
- Mounts local directories correctly
- Sets appropriate environment variables
- Provides colored output for better UX

**Examples**:
```bash
# Build the image
./scripts/docker-run.sh build

# Run with default settings
./scripts/docker-run.sh run

# Run with custom arguments
./scripts/docker-run.sh run scrape --activities cycling --limit 10

# Debug mode
./scripts/docker-run.sh debug

# Interactive shell
./scripts/docker-run.sh shell
```

### `update-version.sh`
**Purpose**: Automated version management across all project files  
**Usage**: `./scripts/update-version.sh <new-version>`

**What it updates**:
- `src/__init__.py` - Package version
- `.github/workflows/ytdl-sub-config-manager-build-and-push.yaml` - Workflow version
- `docs/docker.md` - Documentation examples
- `docker-compose.yml` - Image tag references

**Features**:
- Validates semantic version format
- Creates backup files before changes
- Provides next steps guidance
- Supports pre-release versions (e.g., `1.0.0-beta`)

**Examples**:
```bash
# Update to a new patch version
./scripts/update-version.sh 0.1.1

# Update to a new minor version
./scripts/update-version.sh 0.2.0

# Pre-release version
./scripts/update-version.sh 1.0.0-beta
```

**Workflow**:
1. Run the script with new version
2. Review changes: `git diff`
3. Commit: `git add . && git commit -m "Bump version to X.Y.Z"`
4. Tag: `git tag vX.Y.Z`
5. Push: `git push && git push --tags`

## Requirements

### For `docker-run.sh`
- Docker installed and running
- `.env` file present (copy from `env.example`)
- Bash shell (Linux/macOS/WSL)

### For `update-version.sh`
- Bash shell with `sed` command
- Git repository (for tagging workflow)
- Write permissions to project files

## Adding New Scripts

When adding new scripts to this directory:

1. **Make them executable**: `chmod +x scripts/your-script.sh`
2. **Add shebang**: Start with `#!/bin/bash`
3. **Add usage help**: Include `--help` option
4. **Use colors**: Follow existing color scheme
5. **Update this README**: Document the new script
6. **Test thoroughly**: Ensure cross-platform compatibility where possible

## Script Conventions

- **Error handling**: Use `set -e` for strict error handling
- **Color output**: Use consistent color scheme (RED, GREEN, YELLOW, NC)
- **Help text**: Always provide usage examples
- **Validation**: Check prerequisites and inputs
- **Cleanup**: Remove temporary files on exit
