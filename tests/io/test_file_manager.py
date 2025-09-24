"""Tests for FileManager class."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.io.file_manager import FileManager
from src.core.models import Activity, ActivityData


class TestFileManager:
    """Test the FileManager class."""

    def test_file_manager_initialization_with_validation(self):
        """Test FileManager initialization with validation enabled."""
        with patch('src.io.file_manager.GenericDirectoryValidator') as mock_validator_class:
            with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
                mock_validator = MagicMock()
                mock_validator.validate_and_repair.return_value = True
                mock_validator_class.return_value = mock_validator
                
                mock_manager = MagicMock()
                mock_manager_class.return_value = mock_manager
                
                file_manager = FileManager(
                    media_dir="/test/media",
                    subs_file="/test/subs.yaml",
                    validate_and_repair=True,
                    validation_strategies=["strategy1"],
                    repair_strategies=["repair1"],
                    episode_parsers=["parser1"]
                )
                
                assert file_manager.media_dir == "/test/media"
                assert file_manager.subs_file == "/test/subs.yaml"
                assert file_manager.validation_strategies == ["strategy1"]
                assert file_manager.repair_strategies == ["repair1"]
                assert file_manager.episode_parsers == ["parser1"]
                
                # Should create validator and run validation
                mock_validator_class.assert_called_once_with(
                    media_dir="/test/media",
                    validation_strategies=["strategy1"],
                    repair_strategies=["repair1"]
                )
                mock_validator.validate_and_repair.assert_called_once()

    def test_file_manager_initialization_without_validation(self):
        """Test FileManager initialization with validation disabled."""
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                validation_strategies=["strategy1"],
                repair_strategies=["repair1"],
                episode_parsers=["parser1"]
            )
            
            assert file_manager.directory_validator is None

    def test_file_manager_validation_strategies_required_error(self):
        """Test that validation strategies are required when validate_and_repair=True."""
        with pytest.raises(ValueError, match="validation_strategies and repair_strategies are required"):
            FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=True,
                validation_strategies=[],  # Empty
                repair_strategies=["repair1"],
                episode_parsers=["parser1"]
            )

    def test_file_manager_repair_strategies_required_error(self):
        """Test that repair strategies are required when validate_and_repair=True."""
        with pytest.raises(ValueError, match="validation_strategies and repair_strategies are required"):
            FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=True,
                validation_strategies=["strategy1"],
                repair_strategies=[],  # Empty
                episode_parsers=["parser1"]
            )

    def test_file_manager_episode_parsers_required_error(self):
        """Test that episode parsers are required."""
        with pytest.raises(ValueError, match="episode_parsers are required"):
            FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                validation_strategies=["strategy1"],
                repair_strategies=["repair1"],
                episode_parsers=[]  # Empty
            )

    def test_file_manager_validation_failure_raises_error(self):
        """Test that validation failure raises RuntimeError."""
        with patch('src.io.file_manager.GenericDirectoryValidator') as mock_validator_class:
            mock_validator = MagicMock()
            mock_validator.validate_and_repair.return_value = False  # Validation fails
            mock_validator_class.return_value = mock_validator
            
            with pytest.raises(RuntimeError, match="Directory structure validation failed"):
                FileManager(
                    media_dir="/test/media",
                    subs_file="/test/subs.yaml",
                    validate_and_repair=True,
                    validation_strategies=["strategy1"],
                    repair_strategies=["repair1"],
                    episode_parsers=["parser1"]
                )

    def test_get_merged_episode_data(self):
        """Test get_merged_episode_data method."""
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            expected_data = {Activity.CYCLING: ActivityData(activity=Activity.CYCLING)}
            mock_manager.get_merged_episode_data.return_value = expected_data
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            result = file_manager.get_merged_episode_data()
            assert result == expected_data
            mock_manager.get_merged_episode_data.assert_called_once()

    def test_get_next_episode_number(self):
        """Test get_next_episode_number method."""
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            
            # Setup merged data
            activity_data = ActivityData(activity=Activity.CYCLING)
            activity_data.max_episode = {20: 5, 30: 10}
            merged_data = {Activity.CYCLING: activity_data}
            mock_manager.get_merged_episode_data.return_value = merged_data
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            # Test existing activity and season
            result = file_manager.get_next_episode_number(Activity.CYCLING, 20)
            assert result == 6  # max is 5, so next is 6
            
            # Test existing activity, new season
            result = file_manager.get_next_episode_number(Activity.CYCLING, 45)
            assert result == 1  # new season, so start at 1
            
            # Test new activity
            result = file_manager.get_next_episode_number(Activity.YOGA, 30)
            assert result == 1  # new activity, so start at 1

    def test_find_all_existing_class_ids(self):
        """Test find_all_existing_class_ids method."""
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            expected_ids = {'id1', 'id2', 'id3'}
            mock_manager.find_all_existing_class_ids.return_value = expected_ids
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            result = file_manager.find_all_existing_class_ids()
            assert result == expected_ids
            mock_manager.find_all_existing_class_ids.assert_called_once()

    def test_cleanup_subscriptions(self):
        """Test cleanup_subscriptions method."""
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager.cleanup_subscriptions.return_value = True
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            result = file_manager.cleanup_subscriptions()
            assert result is True
            mock_manager.cleanup_subscriptions.assert_called_once()

    @patch('builtins.open')
    @patch('yaml.safe_load')
    @patch('yaml.dump')
    @patch('src.io.file_manager.Path')
    def test_add_new_subscriptions_success(self, mock_path_class, mock_yaml_dump, mock_yaml_safe_load, mock_open):
        """Test add_new_subscriptions method with successful addition."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        mock_yaml_safe_load.return_value = {"Plex TV Show by Date": {"existing": "data"}}
        mock_open.return_value.__enter__.return_value = MagicMock()
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            subscriptions = {
                "20min": {
                    "Episode 1": {"download": "url1", "overrides": {"season_number": 1}},
                    "Episode 2": {"download": "url2", "overrides": {"season_number": 1}}
                }
            }
            
            result = file_manager.add_new_subscriptions(subscriptions)
            assert result is True
            
            # Verify YAML operations
            mock_yaml_safe_load.assert_called_once()
            mock_yaml_dump.assert_called_once()
            # Verify file operations
            assert mock_open.call_count == 2  # Once for read, once for write

    @patch('builtins.open')
    @patch('yaml.dump')
    @patch('src.io.file_manager.Path')
    def test_add_new_subscriptions_file_not_exists(self, mock_path_class, mock_yaml_dump, mock_open):
        """Test add_new_subscriptions method when file doesn't exist."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path
        
        mock_open.return_value.__enter__.return_value = MagicMock()
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            subscriptions = {"20min": {"Episode 1": {"download": "url1"}}}
            
            result = file_manager.add_new_subscriptions(subscriptions)
            assert result is True
            
            # Should still dump the new structure
            mock_yaml_dump.assert_called_once()
            # Should only write (no read since file doesn't exist)
            mock_open.assert_called_once()

    def test_add_new_subscriptions_empty_subscriptions(self):
        """Test add_new_subscriptions method with empty subscriptions."""
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            result = file_manager.add_new_subscriptions({})
            assert result is True  # Empty is considered success

    @patch('yaml.safe_load')
    def test_add_new_subscriptions_exception_handling(self, mock_yaml_safe_load):
        """Test add_new_subscriptions method exception handling."""
        mock_yaml_safe_load.side_effect = Exception("YAML error")
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            subscriptions = {"20min": {"Episode 1": {"download": "url1"}}}
            
            result = file_manager.add_new_subscriptions(subscriptions)
            assert result is False

    @patch('builtins.open')
    @patch('yaml.dump')
    @patch('yaml.safe_load')
    @patch('src.io.file_manager.Path')
    def test_add_new_subscriptions_unicode_handling(self, mock_path_class, mock_yaml_safe_load, mock_yaml_dump, mock_open):
        """Test add_new_subscriptions method handles Unicode characters correctly."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        mock_yaml_safe_load.return_value = {"Plex TV Show by Date": {}}
        mock_file_handle = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file_handle
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            # Test with Unicode characters including accented characters
            subscriptions_with_unicode = {
                "30min": {
                    "10 min Focus Flow: For Runners with Mariana Fernández": {
                        "download": "https://example.com/class1", 
                        "overrides": {
                            "tv_show_directory": "/media/peloton/Yoga/Mariana Fernández",
                            "season_number": 10,
                            "episode_number": 31
                        }
                    },
                    "Café Morning Flow with José María": {
                        "download": "https://example.com/class2",
                        "overrides": {
                            "tv_show_directory": "/media/peloton/Yoga/José María",
                            "season_number": 10,
                            "episode_number": 32
                        }
                    }
                }
            }
            
            # Call method
            result = file_manager.add_new_subscriptions(subscriptions_with_unicode)
            assert result is True
            
            # Verify that files were opened with UTF-8 encoding
            mock_open.assert_any_call(mock_path, 'r', encoding='utf-8')
            mock_open.assert_any_call(mock_path, 'w', encoding='utf-8')
            
            # Verify YAML dump was called with allow_unicode=True
            mock_yaml_dump.assert_called_once()
            call_args = mock_yaml_dump.call_args
            assert call_args[1]['allow_unicode'] is True
            
            # Verify the data structure passed to yaml.dump contains Unicode correctly
            dumped_data = call_args[0][0]  # First positional argument to yaml.dump
            
            # Check that Unicode characters are preserved in the data structure
            plex_section = dumped_data["Plex TV Show by Date"]["30min"]
            assert "10 min Focus Flow: For Runners with Mariana Fernández" in plex_section
            assert "Café Morning Flow with José María" in plex_section
            
            # Verify directory paths contain Unicode characters
            fernandez_entry = plex_section["10 min Focus Flow: For Runners with Mariana Fernández"]
            assert fernandez_entry["overrides"]["tv_show_directory"] == "/media/peloton/Yoga/Mariana Fernández"
            
            jose_entry = plex_section["Café Morning Flow with José María"]
            assert jose_entry["overrides"]["tv_show_directory"] == "/media/peloton/Yoga/José María"

    @patch('src.io.file_manager.Path')
    def test_validate_directories_success(self, mock_path_class):
        """Test validate_directories method with successful validation."""
        # Setup mocks
        mock_media_path = MagicMock()
        mock_media_path.exists.return_value = True
        mock_media_path.is_dir.return_value = True
        
        mock_subs_path = MagicMock()
        mock_subs_path.exists.return_value = True
        mock_subs_path.is_file.return_value = True
        mock_subs_path.parent.exists.return_value = True
        
        mock_path_class.side_effect = [mock_media_path, mock_subs_path, mock_subs_path.parent]
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            with patch('builtins.open', mock_open_multiple_files()):
                mock_manager = MagicMock()
                mock_manager_class.return_value = mock_manager
                
                file_manager = FileManager(
                    media_dir="/test/media",
                    subs_file="/test/subs.yaml",
                    validate_and_repair=False,
                    episode_parsers=["parser1"]
                )
                
                result = file_manager.validate_directories()
                assert result is True

    @patch('src.io.file_manager.Path')
    def test_validate_directories_media_dir_not_exists(self, mock_path_class):
        """Test validate_directories method when media directory doesn't exist."""
        # Setup mocks
        mock_media_path = MagicMock()
        mock_media_path.exists.return_value = False
        
        mock_subs_path = MagicMock()
        mock_subs_path.exists.return_value = True
        mock_subs_path.is_file.return_value = True
        mock_subs_path.parent.exists.return_value = True
        
        mock_path_class.side_effect = [mock_media_path, mock_subs_path, mock_subs_path.parent]
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            with patch('builtins.open', mock_open_multiple_files()):
                mock_manager = MagicMock()
                mock_manager_class.return_value = mock_manager
                
                file_manager = FileManager(
                    media_dir="/test/media",
                    subs_file="/test/subs.yaml",
                    validate_and_repair=False,
                    episode_parsers=["parser1"]
                )
                
                # Should still pass (media dir not existing is OK for first run)
                result = file_manager.validate_directories()
                assert result is True

    @patch('src.io.file_manager.Path')
    def test_validate_directories_media_path_not_dir(self, mock_path_class):
        """Test validate_directories method when media path is not a directory."""
        # Setup mocks
        mock_media_path = MagicMock()
        mock_media_path.exists.return_value = True
        mock_media_path.is_dir.return_value = False  # Not a directory
        
        mock_path_class.return_value = mock_media_path
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            result = file_manager.validate_directories()
            assert result is False

    @patch('src.io.file_manager.GenericDirectoryValidator')
    def test_repair_directory_structure(self, mock_validator_class):
        """Test repair_directory_structure method."""
        mock_validator = MagicMock()
        mock_validator.validate_and_repair.return_value = True
        mock_validator_class.return_value = mock_validator
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                validation_strategies=["strategy1"],
                repair_strategies=["repair1"],
                episode_parsers=["parser1"]
            )
            
            result = file_manager.repair_directory_structure(dry_run=True)
            assert result is True
            
            # Should create new validator with dry_run setting
            mock_validator_class.assert_called_with(
                media_dir="/test/media",
                validation_strategies=["strategy1"],
                repair_strategies=["repair1"],
                dry_run=True
            )
            mock_validator.validate_and_repair.assert_called_once()


def mock_open_multiple_files():
    """Helper to mock opening multiple files for read/write."""
    from unittest.mock import mock_open
    return mock_open(read_data="test data")
