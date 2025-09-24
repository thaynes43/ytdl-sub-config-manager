"""Logging configuration for ytdl-sub config manager."""

import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def _generate_timestamped_filename(log_file: str) -> str:
    """Generate a timestamped log filename.
    
    Args:
        log_file: Original log file path
        
    Returns:
        Timestamped log file path with format: {name}_{YYYYMMDD_HHMMSS}.{ext}
    """
    log_path = Path(log_file)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Split filename and extension
    stem = log_path.stem
    suffix = log_path.suffix
    
    # Create timestamped filename
    timestamped_name = f"{stem}_{timestamp}{suffix}"
    timestamped_path = log_path.parent / timestamped_name
    
    return str(timestamped_path)


def setup_logging(level: str = "INFO", format_type: str = "standard", 
                  log_file: Optional[str] = None, max_file_size_mb: int = 100, 
                  backup_count: int = 10) -> logging.Logger:
    """Set up structured logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type ("standard" or "json")
        log_file: Optional path to log file. If provided, enables file logging with rotation
        max_file_size_mb: Maximum size of each log file in MB before rotation (default: 100)
        backup_count: Number of backup log files to keep (default: 10)
    
    Returns:
        Configured logger instance
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    if format_type == "json":
        # For structured logging in production/containers
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        # Standard format for development
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if log_file is specified
    if log_file:
        try:
            # Ensure log directory exists
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Generate timestamped filename
            timestamped_log_file = _generate_timestamped_filename(log_file)
            
            # Create rotating file handler with timestamped filename
            max_bytes = max_file_size_mb * 1024 * 1024  # Convert MB to bytes
            file_handler = logging.handlers.RotatingFileHandler(
                filename=timestamped_log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setLevel(numeric_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            # Log the file logging setup
            temp_logger = logging.getLogger("ytdl_sub_config_manager.logging")
            temp_logger.info(f"File logging enabled: {timestamped_log_file} (max: {max_file_size_mb}MB, backups: {backup_count})")
            
        except Exception as e:
            # If file logging setup fails, log to console and continue
            temp_logger = logging.getLogger("ytdl_sub_config_manager.logging")
            temp_logger.warning(f"Failed to setup file logging to {log_file}: {e}")
    
    # Get application logger
    logger = logging.getLogger("ytdl_sub_config_manager")
    
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance for a specific module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    if name:
        return logging.getLogger(f"ytdl_sub_config_manager.{name}")
    return logging.getLogger("ytdl_sub_config_manager")
