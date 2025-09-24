"""Tests for logging configuration."""

import logging
import pytest
from unittest.mock import patch

from src.core.logging import setup_logging, get_logger, _generate_timestamped_filename


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

    def test_setup_logging_with_file_logging(self):
        """Test setup_logging with file logging configuration."""
        import tempfile
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "logs" / "test.log"
            
            # Test file logging setup
            logger = setup_logging(
                level="DEBUG",
                format_type="standard",
                log_file=str(log_file),
                max_file_size_mb=50,
                backup_count=5
            )
            
            assert logger.name == "ytdl_sub_config_manager"
            
            # Check that both console and file handlers were set up
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 2  # Console + File
            
            # Check that log directory was created
            assert log_file.parent.exists()
            
            # Test that logging actually works
            logger.info("Test log message")
            
            # Check that a timestamped log file was created (not the original path)
            # The actual filename will have timestamp, so find it
            log_files = list(log_file.parent.glob("test_*.log"))
            assert len(log_files) == 1
            
            timestamped_log_file = log_files[0]
            assert timestamped_log_file.exists()
            
            # Verify filename format (test_YYYYMMDD_HHMMSS.log)
            import re
            pattern = r"test_\d{8}_\d{6}\.log"
            assert re.match(pattern, timestamped_log_file.name), f"Filename {timestamped_log_file.name} doesn't match expected pattern"
            
            # Close all handlers to release file locks before reading
            for handler in root_logger.handlers[:]:
                handler.close()
                root_logger.removeHandler(handler)
            
            with open(timestamped_log_file, 'r', encoding='utf-8') as f:
                log_content = f.read()
                assert "Test log message" in log_content

    def test_setup_logging_file_logging_failure(self):
        """Test setup_logging handles file logging failures gracefully."""
        # Use a path that will definitely fail (null device on Windows)
        import os
        invalid_path = "NUL:/invalid.log" if os.name == 'nt' else "/dev/null/invalid.log"
        
        logger = setup_logging(
            level="INFO",
            format_type="standard",
            log_file=invalid_path
        )
        
        # Should still work with console logging
        assert logger.name == "ytdl_sub_config_manager"
        
        # Should have at least console handler (may or may not have file handler depending on OS)
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) >= 1

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
    
    def test_generate_timestamped_filename(self):
        """Test timestamped filename generation."""
        import re
        
        # Test with various file paths
        test_cases = [
            "logs/app.log",
            "/var/log/application.log", 
            "C:/logs/debug.log",
            "simple.log"
        ]
        
        for original_path in test_cases:
            timestamped = _generate_timestamped_filename(original_path)
            
            # Should contain timestamp in format YYYYMMDD_HHMMSS
            pattern = r".*_\d{8}_\d{6}\.log"
            assert re.search(pattern, timestamped), f"Timestamped filename {timestamped} doesn't match expected pattern"
            
            # Should preserve directory structure
            from pathlib import Path
            original = Path(original_path)
            timestamped_path = Path(timestamped)
            assert original.parent == timestamped_path.parent
            
            # Should preserve extension
            assert original.suffix == timestamped_path.suffix
    
    def test_generate_timestamped_filename_different_extensions(self):
        """Test timestamped filename generation with different extensions."""
        import re
        from pathlib import Path
        
        test_cases = [
            ("app.txt", r"app_\d{8}_\d{6}\.txt"),
            ("debug.json", r"debug_\d{8}_\d{6}\.json"),
            ("trace", r"trace_\d{8}_\d{6}$"),  # No extension
        ]
        
        for original_path, expected_pattern in test_cases:
            timestamped = _generate_timestamped_filename(original_path)
            assert re.match(expected_pattern, Path(timestamped).name), f"Filename {timestamped} doesn't match pattern {expected_pattern}"
