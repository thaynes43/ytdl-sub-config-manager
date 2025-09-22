"""Tests for logging configuration."""

import logging
import pytest
from unittest.mock import patch

from src.core.logging import setup_logging, get_logger


class TestLogging:
    """Test logging configuration functions."""

    def test_setup_logging_standard_format(self):
        """Test setup_logging with standard format."""
        logger = setup_logging(level="DEBUG", format_type="standard")
        
        assert logger.name == "ytdl_sub_config_manager"
        assert logging.getLogger().level == logging.DEBUG
        
        # Check that handlers were set up
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        
        # Check formatter
        handler = root_logger.handlers[0]
        formatter = handler.formatter
        assert "%(asctime)s - %(name)s - %(levelname)s - %(message)s" in formatter._fmt

    def test_setup_logging_json_format(self):
        """Test setup_logging with JSON format."""
        logger = setup_logging(level="INFO", format_type="json")
        
        assert logger.name == "ytdl_sub_config_manager"
        
        # Check that handlers were set up
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        
        # Check JSON formatter
        handler = root_logger.handlers[0]
        formatter = handler.formatter
        assert '"timestamp"' in formatter._fmt
        assert '"level"' in formatter._fmt
        assert '"logger"' in formatter._fmt
        assert '"message"' in formatter._fmt

    def test_setup_logging_different_levels(self):
        """Test setup_logging with different log levels."""
        levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in levels:
            logger = setup_logging(level=level, format_type="standard")
            expected_numeric_level = getattr(logging, level)
            assert logging.getLogger().level == expected_numeric_level

    def test_setup_logging_invalid_level(self):
        """Test setup_logging with invalid log level falls back to INFO."""
        logger = setup_logging(level="INVALID", format_type="standard")
        
        # Should fall back to INFO level
        assert logging.getLogger().level == logging.INFO

    def test_setup_logging_removes_existing_handlers(self):
        """Test that setup_logging removes existing handlers."""
        # Add a dummy handler
        root_logger = logging.getLogger()
        dummy_handler = logging.StreamHandler()
        root_logger.addHandler(dummy_handler)
        initial_handler_count = len(root_logger.handlers)
        
        # Setup logging should remove existing handlers and add new one
        setup_logging()
        
        # Should have exactly one handler (the new one)
        assert len(root_logger.handlers) == 1
        assert dummy_handler not in root_logger.handlers

    def test_get_logger_with_name(self):
        """Test get_logger with a specific name."""
        logger = get_logger("test.module")
        
        assert logger.name == "ytdl_sub_config_manager.test.module"

    def test_get_logger_without_name(self):
        """Test get_logger without a name."""
        logger = get_logger(None)
        
        assert logger.name == "ytdl_sub_config_manager"

    def test_get_logger_with_empty_string(self):
        """Test get_logger with empty string."""
        logger = get_logger("")
        
        # Empty string is falsy, so should return base logger
        assert logger.name == "ytdl_sub_config_manager"

    def test_setup_logging_console_handler_configuration(self):
        """Test that console handler is properly configured."""
        setup_logging(level="WARNING", format_type="standard")
        
        root_logger = logging.getLogger()
        handler = root_logger.handlers[0]
        
        # Should be a StreamHandler
        assert isinstance(handler, logging.StreamHandler)
        # Should have the same level as root logger
        assert handler.level == logging.WARNING
        # Should have a formatter
        assert handler.formatter is not None

    def test_setup_logging_returns_application_logger(self):
        """Test that setup_logging returns the application logger."""
        logger = setup_logging()
        
        # Should return the application-specific logger, not root
        assert logger.name == "ytdl_sub_config_manager"
        assert logger != logging.getLogger()  # Not the root logger

    def test_get_logger_hierarchy(self):
        """Test that get_logger creates proper logger hierarchy."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module1.submodule")
        logger3 = get_logger("module2")
        
        assert logger1.name == "ytdl_sub_config_manager.module1"
        assert logger2.name == "ytdl_sub_config_manager.module1.submodule"
        assert logger3.name == "ytdl_sub_config_manager.module2"
        
        # Should be different logger instances
        assert logger1 != logger2
        assert logger1 != logger3
        assert logger2 != logger3
