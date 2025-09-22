# Debugging Guide

This document explains how to debug the ytdl-sub Config Manager using VS Code.

## Quick Start

1. **Copy `env.example` to `.env`** and add your real credentials
2. **Press F5** in VS Code to start debugging with the default configuration
3. The debugger will use `debug-config.yaml` and your `.env` file
4. Breakpoints can be set in any Python file

## Setting Up Your Environment

### Create Your .env File
```bash
# Copy the example file
cp env.example .env

# Edit .env with your actual credentials (this file is git-ignored)
```

**Important**: The `.env` file is automatically git-ignored for security. Never commit real credentials to version control.

## Debug Configurations

### 1. "Debug ytdl-sub Config Manager" (Default)
- **Usage**: Press F5 or select from debug dropdown
- **Config**: Uses `debug-config.yaml` file + `.env` file
- **Environment**: Loads all variables from `.env` file
- **Log Level**: DEBUG
- **Best for**: Testing configuration loading and general debugging

### 2. "Debug with Environment Only"
- **Usage**: Select from debug dropdown
- **Config**: Uses only `.env` file (no YAML file)
- **CLI Args**: Includes `--activities cycling,yoga --limit 10`
- **Best for**: Testing environment variable precedence

### 3. "Debug CLI Help"
- **Usage**: Select from debug dropdown
- **Config**: Shows help output
- **Best for**: Testing CLI argument parsing

## Configuration Files

### `debug-config.yaml`
- Main debug configuration file
- Contains safe debug values
- Can be modified for different test scenarios
- **Note**: Environment variables in launch.json will override YAML values

### Environment Variables in Debug
The debug configurations load environment variables from your `.env` file. Example `.env` content:
```
PELOTON_USERNAME=your-actual-username
PELOTON_PASSWORD=your-actual-password
MEDIA_DIR=D:\your\actual\media\path
LOG_LEVEL=DEBUG
RUN_IN_CONTAINER=False
PELOTON_ACTIVITY=cycling,yoga
PELOTON_CLASS_LIMIT_PER_ACTIVITY=5
```

## Debugging Tips

### Setting Breakpoints
- Click in the left margin of any Python file to set breakpoints
- Breakpoints work in all modules: `core/`, `main.py`, etc.
- Use conditional breakpoints for specific scenarios

### Configuration Precedence Testing
1. Set breakpoint in `config.py` at line where config is loaded
2. Modify `debug-config.yaml` to test YAML loading
3. Modify your `.env` file to test environment variable precedence
4. Add CLI arguments in `launch.json` to test CLI precedence

**Precedence Order** (highest to lowest):
1. CLI arguments (in `launch.json` args)
2. Environment variables (from `.env` file)
3. YAML config file (`debug-config.yaml`)
4. Application defaults

### Common Debug Scenarios

#### Test Configuration Loading
```python
# Set breakpoint in ConfigLoader.load_config()
# Step through each configuration source loading
```

#### Test Activity Parsing
```python
# Set breakpoint in ActivityData.parse_activities_from_env()
# Test different activity string formats
```

#### Test CLI Argument Parsing
```python
# Set breakpoint in parse_args()
# Test different CLI argument combinations
```

## VS Code Tasks

Use **Ctrl+Shift+P** → "Tasks: Run Task" to access:

- **Run with Debug Config**: Run without debugger
- **Run Tests**: Execute pytest with coverage
- **Format Code**: Run black formatter
- **Lint Code**: Run flake8 linter
- **Type Check**: Run mypy type checker

## Customizing Debug Configuration

### Modify Arguments
Edit `.vscode/launch.json` → `args` array:
```json
"args": [
    "--config", "your-config.yaml",
    "--log-level", "INFO",
    "scrape",
    "--activities", "cycling",
    "--limit", "5"
]
```

### Modify Environment Variables
Edit your `.env` file (git-ignored):
```
PELOTON_USERNAME=your_username
PELOTON_PASSWORD=your_password
MEDIA_DIR=C:\your\media\path
LOG_LEVEL=DEBUG
```

**Note**: The `.env` file is automatically loaded by all debug configurations.

### Create New Debug Configuration
Add to `.vscode/launch.json` → `configurations` array:
```json
{
    "name": "Your Custom Debug",
    "type": "python",
    "request": "launch",
    "module": "src",
    "args": ["your", "args"],
    "console": "integratedTerminal",
    "cwd": "${workspaceFolder}",
    "env": {
        "PYTHONPATH": "${workspaceFolder}"
    },
    "envFile": "${workspaceFolder}/.env"
}
```

## Troubleshooting

### Module Not Found Error
- Ensure `PYTHONPATH` includes `${workspaceFolder}` in launch.json
- Check that you're in the project root directory

### Configuration Errors
- Verify `debug-config.yaml` syntax is valid YAML
- Check that required fields are present in your `.env` file
- Review environment variable names (case-sensitive)
- Ensure `.env` file exists (copy from `env.example`)
- Check that `.env` file has proper format (no spaces around =)

### Breakpoints Not Hit
- Ensure `"justMyCode": true` in launch.json (set to false to debug libraries)
- Check that the code path is actually executed
- Verify the module is being imported correctly
