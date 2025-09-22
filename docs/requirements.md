## MVP Requirements: ytdl-sub Config Manager

This document defines the minimum viable product (MVP) to rebuild the Peloton scraper from `docs/old-implementation.py` into a clean, modular, and testable Python application that updates `ytdl-sub` subscription YAMLs. The new implementation must match the functional behavior of the legacy script while improving structure, reliability, and extensibility for future sources.

Reference: `ytdl-sub` repository and configuration format are documented here: [ytdl-sub (GitHub)](https://github.com/jmbannon/ytdl-sub).

### Goals
- Re-implement the Peloton scraping workflow with parity to `docs/old-implementation.py`.
- Restructure into multiple Python modules with clear boundaries.
- Provide a CLI entrypoint to run the full flow.
- Ship a Docker image that runs headless scraping in containers.
- Add unit tests with high coverage of business logic (non-Selenium parts mocked).
- Make the design source-agnostic to enable adding new scrapers later.

## Functional Requirements

- Login and scrape Peloton classes using a headless browser session (Selenium + Chromium in container mode) with credentials from environment variables.
- For each selected activity, navigate the Peloton classes listing page and collect candidate class links. Implement lazy-load pagination by programmatic scrolling a configurable number of times.
- Parse class metadata from listing tiles:
  - classId from the `classId` query param
  - title
  - instructor name
  - activity label
  - duration in minutes (derived from tile text; legacy logic acceptable)
- Deduplicate before output by removing any class IDs that already exist:
  - On disk: scan `MEDIA_DIR` recursively for `.info.json` files and collect `id` fields.
  - In the current subscriptions YAML: inspect values with `download` URLs matching `/classes/player/{id}` and collect IDs.
- Map activity labels to canonical enum values matching legacy behavior, including special handling for Bootcamp variants (Bike/Tread/Row Bootcamp collapse as in the legacy script).
- Determine season and episode numbering per activity:
  - season_number = the duration in minutes (e.g., 20, 30, 45) per legacy behavior
  - episode_number = the next sequential episode index within the season per activity, based on the max found across both disk and subscriptions
- Update the subscriptions YAML file by adding new entries under top-level key `Plex TV Show by Date` using the legacy structure:
  - Duration group key: `= {Activity} ({minutes} min)` (e.g., `= Cycling (20 min)`).
  - Episode title: `{Title} with {Instructor}`; replace any `/` with `-`. If duplicates occur, append ` (n)` suffix.
  - Episode value:
    - `download`: `https://members.onepeloton.com/classes/player/{class_id}`
    - `overrides`:
      - `tv_show_directory`: `/media/peloton/{Activity}/{Instructor}`
      - `season_number`: integer
      - `episode_number`: integer
- Optionally, when `GITHUB_REPO_URL` and `GITHUB_TOKEN` are set, clone/pull a remote repo to a temp working directory, write to the configured `SUBS_FILE` path in that repo, commit on a new timestamped branch, push, and open a PR against `main`.

## Non-Functional Requirements

- Reliability: Replace print statements with structured logging and predictable error handling paths.
- Testability: Business logic must be isolated from I/O and Selenium to enable unit testing without a browser.
- Extensibility: Introduce a source abstraction (interface/protocol) so new scrapers can plug in without changes to core services.
- Configuration via environment variables with sane defaults; no hard-coded secrets.
- Deterministic YAML formatting (stable keys, unicode-safe, wrapped reasonably) matching legacy output semantics.

## Configuration and Environment

- Required
  - `PELOTON_USERNAME`: Peloton account username/email
  - `PELOTON_PASSWORD`: Peloton account password
  - `MEDIA_DIR`: Absolute path to the root directory containing downloaded media

- Conditional
  - `SUBS_FILE`: Path to subscriptions YAML. Default: `/tmp/peloton-scrape-repo/kubernetes/main/apps/downloads/ytdl-sub/peloton/config/subscriptions.yaml`
  - `GITHUB_REPO_URL`: HTTPS URL to the target repo (without protocol in internal usage is acceptable); if set, the workflow clones/pulls/pushes.
  - `GITHUB_TOKEN`: Token for repo access (required if `GITHUB_REPO_URL` is set)

- Optional (with defaults matching legacy behavior)
  - `PELOTON_CLASS_LIMIT_PER_ACTIVITY` (int, default 25)
  - `PELOTON_ACTIVITY` (comma-separated list; default is all Activity enum values except `ALL`)
  - `RUN_IN_CONTAINER` (bool-like string, default `True`)
  - `PELOTON_PAGE_SCROLLS` (int, default 10)

## Proposed Project Structure

Use a package name and layout that keeps core logic separate from I/O:

- `src/`
  - `core/`
    - `config.py`: Load/validate env vars, provide immutable Config object
    - `models.py`: `Activity` enum, `ActivityData`, and related data classes
    - `logging.py`: logger setup helpers
  - `io/`
    - `file_manager.py`: media inventory scanning, subscriptions YAML read/write, ID extraction
  - `services/`
    - `subscriptions.py`: merge logic, dedupe, duplicate-title handling
    - `git_sync.py`: clone/pull, commit, push, PR creation
  - `sources/`
    - `base.py`: scraper/source protocol (interfaces for session + scraping)
    - `peloton/`
      - `session.py`: Selenium session management (headless Chromium in container)
      - `scraper.py`: list page scraping, parsing, result mapping to episodes
  - `main.py`: Main entrypoint to run the end-to-end flow

Notes:
- No business logic in `main.py`—compose services and call into modules.
- No global mutable state; pass `Config` and explicit dependencies.

## Implementation Requirements

- Language/runtime: Python 3.13 (to match base image) with type hints on all public interfaces.
- Dependencies (minimum):
  - `selenium`
  - `PyYAML`
  - `python-dotenv`
  - `GitPython`
  - `PyGithub`
  - `requests`
  - `webdriver-manager` (optional: local use; container can rely on system `chromium` and `chromedriver`)
- Logging: use the standard `logging` module; default to INFO in CLI, DEBUG via env switch.
- Error handling: raise explicit exceptions in core modules; convert to user-friendly messages in CLI.
- YAML I/O: preserve top-level key ordering where possible; width similar to legacy (e.g., 4096) and `allow_unicode=True`.
- Browser: launch headless Chromium with container-safe flags; retry login navigation on transient failures.
- Security: never log secrets; handle tokens only via env.

## Testing Requirements

- Framework: `pytest`.
- Coverage target: ≥85% for core and services; Selenium-backed code covered via mocks.
- Unit tests (examples):
  - Activity parsing from env (valid/invalid/mixed case)
  - Media inventory scanning for `.info.json` IDs
  - Subscriptions YAML parsing/writing, including duplicate key handling and duration grouping
  - Episode number merging across disk+subscriptions using `ActivityData.mergeCollections`
  - Title normalization and duplicate suffixing
  - Git sync (branch naming, commit staging) with filesystem and GitHub clients mocked
- Test layout: `tests/` mirrors module structure; use fixtures and factories for sample YAML and directories.

## CLI Requirements

Provide a single command that executes the Peloton flow end-to-end. Either `argparse`, `click`, or `typer` is acceptable. Example shape:

```bash
python -m ytdl_sub_config_manager.cli scrape \
  --source peloton \
  --limit 25 \
  --activities "cycling,yoga" \
  --subs-file /path/to/subscriptions.yaml
```

Environment variables override defaults; flags override env.

## Docker and CI

- Docker image must:
  - Use `python:3.13-slim`.
  - Install `chromium` and `chromium-driver` (apt), plus `git`.
  - Install Python dependencies via `requirements.txt` or `pyproject.toml`.
  - Set sensible `ENTRYPOINT` to run the CLI (`python -m ytdl_sub_config_manager.cli scrape`).
- The existing Dockerfile and GitHub workflow will be updated to point at the new package layout (no `scripts/peloton-scrape/**` path). CI should build and push `ghcr.io/<owner>/peloton-scraper:latest` and a versioned tag.

## Acceptance Criteria

- Running the CLI locally (with a real Peloton account and test `MEDIA_DIR`) produces the same YAML structure and semantics as the legacy script for the same inputs.
- Running the container with appropriate env vars completes the scrape and writes updates to the configured `SUBS_FILE` path.
- When `GITHUB_REPO_URL` and `GITHUB_TOKEN` are set, a PR is created against `main` containing the updated YAML.
- Unit tests pass locally and in CI, with coverage meeting the target.

## Out of Scope (MVP)

- Implementing additional sources beyond Peloton (the architecture must allow for it).
- Full end-to-end browser tests.
- Rich retry/backoff policies beyond basic transient handling.


