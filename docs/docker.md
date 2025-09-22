# Docker Usage Guide

This document explains how to build and run the ytdl-sub Config Manager using Docker.

## Quick Start

### Using Docker Compose (Recommended)

1. **Create your environment file**:
   ```bash
   cp env.example .env
   # Edit .env with your actual credentials
   ```

2. **Run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

### Using Docker Directly

1. **Build the image**:
   ```bash
   docker build -t ytdl-sub-config-manager .
   ```

2. **Run the container**:
   ```bash
   docker run --rm \
     -e PELOTON_USERNAME="your-username" \
     -e PELOTON_PASSWORD="your-password" \
     -e MEDIA_DIR="/media" \
     -v "/path/to/your/media:/media" \
     -v "/path/to/subscriptions.yaml:/app/subscriptions.yaml" \
     ytdl-sub-config-manager
   ```

### Using Helper Scripts

The project includes convenient helper scripts in the `scripts/` directory:

```bash
# Build and run with helper script
./scripts/docker-run.sh build
./scripts/docker-run.sh run

# Debug mode with verbose logging
./scripts/docker-run.sh debug

# Interactive shell
./scripts/docker-run.sh shell
```

The helper script automatically:
- Checks for `.env` file existence
- Mounts local directories correctly
- Sets appropriate environment variables
- Provides colored output for better UX

## Docker Image Details

### Base Image
- **python:3.13-slim** - Minimal Python 3.13 runtime

### Installed Packages
- **chromium** - Headless browser for scraping
- **chromium-driver** - WebDriver for Selenium
- **git** - For GitHub integration

### Environment Variables
The container supports all the same environment variables as the local installation:

#### Required
- `PELOTON_USERNAME` - Your Peloton account username
- `PELOTON_PASSWORD` - Your Peloton account password  
- `MEDIA_DIR` - Path to media directory (default: `/media`)

#### Optional
- `SUBS_FILE` - Path to subscriptions YAML file
- `GITHUB_REPO_URL` - GitHub repository for PR creation
- `GITHUB_TOKEN` - GitHub personal access token
- `PELOTON_CLASS_LIMIT_PER_ACTIVITY` - Max classes per activity (default: 25)
- `PELOTON_ACTIVITY` - Comma-separated activities (default: all)
- `PELOTON_PAGE_SCROLLS` - Number of page scrolls (default: 10)
- `LOG_LEVEL` - Logging level (default: INFO)
- `LOG_FORMAT` - Log format: standard or json (default: standard)

### Container Defaults
- `RUN_IN_CONTAINER=True` - Automatically set for container mode
- `PYTHONPATH=/app` - Python module path
- `PYTHONUNBUFFERED=1` - Immediate output

## Volume Mounts

### Required Volumes
- **Media Directory**: Mount your local media directory to `/media`
  ```bash
  -v "/path/to/your/media:/media"
  ```

### Optional Volumes
- **Subscriptions File**: Mount your subscriptions YAML file
  ```bash
  -v "/path/to/subscriptions.yaml:/app/subscriptions.yaml"
  ```

- **Config File**: Mount a config file for complex configurations
  ```bash
  -v "/path/to/config.yaml:/app/config.yaml"
  ```

## Docker Compose Configuration

### Basic docker-compose.yml
```yaml
version: '3.8'
services:
  ytdl-sub-config-manager:
    build: .
    environment:
      - PELOTON_USERNAME=${PELOTON_USERNAME}
      - PELOTON_PASSWORD=${PELOTON_PASSWORD}
      - MEDIA_DIR=/media
    volumes:
      - "./media:/media"
      - "./subscriptions.yaml:/app/subscriptions.yaml"
```

### Using .env File
Docker Compose automatically loads `.env` files:
```bash
# .env file
PELOTON_USERNAME=your-username
PELOTON_PASSWORD=your-password
MEDIA_DIR=./media
PELOTON_ACTIVITY=cycling,yoga
```

## GitHub Actions CI/CD

The project includes a GitHub Actions workflow that:
- Builds the Docker image on code changes
- Pushes to GitHub Container Registry (ghcr.io)
- Tags with both `latest` and commit SHA

### Workflow Triggers
- Push to `src/**`, `requirements.txt`, `Dockerfile`
- Manual workflow dispatch

### Image Tags
- `ghcr.io/owner/ytdl-sub-config-manager:latest` - Latest build from main branch
- `ghcr.io/owner/ytdl-sub-config-manager:0.1.0` - Current semantic version
- `ghcr.io/owner/ytdl-sub-config-manager:${{ github.sha }}` - Specific commit SHA

## Running Pre-built Images

### From GitHub Container Registry
```bash
# Pull the latest image
docker pull ghcr.io/owner/ytdl-sub-config-manager:latest

# Or pull a specific version
docker pull ghcr.io/owner/ytdl-sub-config-manager:0.1.0

# Run with environment variables
docker run --rm \
  --env-file .env \
  -v "./media:/media" \
  -v "./subscriptions.yaml:/app/subscriptions.yaml" \
  ghcr.io/owner/ytdl-sub-config-manager:0.1.0
```

## Development & Debugging

### Interactive Container
```bash
# Start container with bash shell
docker run -it --entrypoint /bin/bash ytdl-sub-config-manager

# Or with docker-compose
docker-compose run --entrypoint /bin/bash ytdl-sub-config-manager
```

### Debug Mode
```bash
# Run with debug logging
docker run --rm \
  -e LOG_LEVEL=DEBUG \
  -e PELOTON_CLASS_LIMIT_PER_ACTIVITY=5 \
  --env-file .env \
  -v "./media:/media" \
  ytdl-sub-config-manager
```

### Override Command
```bash
# Run with custom arguments
docker run --rm \
  --env-file .env \
  -v "./media:/media" \
  ytdl-sub-config-manager \
  scrape --activities cycling --limit 10
```

## Troubleshooting

### Common Issues

#### Permission Errors
```bash
# Fix file permissions for mounted volumes
sudo chown -R $(id -u):$(id -g) ./media
```

#### Browser Issues
The container uses headless Chromium. If you encounter browser-related errors:
- Ensure the container has enough memory (>1GB recommended)
- Check that no display is required (headless mode is automatic)

#### Network Issues
```bash
# Run with host networking for debugging
docker run --network host ytdl-sub-config-manager
```

### Logs and Debugging
```bash
# View container logs
docker-compose logs -f

# Run with verbose logging
docker-compose run -e LOG_LEVEL=DEBUG ytdl-sub-config-manager
```

### Container Resource Limits
```yaml
# docker-compose.yml
services:
  ytdl-sub-config-manager:
    # ... other config ...
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

## Security Considerations

### Secrets Management
- Never include credentials in Dockerfiles or images
- Use environment variables or mounted secret files
- Consider using Docker secrets in production

### Example with Docker Secrets
```yaml
# docker-compose.yml
version: '3.8'
services:
  ytdl-sub-config-manager:
    build: .
    secrets:
      - peloton_username
      - peloton_password
    environment:
      - PELOTON_USERNAME_FILE=/run/secrets/peloton_username
      - PELOTON_PASSWORD_FILE=/run/secrets/peloton_password

secrets:
  peloton_username:
    file: ./secrets/username.txt
  peloton_password:
    file: ./secrets/password.txt
```
