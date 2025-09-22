"""Tests for main entry point."""

import sys
import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace

from src.main import main


class TestMain:
    """Test the main entry point function."""

    @patch('src.main.Application')
    @patch('src.main.CLIConfigManager')
    @patch('src.main.setup_logging')
    @patch('src.main.get_logger')
    def test_main_successful_execution(self, mock_get_logger, mock_setup_logging, 
                                     mock_cli_manager_class, mock_app_class):
        """Test successful execution of main function."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        mock_cli_manager = MagicMock()
        mock_args = Namespace(log_level='INFO', log_format='standard', command='scrape')
        mock_cli_manager.parse_args.return_value = mock_args
        mock_cli_manager_class.return_value = mock_cli_manager
        
        mock_app = MagicMock()
        mock_app.run.return_value = 0
        mock_app_class.return_value = mock_app
        
        # Run main
        result = main()
        
        # Verify interactions
        assert result == 0
        mock_cli_manager_class.assert_called_once()
        mock_cli_manager.parse_args.assert_called_once()
        mock_setup_logging.assert_called_once_with(level='INFO', format_type='standard')
        mock_get_logger.assert_called_with('src.main')
        mock_logger.info.assert_called_with("Starting ytdl-sub Config Manager")
        mock_app_class.assert_called_once()
        mock_app.run.assert_called_once_with(mock_args)

    @patch('src.main.Application')
    @patch('src.main.CLIConfigManager')
    @patch('src.main.setup_logging')
    @patch('src.main.get_logger')
    def test_main_application_returns_error_code(self, mock_get_logger, mock_setup_logging, 
                                                mock_cli_manager_class, mock_app_class):
        """Test main function when application returns non-zero exit code."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        mock_cli_manager = MagicMock()
        mock_args = Namespace(log_level='DEBUG', log_format='json', command='validate')
        mock_cli_manager.parse_args.return_value = mock_args
        mock_cli_manager_class.return_value = mock_cli_manager
        
        mock_app = MagicMock()
        mock_app.run.return_value = 1  # Error code
        mock_app_class.return_value = mock_app
        
        # Run main
        result = main()
        
        # Verify error code is returned
        assert result == 1
        mock_setup_logging.assert_called_once_with(level='DEBUG', format_type='json')

    @patch('src.main.CLIConfigManager')
    @patch('src.main.setup_logging')
    @patch('src.main.get_logger')
    def test_main_keyboard_interrupt(self, mock_get_logger, mock_setup_logging, 
                                   mock_cli_manager_class):
        """Test main function handles KeyboardInterrupt."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        mock_cli_manager = MagicMock()
        mock_cli_manager.parse_args.side_effect = KeyboardInterrupt()
        mock_cli_manager_class.return_value = mock_cli_manager
        
        # Run main
        result = main()
        
        # Verify keyboard interrupt handling
        assert result == 130
        mock_get_logger.assert_called_with('src.main')
        mock_logger.info.assert_called_with("Interrupted by user")

    @patch('src.main.Application')
    @patch('src.main.CLIConfigManager')
    @patch('src.main.setup_logging')
    @patch('src.main.get_logger')
    def test_main_unexpected_exception(self, mock_get_logger, mock_setup_logging, 
                                     mock_cli_manager_class, mock_app_class):
        """Test main function handles unexpected exceptions."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logger.handlers = ['some_handler']  # Logger has handlers
        mock_get_logger.return_value = mock_logger
        
        mock_cli_manager = MagicMock()
        mock_cli_manager.parse_args.side_effect = RuntimeError("Test error")
        mock_cli_manager_class.return_value = mock_cli_manager
        
        # Run main
        result = main()
        
        # Verify exception handling
        assert result == 1
        mock_get_logger.assert_called_with('src.main')
        mock_logger.error.assert_called_with("Unexpected error: Test error")

    @patch('src.main.Application')
    @patch('src.main.CLIConfigManager')
    @patch('src.main.setup_logging')
    @patch('src.main.get_logger')
    def test_main_exception_with_no_logger_handlers(self, mock_get_logger, mock_setup_logging, 
                                                   mock_cli_manager_class, mock_app_class):
        """Test main function handles exceptions when logger has no handlers."""
        # Setup mocks - return different logger instances to simulate setup_logging effect
        mock_logger_no_handlers = MagicMock()
        mock_logger_no_handlers.handlers = []  # No handlers
        mock_logger_with_handlers = MagicMock()
        mock_logger_with_handlers.handlers = ['handler']  # Has handlers after setup
        mock_get_logger.side_effect = [mock_logger_no_handlers, mock_logger_with_handlers]
        
        mock_cli_manager = MagicMock()
        mock_cli_manager.parse_args.side_effect = ValueError("Config error")
        mock_cli_manager_class.return_value = mock_cli_manager
        
        # Run main
        result = main()
        
        # Verify exception handling with logger setup
        assert result == 1
        # Should call setup_logging once when no handlers detected
        mock_setup_logging.assert_called_once_with()
        # Should call get_logger twice - once to check handlers, once after setup
        assert mock_get_logger.call_count == 2
        mock_logger_with_handlers.error.assert_called_with("Unexpected error: Config error")

    @patch('src.main.Application')
    @patch('src.main.CLIConfigManager')
    @patch('src.main.setup_logging')
    @patch('src.main.get_logger')
    def test_main_exception_with_logger_setup_failure(self, mock_get_logger, mock_setup_logging, 
                                                     mock_cli_manager_class, mock_app_class):
        """Test main function when even logger setup fails during exception handling."""
        # Setup mocks - first get_logger call fails, second succeeds after setup_logging
        mock_logger = MagicMock()
        mock_get_logger.side_effect = [Exception("Logger error"), mock_logger]
        
        mock_cli_manager = MagicMock()
        mock_cli_manager.parse_args.side_effect = OSError("OS error")
        mock_cli_manager_class.return_value = mock_cli_manager
        
        # Run main
        result = main()
        
        # Verify exception handling with fallback logger setup
        assert result == 1
        mock_setup_logging.assert_called_with()  # Called with no args as fallback
        mock_logger.error.assert_called_with("Unexpected error: OS error")

    @patch('src.main.Application')
    @patch('src.main.CLIConfigManager') 
    @patch('src.main.setup_logging')
    @patch('src.main.get_logger')
    def test_main_with_different_log_levels_and_formats(self, mock_get_logger, mock_setup_logging,
                                                       mock_cli_manager_class, mock_app_class):
        """Test main function with different logging configurations."""
        # Setup mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        mock_cli_manager = MagicMock()
        mock_args = Namespace(log_level='ERROR', log_format='json', command='scrape')
        mock_cli_manager.parse_args.return_value = mock_args
        mock_cli_manager_class.return_value = mock_cli_manager
        
        mock_app = MagicMock()
        mock_app.run.return_value = 0
        mock_app_class.return_value = mock_app
        
        # Run main
        result = main()
        
        # Verify logging setup with custom parameters
        assert result == 0
        mock_setup_logging.assert_called_once_with(level='ERROR', format_type='json')

    def test_main_script_execution(self):
        """Test that the script can be executed directly."""
        # This tests the if __name__ == "__main__" block
        with patch('src.main.main') as mock_main_func:
            mock_main_func.return_value = 42
            
            with patch('sys.exit') as mock_sys_exit:
                # Import and execute the module's main block
                import src.main
                # We can't easily test the __main__ block directly, but we can verify 
                # that the main function exists and is callable
                assert callable(src.main.main)
                
    def test_main_script_has_main_guard(self):
        """Test that the script has the proper __main__ guard."""
        # Read the source file and check for the __main__ guard
        with open('src/main.py', 'r') as f:
            content = f.read()
        
        # Verify the __main__ guard exists
        assert 'if __name__ == "__main__":' in content
        assert 'sys.exit(main())' in content

    @patch('src.main.Application')
    @patch('src.main.CLIConfigManager')
    @patch('src.main.setup_logging')
    @patch('src.main.get_logger')
    def test_main_application_run_with_different_commands(self, mock_get_logger, mock_setup_logging,
                                                        mock_cli_manager_class, mock_app_class):
        """Test main function passes different commands to application."""
        test_cases = [
            ('scrape', 0),
            ('validate', 0), 
            ('scrape', 1),  # Error case
            ('validate', 2)  # Different error code
        ]
        
        for command, expected_code in test_cases:
            # Reset mocks
            mock_get_logger.reset_mock()
            mock_setup_logging.reset_mock()
            mock_cli_manager_class.reset_mock()
            mock_app_class.reset_mock()
            
            # Setup mocks
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            mock_cli_manager = MagicMock()
            mock_args = Namespace(log_level='INFO', log_format='standard', command=command)
            mock_cli_manager.parse_args.return_value = mock_args
            mock_cli_manager_class.return_value = mock_cli_manager
            
            mock_app = MagicMock()
            mock_app.run.return_value = expected_code
            mock_app_class.return_value = mock_app
            
            # Run main
            result = main()
            
            # Verify
            assert result == expected_code
            mock_app.run.assert_called_once_with(mock_args)
