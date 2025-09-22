# ytdl-sub Config Manager

A modular Peloton scraper for ytdl-sub subscriptions. This application periodically scrapes Peloton classes and automatically updates ytdl-sub configuration files to download new content.

## Quick Start

1. **Setup environment**:
   ```bash
   cp env.example .env
   # Edit .env with your Peloton credentials
   ```

2. **Run locally**:
   ```bash
   python -m src.ytdl_sub_config_manager.cli scrape
   ```

3. **Run with Docker**:
   ```bash
   ./scripts/docker-run.sh build
   ./scripts/docker-run.sh run
   ```

## Project Structure

- `src/ytdl_sub_config_manager/` - Main application code
  - `core/` - Configuration, logging, and data models
  - `cli.py` - Command-line interface
- `scripts/` - Helper scripts for development and deployment
  - `docker-run.sh` - Docker build and run helper
  - `update-version.sh` - Version management script
- `.vscode/` - VS Code debug configurations
- `docs/` - Documentation and requirements

## Documentation

- [Docker Usage Guide](docs/docker.md) - Complete Docker setup and usage
- [Debug Guide](docs/debug.md) - VS Code debugging setup
- [Requirements](docs/requirements.md) - MVP requirements and specifications

## Features

- **Multi-source configuration**: Environment variables, CLI args, and YAML files
- **Secure credential management**: Uses `.env` files (git-ignored)
- **Docker support**: Full containerization with helper scripts
- **VS Code integration**: Debug configurations and tasks
- **Semantic versioning**: Automated version management
- **GitHub Actions**: CI/CD with container registry publishing

## Development

- **Debug in VS Code**: Press F5 after setting up your `.env` file
- **Run tests**: `python -m pytest` (when implemented)
- **Update version**: `./scripts/update-version.sh 0.2.0` 
