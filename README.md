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
   # Run the full scraping workflow
   python -m src scrape --source peloton --activities cycling,yoga --limit 25
   
   # Or validate/repair directory structure only
   python -m src validate --media-dir ./media --dry-run
   
   # View all available commands and options
   python -m src --help
   ```

3. **Run with Docker**:
   ```bash
   ./scripts/docker-run.sh build
   ./scripts/docker-run.sh run
   ```

## Project Structure

- `src/` - Main application code (flattened package structure)
  - `config/` - Configuration management (CLI parsing, config loading)
  - `core/` - Core application logic, logging, and data models
  - `io/` - File and directory operations, episode parsing, strategy loading
  - `webscraper/` - Web scraping with dependency injection (factory, session, strategies)
  - `git_integration/` - GitHub repository management and PR automation
  - `main.py` - Main entry point
- `tests/` - Comprehensive test suite with pytest
- `scripts/` - Helper scripts for development and deployment
- `.vscode/` - VS Code debug configurations
- `docs/` - Documentation and requirements

## Documentation

- [Docker Usage Guide](docs/docker.md) - Complete Docker setup and usage
- [Debug Guide](docs/debug.md) - VS Code debugging setup
- [Requirements](docs/requirements.md) - MVP requirements and specifications

## Features

- **Multi-source configuration**: Environment variables, CLI args, and nested YAML files with precedence
- **Secure credential management**: Uses `.env` files (git-ignored) with masked logging
- **Episode numbering system**: Intelligent season/episode assignment based on duration and sequence
- **Directory validation**: Automated detection and repair of corrupted directory structures
- **Web scraping architecture**: Dependency injection with factory pattern for extensible scrapers
- **Strategy pattern**: Pluggable login, scraping, and parsing strategies via configuration
- **GitHub integration**: Automated repository management with PR creation and optional auto-merge
- **Comprehensive testing**: Test-gated development with **87% coverage** (316 tests)
- **Docker support**: Full containerization with helper scripts
- **VS Code integration**: Debug configurations and tasks
- **CI/CD pipeline**: GitHub Actions with test-gated builds and semantic versioning

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

## GitHub Integration

The application supports automated GitHub workflows for managing subscription files. The GitHub integration is **media-type agnostic** and works with any subscription file format (Peloton, YouTube, Spotify, etc.).

### Configuration

Set the following environment variables or configuration options:

```bash
# Required for GitHub integration
GITHUB_REPO_URL=github.com/username/repository
GITHUB_TOKEN=your_github_personal_access_token

# Optional: Enable auto-merge (defaults to false)
GITHUB_AUTO_MERGE=true
```

Or in `config.yaml`:

```yaml
github:
  repo-url: "github.com/username/repository"
  token: "your_github_personal_access_token"
  auto-merge: false  # Set to true for automatic PR merging
```

### Workflow

When GitHub integration is enabled, the application will:

1. **Clone/Pull Repository**: Automatically clone the repository or pull latest changes
2. **Update Subscriptions**: Use the subscriptions file from the repository
3. **Process Changes**: Run the normal scraping and file management workflow
4. **Create Pull Request**: Commit changes and create a PR with new subscriptions
5. **Optional Auto-Merge**: If enabled, automatically merge the PR

### CLI Usage

```bash
# Run with GitHub integration (works with any media type)
python -m src scrape --github-repo github.com/user/repo --github-token $GITHUB_TOKEN

# Enable auto-merge
python -m src scrape --github-auto-merge

# The subs-file configuration points directly to the subscription file
python -m src scrape --subs-file /path/to/peloton-subscriptions.yaml --github-repo github.com/user/repo
python -m src scrape --subs-file /path/to/youtube-subscriptions.yaml --github-repo github.com/user/repo
```

### Generic Design

The GitHub integration is designed to be **completely media-type agnostic**:

- **Zero media-specific logic**: No Peloton, YouTube, or other platform-specific code
- **Direct file paths**: Use `application.subs-file` to specify the absolute path to the subscription file
- **Universal workflow**: Same pull-edit-push pattern for all media types and subscription formats
- **True extensibility**: Add new media sources without touching any GitHub integration code
- **Smart logging**: Clearly indicates when GitHub integration is disabled and why
- **Robust cleanup**: Handles Windows file locking issues with retry logic and graceful fallback

**Example: Supporting Multiple Media Types**
```bash
# Peloton subscriptions
python -m src scrape --subs-file /path/to/peloton/subscriptions.yaml --github-repo github.com/user/repo

# YouTube subscriptions  
python -m src scrape --subs-file /path/to/youtube/subscriptions.yaml --github-repo github.com/user/repo

# Custom media source
python -m src scrape --subs-file /path/to/custom-source/config.yaml --github-repo github.com/user/repo
```

## Development

- **Debug in VS Code**: Press F5 after setting up your `.env` file
- **Update version**: `./scripts/update-version.sh 0.2.0`

### Testing 🧪

The project maintains **87% test coverage** with **316 comprehensive tests**. Testing is **mandatory** - all code changes must pass tests and maintain coverage.

#### Running Tests

```bash
# Run all tests (recommended before committing)
python -m pytest tests/

# Run with coverage report
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test modules
python -m pytest tests/core/           # Core functionality tests
python -m pytest tests/config/        # Configuration tests  
python -m pytest tests/io/            # I/O and parsing tests
python -m pytest tests/webscraper/    # Web scraping tests
python -m pytest tests/git_integration/ # GitHub integration tests

# Run with coverage enforcement (fails if below 87%)
python -m pytest tests/ --cov=src --cov-fail-under=87

# Use helper scripts (cross-platform)
./scripts/run-tests.sh              # Unix/Linux/macOS
./scripts/run-tests.ps1             # Windows PowerShell
```

#### Test Organization

- **`tests/core/`** - Application logic, logging, models (95%+ coverage)
- **`tests/config/`** - CLI parsing, configuration loading (98%+ coverage)  
- **`tests/io/`** - File operations, episode parsing, strategies (85%+ coverage)
- **`tests/webscraper/`** - Web scraping, session management, factory patterns (95%+ coverage)
- **`tests/git_integration/`** - Generic GitHub operations, PR management, workflows (96%+ coverage, media-agnostic)
- **`pytest.ini`** - Pytest configuration with markers and options
- **`tests/conftest.py`** - Shared fixtures and test setup

#### Coverage Requirements

- **Minimum**: 80% overall coverage (enforced by CI/CD)
- **Current**: 87% coverage achieved
- **High-coverage modules** (maintain these levels):
  - `config.py`: 96% | `cli_config.py`: 99% | `application.py`: 86%
  - `main.py`: 97% | `strategy_loader.py`: 100% | `file_manager.py`: 88%
  - `webscraper/models.py`: 100% | `webscraper/scraper_factory.py`: 100%
  - `git_integration/models.py`: 100% | `git_integration/repository_manager.py`: 93%

#### Testing Best Practices

- **Before committing**: Always run `python -m pytest tests/`
- **New features**: Must include corresponding test coverage
- **Regression prevention**: Check coverage with `--cov-report=term-missing`
- **Test isolation**: All tests use proper mocking and fixtures
- **CI/CD gating**: Tests must pass before Docker builds or merges 
