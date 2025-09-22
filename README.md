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

## Episode Naming Strategy

The application uses a specific naming convention for organizing Peloton classes:

### Season and Episode Structure
- **Season Number**: The workout duration in minutes (e.g., 20, 30, 45)
- **Episode Number**: Sequential numbering starting from 1 for the oldest video in each season
- **Activity Grouping**: Classes are grouped by activity type (Cycling, Yoga, Strength, etc.)
- **Instructor Organization**: Episodes are organized by instructor within each activity

### Directory Structure
```
/media/peloton/
├── Cycling/
│   ├── Hannah Frankson/
│   │   ├── S20E001 - 2024-01-15 - 20 min Pop Ride/
│   │   ├── S20E002 - 2024-01-16 - 20 min Rock Ride/
│   │   └── S30E001 - 2024-01-15 - 30 min HIIT Ride/
│   └── Sam Yo/
│       ├── S20E001 - 2024-01-15 - 20 min Low Impact/
│       └── S45E001 - 2024-01-15 - 45 min Power Zone/
├── Yoga/
│   └── Aditi Shah/
│       ├── S30E001 - 2024-01-15 - 30 min Flow/
│       └── S45E001 - 2024-01-15 - 45 min Power Flow/
└── Strength/
    └── Andy Speer/
        ├── S10E001 - 2024-01-15 - 10 min Core/
        └── S20E001 - 2024-01-15 - 20 min Upper Body/
```

### Episode Number Determination
The application determines the next episode number by checking two sources:

1. **Filesystem Analysis**: Scans existing downloaded files in `MEDIA_DIR`
   - Parses `S{season}E{episode}` patterns from folder names
   - Tracks the highest episode number per season per activity

2. **Subscriptions Analysis**: Parses the ytdl-sub subscriptions YAML
   - Extracts episode numbers from configured downloads
   - Ensures no overlap with pending downloads

3. **Merged Results**: Combines both sources to determine the next available episode number
   - Takes the maximum episode number from either source
   - Increments by 1 for new episodes

## Development

- **Debug in VS Code**: Press F5 after setting up your `.env` file
- **Run tests**: 
  - All tests: `python -m pytest tests/`
  - Specific module: `python -m pytest tests/io/`
  - With coverage: `python -m pytest tests/ --cov=src/ytdl_sub_config_manager`
  - Use helper scripts: `./scripts/run-tests.sh` or `./scripts/run-tests.ps1`
- **Update version**: `./scripts/update-version.sh 0.2.0`

### Testing

The project includes comprehensive tests organized by module:
- `tests/core/` - Core functionality (models, configuration, logging)
- `tests/io/` - I/O operations (filesystem parsing, subscriptions parsing)
- `pytest.ini` - Pytest configuration with markers and options
- `tests/conftest.py` - Shared fixtures and test setup 
