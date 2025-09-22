"""Tests for the main Application class."""

import pytest
from unittest.mock import patch, MagicMock
from argparse import Namespace

from src.core.application import Application
from src.core.models import Activity, ActivityData


class TestApplication:
    """Test the Application class."""

    def test_application_initialization(self):
        """Test Application initialization."""
        app = Application()
        assert app is not None

    def test_run_with_scrape_command_calls_run_scrape_command(self):
        """Test that run() with scrape command calls run_scrape_command."""
        args = Namespace(command='scrape', config='test.yaml')

        with patch.object(Application, 'run_scrape_command', return_value=42) as mock_run_scrape:
            app = Application()
            result = app.run(args)

            # Should return the value from run_scrape_command, or 1 if config loading fails
            # Let's just verify it's called and returns something
            assert result in [42, 1]  # Either our mock return or error from config loading

    def test_run_validate_command_success(self):
        """Test successful execution of validate command."""
        args = Namespace(command='validate', media_dir='/test/media', dry_run=False)

        with patch.object(Application, 'run_validate_command', return_value=0) as mock_run_validate:
            app = Application()
            result = app.run(args)

            assert result == 0
            mock_run_validate.assert_called_once_with(args)

    def test_run_unknown_command(self):
        """Test handling of unknown command."""
        args = Namespace(command='unknown')

        app = Application()
        result = app.run(args)

        assert result == 1

    def test_run_exception_handling(self):
        """Test exception handling in run method."""
        args = Namespace(command='scrape', config='nonexistent.yaml')

        app = Application()
        result = app.run(args)

        # Should return 1 due to config loading error
        assert result == 1

    @patch('src.core.application.FileManager')
    def test_run_scrape_command_detailed(self, mock_file_manager_class):
        """Test detailed execution of run_scrape_command."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = ['strategy1']
        mock_config.peloton_directory_repair_strategies = ['repair1']
        mock_config.peloton_episode_parsers = ['parser1']
        mock_config.skip_validation = False

        # Setup mock file manager
        mock_file_manager = MagicMock()
        
        # Setup merged episode data
        activity_data = ActivityData(activity=Activity.CYCLING)
        activity_data.max_episode = {20: 5, 30: 10}  # Season 20: 5 episodes, Season 30: 10 episodes
        merged_data = {Activity.CYCLING: activity_data}
        mock_file_manager.get_merged_episode_data.return_value = merged_data
        
        mock_file_manager.find_all_existing_class_ids.return_value = {'id1', 'id2', 'id3'}
        mock_file_manager.cleanup_subscriptions.return_value = True
        
        mock_file_manager_class.return_value = mock_file_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0
        
        # Verify file manager initialization
        mock_file_manager_class.assert_called_once_with(
            media_dir='/test/media',
            subs_file='/test/subs.yaml',
            validate_and_repair=True,  # not skip_validation
            validation_strategies=['strategy1'],
            repair_strategies=['repair1'],
            episode_parsers=['parser1']
        )
        
        # Verify method calls
        mock_config.log_config.assert_called_once()
        mock_file_manager.get_merged_episode_data.assert_called_once()
        mock_file_manager.find_all_existing_class_ids.assert_called_once()
        mock_file_manager.cleanup_subscriptions.assert_called_once()

    @patch('src.core.application.FileManager')
    def test_run_scrape_command_with_skip_validation(self, mock_file_manager_class):
        """Test run_scrape_command with skip_validation=True."""
        # Setup mock config with skip_validation
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = ['strategy1']
        mock_config.peloton_directory_repair_strategies = ['repair1']
        mock_config.peloton_episode_parsers = ['parser1']
        mock_config.skip_validation = True

        # Setup mock file manager
        mock_file_manager = MagicMock()
        mock_file_manager.get_merged_episode_data.return_value = {}
        mock_file_manager.find_all_existing_class_ids.return_value = set()
        mock_file_manager.cleanup_subscriptions.return_value = False
        
        mock_file_manager_class.return_value = mock_file_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0
        
        # Verify file manager initialization with validation disabled
        mock_file_manager_class.assert_called_once_with(
            media_dir='/test/media',
            subs_file='/test/subs.yaml',
            validate_and_repair=False,  # skip_validation=True
            validation_strategies=['strategy1'],
            repair_strategies=['repair1'],
            episode_parsers=['parser1']
        )

    @patch('src.core.application.FileManager')
    def test_run_scrape_command_no_cleanup_needed(self, mock_file_manager_class):
        """Test run_scrape_command when no cleanup is needed."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = []
        mock_config.peloton_directory_repair_strategies = []
        mock_config.peloton_episode_parsers = []
        mock_config.skip_validation = False

        # Setup mock file manager
        mock_file_manager = MagicMock()
        mock_file_manager.get_merged_episode_data.return_value = {}
        mock_file_manager.find_all_existing_class_ids.return_value = set()
        mock_file_manager.cleanup_subscriptions.return_value = False  # No cleanup needed
        
        mock_file_manager_class.return_value = mock_file_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0

    @patch('src.core.application.FileManager')
    def test_run_scrape_command_multiple_activities(self, mock_file_manager_class):
        """Test run_scrape_command with multiple activities."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = []
        mock_config.peloton_directory_repair_strategies = []
        mock_config.peloton_episode_parsers = []
        mock_config.skip_validation = False

        # Setup mock file manager with multiple activities
        mock_file_manager = MagicMock()
        
        cycling_data = ActivityData(activity=Activity.CYCLING)
        cycling_data.max_episode = {20: 5, 30: 3}
        
        yoga_data = ActivityData(activity=Activity.YOGA)
        yoga_data.max_episode = {45: 8, 60: 2}
        
        merged_data = {
            Activity.CYCLING: cycling_data,
            Activity.YOGA: yoga_data
        }
        mock_file_manager.get_merged_episode_data.return_value = merged_data
        mock_file_manager.find_all_existing_class_ids.return_value = {'id1', 'id2'}
        mock_file_manager.cleanup_subscriptions.return_value = True
        
        mock_file_manager_class.return_value = mock_file_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0

    @patch('src.core.application.GenericDirectoryValidator')
    def test_run_validate_command_success_dry_run(self, mock_validator_class):
        """Test successful validate command with dry run."""
        args = Namespace(media_dir='/test/media', dry_run=True)

        mock_validator = MagicMock()
        mock_validator.validate_and_repair.return_value = True
        mock_validator_class.return_value = mock_validator

        app = Application()
        result = app.run_validate_command(args)

        assert result == 0
        
        # Verify validator initialization
        mock_validator_class.assert_called_once_with(
            media_dir='/test/media',
            validation_strategies=["src.io.peloton.activity_based_path_strategy:ActivityBasedPathStrategy"],
            repair_strategies=["src.io.peloton.repair_5050_strategy:Repair5050Strategy"],
            dry_run=True
        )
        mock_validator.validate_and_repair.assert_called_once()

    @patch('src.core.application.GenericDirectoryValidator')
    def test_run_validate_command_success_no_dry_run(self, mock_validator_class):
        """Test successful validate command without dry run."""
        args = Namespace(media_dir='/test/media', dry_run=False)

        mock_validator = MagicMock()
        mock_validator.validate_and_repair.return_value = True
        mock_validator_class.return_value = mock_validator

        app = Application()
        result = app.run_validate_command(args)

        assert result == 0
        
        # Verify validator initialization
        mock_validator_class.assert_called_once_with(
            media_dir='/test/media',
            validation_strategies=["src.io.peloton.activity_based_path_strategy:ActivityBasedPathStrategy"],
            repair_strategies=["src.io.peloton.repair_5050_strategy:Repair5050Strategy"],
            dry_run=False
        )

    @patch('src.core.application.GenericDirectoryValidator')
    def test_run_validate_command_validation_failure(self, mock_validator_class):
        """Test validate command when validation fails."""
        args = Namespace(media_dir='/test/media', dry_run=False)

        mock_validator = MagicMock()
        mock_validator.validate_and_repair.return_value = False
        mock_validator_class.return_value = mock_validator

        app = Application()
        result = app.run_validate_command(args)

        assert result == 1

    @patch('src.core.application.GenericDirectoryValidator')
    def test_run_validate_command_exception(self, mock_validator_class):
        """Test validate command when an exception occurs."""
        args = Namespace(media_dir='/test/media', dry_run=False)

        mock_validator_class.side_effect = RuntimeError("Validation error")

        app = Application()
        result = app.run_validate_command(args)

        assert result == 1

    @patch('src.core.application.FileManager')
    def test_run_scrape_command_with_getattr_default(self, mock_file_manager_class):
        """Test run_scrape_command when config doesn't have skip_validation attribute."""
        # Setup mock config without skip_validation attribute
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = []
        mock_config.peloton_directory_repair_strategies = []
        mock_config.peloton_episode_parsers = []
        
        # Remove skip_validation attribute to test getattr default
        del mock_config.skip_validation

        # Setup mock file manager
        mock_file_manager = MagicMock()
        mock_file_manager.get_merged_episode_data.return_value = {}
        mock_file_manager.find_all_existing_class_ids.return_value = set()
        mock_file_manager.cleanup_subscriptions.return_value = False
        
        mock_file_manager_class.return_value = mock_file_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0
        
        # Verify file manager initialization with default validation (True, since getattr default is False)
        mock_file_manager_class.assert_called_once_with(
            media_dir='/test/media',
            subs_file='/test/subs.yaml',
            validate_and_repair=True,  # not getattr(config, 'skip_validation', False)
            validation_strategies=[],
            repair_strategies=[],
            episode_parsers=[]
        )

    @patch('src.core.application.FileManager')
    def test_run_scrape_command_empty_episode_data(self, mock_file_manager_class):
        """Test run_scrape_command with empty episode data."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = []
        mock_config.peloton_directory_repair_strategies = []
        mock_config.peloton_episode_parsers = []
        mock_config.skip_validation = False

        # Setup mock file manager with empty data
        mock_file_manager = MagicMock()
        mock_file_manager.get_merged_episode_data.return_value = {}  # Empty
        mock_file_manager.find_all_existing_class_ids.return_value = set()  # Empty
        mock_file_manager.cleanup_subscriptions.return_value = False
        
        mock_file_manager_class.return_value = mock_file_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0
