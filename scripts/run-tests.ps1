# PowerShell test runner script for ytdl-sub config manager
param(
    [string]$TestType = "all"
)

# Colors for output (PowerShell)
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"

Write-Host "Running tests for ytdl-sub config manager" -ForegroundColor $Yellow
Write-Host ("=" * 50)

# Check if we're in the right directory
if (-not (Test-Path "pytest.ini")) {
    Write-Host "Error: pytest.ini not found. Please run from project root." -ForegroundColor $Red
    exit 1
}

# Check if pytest is available
try {
    pytest --version | Out-Null
}
catch {
    Write-Host "Error: pytest not found. Please install requirements:" -ForegroundColor $Red
    Write-Host "pip install -r requirements.txt"
    exit 1
}

# Run different test suites based on argument
switch ($TestType) {
    "unit" {
        Write-Host "Running unit tests only..." -ForegroundColor $Yellow
        pytest tests/ -m "unit" -v
    }
    "integration" {
        Write-Host "Running integration tests only..." -ForegroundColor $Yellow
        pytest tests/ -m "integration" -v
    }
    "io" {
        Write-Host "Running IO tests only..." -ForegroundColor $Yellow
        pytest tests/io/ -v
    }
    "core" {
        Write-Host "Running core tests only..." -ForegroundColor $Yellow
        pytest tests/core/ -v
    }
    "coverage" {
        Write-Host "Running tests with coverage..." -ForegroundColor $Yellow
        pytest tests/ --cov=src/ytdl_sub_config_manager --cov-report=html --cov-report=term-missing -v
        Write-Host "Coverage report generated in htmlcov/index.html" -ForegroundColor $Green
    }
    "fast" {
        Write-Host "Running fast tests only (excluding slow tests)..." -ForegroundColor $Yellow
        pytest tests/ -m "not slow" -v
    }
    default {
        Write-Host "Running all tests..." -ForegroundColor $Yellow
        pytest tests/ -v
    }
}

$exit_code = $LASTEXITCODE

if ($exit_code -eq 0) {
    Write-Host "✅ All tests passed!" -ForegroundColor $Green
}
else {
    Write-Host "❌ Some tests failed!" -ForegroundColor $Red
}

exit $exit_code
