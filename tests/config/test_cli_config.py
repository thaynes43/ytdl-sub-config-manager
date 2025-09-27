"""Tests for CLI configuration management."""

import argparse
import pytest
from unittest.mock import patch

from src.config.cli_config import CLIConfigManager
from src.core.models import Activity


class TestCLIConfigManager:
    """Test the CLIConfigManager class."""

    def test_cli_config_manager_initialization(self):
        """Test CLIConfigManager initialization."""
        manager = CLIConfigManager()
        assert manager.parser is not None
        assert isinstance(manager.parser, argparse.ArgumentParser)

    def test_parser_creation_has_required_arguments(self):
        """Test that the parser has the required global arguments."""
        manager = CLIConfigManager()
        
        # Test that we can parse basic arguments
        args = manager.parser.parse_args(['scrape'])
        assert args.command == 'scrape'
        assert args.config is None  # No default
        assert args.log_level == 'INFO'  # default
        assert args.log_format == 'standard'  # default
        assert args.media_source == 'peloton'  # default

    def test_parser_global_arguments(self):
        """Test parsing global arguments."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            '--config', 'custom.yaml',
            '--log-level', 'DEBUG',
            '--log-format', 'json',
            '--media-source', 'custom',
            'scrape'
        ])
        
        assert args.config == 'custom.yaml'
        assert args.log_level == 'DEBUG'
        assert args.log_format == 'json'
        assert args.media_source == 'custom'
        assert args.command == 'scrape'

    def test_scrape_command_arguments(self):
        """Test scrape command specific arguments."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            'scrape',
            '--username', 'testuser',
            '--password', 'testpass',
            '--media-dir', '/test/media',
            '--subs-file', '/test/subs.yaml'
        ])
        
        assert args.command == 'scrape'
        assert args.username == 'testuser'
        assert args.password == 'testpass'
        assert args.media_dir == '/test/media'
        assert args.subs_file == '/test/subs.yaml'

    def test_scrape_command_optional_arguments(self):
        """Test scrape command optional arguments."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            'scrape',
            '--username', 'testuser',
            '--password', 'testpass',
            '--media-dir', '/test/media',
            '--subs-file', '/test/subs.yaml',
            '--github-repo', 'github.com/test/repo',
            '--github-token', 'ghp_test123',
            '--limit', '50',
            '--activities', 'cycling,strength',
            '--no-container',
            '--scrolls', '20',
            '--subscription-timeout-days', '30'
        ])
        
        assert args.github_repo == 'github.com/test/repo'
        assert args.github_token == 'ghp_test123'
        assert args.limit == 50
        assert args.activities == 'cycling,strength'
        assert args.no_container is True
        assert args.scrolls == 20
        assert args.subscription_timeout_days == 30

    def test_validate_command_arguments(self):
        """Test validate command specific arguments."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            'validate',
            '--media-dir', '/test/media',
            '--dry-run'
        ])
        
        assert args.command == 'validate'
        assert args.media_dir == '/test/media'
        assert args.dry_run is True

    def test_validate_command_without_dry_run(self):
        """Test validate command without dry-run flag."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            'validate',
            '--media-dir', '/test/media'
        ])
        
        assert args.command == 'validate'
        assert args.media_dir == '/test/media'
        assert args.dry_run is False  # default

    def test_validate_command_requires_media_dir(self):
        """Test that validate command requires media-dir argument."""
        manager = CLIConfigManager()

        with pytest.raises(SystemExit):  # argparse raises SystemExit for missing required args
            manager.parser.parse_args(['validate'])

    def test_args_to_config_dict_scrape_command(self):
        """Test converting scrape command args to config dict."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            '--log-level', 'DEBUG',
            '--log-format', 'json',
            'scrape',
            '--username', 'testuser',
            '--password', 'testpass',
            '--media-dir', '/test/media',
            '--subs-file', '/test/subs.yaml',
            '--github-repo', 'github.com/test/repo',
            '--github-token', 'ghp_test123',
            '--limit', '50',
            '--activities', 'cycling,strength',
            '--no-container',
            '--scrolls', '20',
            '--subscription-timeout-days', '30'
        ])
        
        config_dict = manager.args_to_config_dict(args)
        
        assert config_dict['username'] == 'testuser'
        assert config_dict['password'] == 'testpass'
        assert config_dict['media_dir'] == '/test/media'
        assert config_dict['subs_file'] == '/test/subs.yaml'
        assert config_dict['github_repo'] == 'github.com/test/repo'
        assert config_dict['github_token'] == 'ghp_test123'
        assert config_dict['limit'] == 50
        assert config_dict['activities'] == 'cycling,strength'
        assert config_dict['container'] is False  # no-container flag
        assert config_dict['scrolls'] == 20
        assert config_dict['subscription_timeout_days'] == 30
        assert config_dict['log_level'] == 'DEBUG'
        assert config_dict['log_format'] == 'json'

    def test_args_to_config_dict_validate_command(self):
        """Test converting validate command args to config dict."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            'validate',
            '--media-dir', '/test/media',
            '--dry-run'
        ])
        
        config_dict = manager.args_to_config_dict(args)
        
        # Validate command should only include global args and validate-specific args
        assert config_dict['log_level'] == 'INFO'  # Default
        assert config_dict['media_dir'] == '/test/media'
        # dry_run is not added to config dict by args_to_config_dict - it's handled by validate command
        assert 'dry_run' not in config_dict
        # Should not include scrape-specific args
        assert 'username' not in config_dict
        assert 'password' not in config_dict

    def test_args_to_config_dict_excludes_none_values(self):
        """Test that None values are excluded from config dict."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            'scrape',
            '--username', 'testuser',
            '--password', 'testpass',
            '--media-dir', '/test/media',
            '--subs-file', '/test/subs.yaml'
            # Not providing optional arguments
        ])
        
        config_dict = manager.args_to_config_dict(args)
        
        # Should include provided args
        assert 'username' in config_dict
        assert 'password' in config_dict
        assert 'media_dir' in config_dict
        assert 'subs_file' in config_dict
        
        # Should not include None values
        assert 'github_repo' not in config_dict
        assert 'github_token' not in config_dict

    def test_args_to_config_dict_handles_container_flags(self):
        """Test that the container flags are handled correctly."""
        manager = CLIConfigManager()
        
        # Test with --no-container flag
        args_no_container = manager.parser.parse_args([
            'scrape',
            '--username', 'testuser',
            '--password', 'testpass',
            '--media-dir', '/test/media',
            '--subs-file', '/test/subs.yaml',
            '--no-container'
        ])
        
        config_dict = manager.args_to_config_dict(args_no_container)
        assert config_dict['container'] is False
        
        # Test with --container flag
        args_container = manager.parser.parse_args([
            'scrape',
            '--username', 'testuser',
            '--password', 'testpass',
            '--media-dir', '/test/media',
            '--subs-file', '/test/subs.yaml',
            '--container'
        ])
        
        config_dict = manager.args_to_config_dict(args_container)
        assert config_dict['container'] is True
        
        # Test without any flag (should not be in config dict)
        args_without_flag = manager.parser.parse_args([
            'scrape',
            '--username', 'testuser',
            '--password', 'testpass',
            '--media-dir', '/test/media',
            '--subs-file', '/test/subs.yaml'
        ])
        
        config_dict = manager.args_to_config_dict(args_without_flag)
        assert 'container' not in config_dict

    def test_parse_args_validates_container_flags(self):
        """Test that parse_args validates conflicting container flags."""
        manager = CLIConfigManager()

        with pytest.raises(SystemExit):  # Should raise error for conflicting flags
            manager.parse_args([
                'scrape',
                '--container',
                '--no-container'
            ])

    def test_parser_help_text(self):
        """Test that parser generates help text without errors."""
        manager = CLIConfigManager()
        
        # This should not raise an exception
        help_text = manager.parser.format_help()
        assert 'ytdl-sub Config Manager' in help_text
        assert 'scrape' in help_text
        assert 'validate' in help_text

    def test_parser_version_information(self):
        """Test that version information is available."""
        manager = CLIConfigManager()
        
        # Check that version action exists
        with pytest.raises(SystemExit) as exc_info:
            manager.parser.parse_args(['--version'])
        
        assert exc_info.value.code == 0

    def test_invalid_log_level_choice(self):
        """Test that invalid log level choices are rejected."""
        manager = CLIConfigManager()
        
        with pytest.raises(SystemExit):  # argparse raises SystemExit on invalid choices
            manager.parser.parse_args([
                '--log-level', 'INVALID',
                'scrape'
            ])

    def test_invalid_log_format_choice(self):
        """Test that invalid log format choices are rejected."""
        manager = CLIConfigManager()
        
        with pytest.raises(SystemExit):  # argparse raises SystemExit on invalid choices
            manager.parser.parse_args([
                '--log-format', 'invalid',
                'scrape'
            ])

    def test_missing_required_scrape_arguments(self):
        """Test that missing required arguments for scrape command are handled."""
        manager = CLIConfigManager()
        
        # Parse args with missing required arguments - should not fail at parse time
        # Validation happens later in the config loading process
        args = manager.parser.parse_args(['scrape'])
        
        config_dict = manager.args_to_config_dict(args)
        
        # Should not include None values
        assert 'username' not in config_dict
        assert 'password' not in config_dict
        assert 'media_dir' not in config_dict
        assert 'subs_file' not in config_dict

    def test_numeric_argument_conversion(self):
        """Test that numeric arguments are properly converted."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            'scrape',
            '--username', 'testuser',
            '--password', 'testpass',
            '--media-dir', '/test/media',
            '--subs-file', '/test/subs.yaml',
            '--limit', '100',
            '--scrolls', '50'
        ])
        
        # Verify numeric arguments are converted to int by argparse
        assert isinstance(args.limit, int)
        assert args.limit == 100
        assert isinstance(args.scrolls, int)
        assert args.scrolls == 50
        
        config_dict = manager.args_to_config_dict(args)
        
        # Should be included as integers
        assert isinstance(config_dict['limit'], int)
        assert config_dict['limit'] == 100
        assert isinstance(config_dict['scrolls'], int)
        assert config_dict['scrolls'] == 50

    def test_boolean_flag_handling(self):
        """Test that boolean flags are handled correctly."""
        manager = CLIConfigManager()
        
        # Test skip-validation flag for scrape command
        args = manager.parser.parse_args([
            'scrape',
            '--skip-validation'
        ])
        
        config_dict = manager.args_to_config_dict(args)
        assert config_dict['skip_validation'] is True
        
        # Test without flag
        args = manager.parser.parse_args(['scrape'])
        config_dict = manager.args_to_config_dict(args)
        assert 'skip_validation' not in config_dict

    def test_subcommand_required_via_parse_args(self):
        """Test that a subcommand is required when using parse_args method."""
        manager = CLIConfigManager()
        
        # Direct parser doesn't require subcommand
        args = manager.parser.parse_args([])
        assert args.command is None
        
        # But our parse_args method validates it
        with pytest.raises(SystemExit):
            manager.parse_args([])

    def test_config_file_argument(self):
        """Test that config file argument works correctly."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            '--config', '/custom/path/config.yaml',
            'scrape'
        ])
        
        assert args.config == '/custom/path/config.yaml'

    def test_all_global_arguments_in_config_dict(self):
        """Test that all global arguments are included in config dict."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            '--config', 'test.yaml',
            '--log-level', 'ERROR',
            '--log-format', 'json',
            '--media-source', 'custom',
            'scrape'
        ])
        
        config_dict = manager.args_to_config_dict(args)
        
        # Global args should be in config dict
        assert config_dict['log_level'] == 'ERROR'
        assert config_dict['log_format'] == 'json'
        # media_source is not mapped in args_to_config_dict
        assert 'media_source' not in config_dict
        # Config file path is not included in config dict (it's used to load config)
        assert 'config' not in config_dict

    def test_source_argument_for_scrape(self):
        """Test that source argument works for scrape command."""
        manager = CLIConfigManager()
        
        args = manager.parser.parse_args([
            'scrape',
            '--source', 'peloton'
        ])
        
        assert args.source == 'peloton'
        
        # Should not be included in config dict (it's handled differently)
        config_dict = manager.args_to_config_dict(args)
        assert 'source' not in config_dict

    def test_version_action_works(self):
        """Test that version action works correctly."""
        manager = CLIConfigManager()
        
        # Version should exit with code 0
        with pytest.raises(SystemExit) as exc_info:
            manager.parser.parse_args(['--version'])
        
        assert exc_info.value.code == 0

    @patch('src.config.cli_config.__version__', '1.2.3')
    def test_version_string_format(self):
        """Test that version string is properly formatted."""
        manager = CLIConfigManager()
        
        # This will exit, but we can check the version string is used
        with pytest.raises(SystemExit):
            manager.parser.parse_args(['--version'])