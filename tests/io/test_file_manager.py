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
            
            # Verify preset was updated with configured media directory
            dumped_data = mock_yaml_dump.call_args[0][0]
            assert "__preset__" in dumped_data
            assert dumped_data["__preset__"]["overrides"]["tv_show_directory"] == "/test/media"

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

    @patch('builtins.open')
    @patch('yaml.dump')
    @patch('yaml.safe_load')
    @patch('src.io.file_manager.Path')
    def test_update_subscription_directories_success(self, mock_path_class, mock_yaml_safe_load, mock_yaml_dump, mock_open):
        """Test update_subscription_directories method with successful updates."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        # Mock existing subscription data with old media directory
        mock_yaml_safe_load.return_value = {
            "Plex TV Show by Date": {
                "= Cycling (30 min)": {
                    "Test Ride with Instructor One": {
                        "download": "https://example.com/class1",
                        "overrides": {
                            "tv_show_directory": "/media/peloton/Cycling/Instructor One",
                            "season_number": 30,
                            "episode_number": 1
                        }
                    }
                },
                "= Strength (20 min)": {
                    "Test Workout with Instructor Two": {
                        "download": "https://example.com/class2",
                        "overrides": {
                            "tv_show_directory": "/old/media/path/Strength/Instructor Two",
                            "season_number": 20,
                            "episode_number": 1
                        }
                    }
                }
            }
        }
        
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
            
            # Call method with new media directory
            result = file_manager.update_subscription_directories("D:/labspace/tmp/test-media")
            assert result is True
            
            # Verify YAML dump was called
            mock_yaml_dump.assert_called_once()
            
            # Verify the updated data structure
            dumped_data = mock_yaml_dump.call_args[0][0]
            cycling_entry = dumped_data["Plex TV Show by Date"]["= Cycling (30 min)"]["Test Ride with Instructor One"]
            strength_entry = dumped_data["Plex TV Show by Date"]["= Strength (20 min)"]["Test Workout with Instructor Two"]
            
            # Check that directories were updated
            assert cycling_entry["overrides"]["tv_show_directory"] == "D:/labspace/tmp/test-media/Cycling/Instructor One"
            assert strength_entry["overrides"]["tv_show_directory"] == "D:/labspace/tmp/test-media/Strength/Instructor Two"

    @patch('builtins.open')
    @patch('yaml.safe_load')
    @patch('src.io.file_manager.Path')
    def test_update_subscription_directories_no_file(self, mock_path_class, mock_yaml_safe_load, mock_open):
        """Test update_subscription_directories method when file doesn't exist."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="/test/media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            # Call method
            result = file_manager.update_subscription_directories("D:/labspace/tmp/test-media")
            assert result is True
            
            # Should not try to read or write files
            mock_open.assert_not_called()

    @patch('builtins.open')
    @patch('yaml.dump')
    @patch('yaml.safe_load')
    @patch('src.io.file_manager.Path')
    def test_update_subscription_directories_no_changes_needed(self, mock_path_class, mock_yaml_safe_load, mock_yaml_dump, mock_open):
        """Test update_subscription_directories method when no changes are needed."""
        # Setup mocks
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        # Mock existing subscription data that already matches target directory
        mock_yaml_safe_load.return_value = {
            "Plex TV Show by Date": {
                "= Cycling (30 min)": {
                    "Test Ride with Instructor One": {
                        "download": "https://example.com/class1",
                        "overrides": {
                            "tv_show_directory": "D:/labspace/tmp/test-media/Cycling/Instructor One",
                            "season_number": 30,
                            "episode_number": 1
                        }
                    }
                }
            }
        }
        
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
            
            # Call method with same media directory
            result = file_manager.update_subscription_directories("D:/labspace/tmp/test-media")
            assert result is True
            
            # Should not write back to file since no changes were needed
            mock_yaml_dump.assert_not_called()

    def test_validate_and_resolve_subscription_conflicts_integration(self):
        """Integration test for validate_and_resolve_subscription_conflicts with real files."""
        import tempfile
        import yaml
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create media directory structure with existing episode
            media_dir = temp_path / "media"
            cycling_dir = media_dir / "Cycling" / "Hannah Corbin"
            existing_episode_dir = cycling_dir / "S20E1 - 2024-01-15 - 20 min Pop Ride with Hannah Corbin"
            existing_episode_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subscriptions file with potential conflict
            subs_file = temp_path / "subscriptions.yaml"
            subs_data = {
                "Plex TV Show by Date": {
                    "= Cycling (20 min)": {
                        "20 min Pick-Me-Up Ride with Hannah Corbin": {
                            "download": "https://members.onepeloton.com/classes/player/97209d52427247b995645c70479a8e2d",
                            "overrides": {
                                "tv_show_directory": str(cycling_dir),
                                "season_number": 20,
                                "episode_number": 1
                            }
                        }
                    }
                }
            }
            
            with open(subs_file, 'w', encoding='utf-8') as f:
                yaml.dump(subs_data, f, allow_unicode=True, default_flow_style=False, indent=2)
            
            # Create FileManager and test conflict resolution
            file_manager = FileManager(
                media_dir=str(media_dir),
                subs_file=str(subs_file),
                validate_and_repair=False,
                episode_parsers=["src.io.peloton.episodes_from_disk:EpisodesFromDisk"]
            )
            
            # Test conflict resolution
            result = file_manager.validate_and_resolve_subscription_conflicts()
            assert result is True
            
            # Check if the subscription file was updated
            with open(subs_file, 'r', encoding='utf-8') as f:
                updated_subs_data = yaml.safe_load(f)
            
            cycling_section = updated_subs_data["Plex TV Show by Date"]["= Cycling (20 min)"]
            
            # Should have the original title with hash suffix
            expected_new_title = "20 min Pick-Me-Up Ride with Hannah Corbin 97209d5"
            assert expected_new_title in cycling_section
            
            # Should not have the original title without suffix
            original_title = "20 min Pick-Me-Up Ride with Hannah Corbin"
            assert original_title not in cycling_section

    def test_validate_and_resolve_subscription_conflicts_with_fifty_fifty(self):
        """Integration test for conflict resolution with 50/50 case (filesystem sanitization + conflict resolution)."""
        import tempfile
        import yaml
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create media directory structure with existing 50/50 episode
            media_dir = temp_path / "media"
            strength_dir = media_dir / "Strength" / "Kirra Michel"
            existing_episode_dir = strength_dir / "S15E1 - 2024-01-15 - 15 min 50-50 Workout with Kirra Michel"
            existing_episode_dir.mkdir(parents=True, exist_ok=True)
            
            # Create subscriptions file with another 50/50 episode that would conflict
            subs_file = temp_path / "subscriptions.yaml"
            subs_data = {
                "Plex TV Show by Date": {
                    "= Strength (15 min)": {
                        "15 min 50/50 Advanced Workout with Kirra Michel": {
                            "download": "https://members.onepeloton.com/classes/player/abc123def456789012345678901234567890",
                            "overrides": {
                                "tv_show_directory": str(strength_dir),
                                "season_number": 15,
                                "episode_number": 1
                            }
                        }
                    }
                }
            }
            
            with open(subs_file, 'w', encoding='utf-8') as f:
                yaml.dump(subs_data, f, allow_unicode=True, default_flow_style=False, indent=2)
            
            # Create FileManager and test conflict resolution
            file_manager = FileManager(
                media_dir=str(media_dir),
                subs_file=str(subs_file),
                validate_and_repair=False,
                episode_parsers=["src.io.peloton.episodes_from_disk:EpisodesFromDisk"]
            )
            
            # Test conflict resolution
            result = file_manager.validate_and_resolve_subscription_conflicts()
            assert result is True
            
            # Check if the subscription file was updated
            with open(subs_file, 'r', encoding='utf-8') as f:
                updated_subs_data = yaml.safe_load(f)
            
            strength_section = updated_subs_data["Plex TV Show by Date"]["= Strength (15 min)"]
            
            # Should have the title with both filesystem sanitization (50/50 -> 50-50) and hash suffix
            expected_new_title = "15 min 50-50 Advanced Workout with Kirra Michel abc123d"
            assert expected_new_title in strength_section
            
            # Should not have the original title
            original_title = "15 min 50/50 Advanced Workout with Kirra Michel"
            assert original_title not in strength_section
            
            # Verify the entry data is preserved
            entry_data = strength_section[expected_new_title]
            assert entry_data["download"] == "https://members.onepeloton.com/classes/player/abc123def456789012345678901234567890"
            assert entry_data["overrides"]["season_number"] == 15
            assert entry_data["overrides"]["episode_number"] == 1

    @patch('builtins.open')
    @patch('yaml.safe_load')
    @patch('src.io.file_manager.Path')
    @patch('os.walk')
    def test_validate_and_resolve_subscription_conflicts_no_conflicts(self, mock_walk, mock_path_class, mock_yaml_safe_load, mock_open):
        """Test validate_and_resolve_subscription_conflicts with no conflicts."""
        # Setup mocks for filesystem
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path
        
        # Mock filesystem with different episodes (no conflicts)
        mock_walk.return_value = [
            ("D:/labspace/tmp/test-media/Cycling/Hannah Corbin", ["S30E001 - 2024-01-15 - 30 min Different Ride"], [])
        ]
        
        # Mock subscription data
        mock_yaml_safe_load.return_value = {
            "Plex TV Show by Date": {
                "= Cycling (20 min)": {
                    "20 min Pick-Me-Up Ride with Hannah Corbin": {
                        "download": "https://members.onepeloton.com/classes/player/97209d52427247b995645c70479a8e2d",
                        "overrides": {
                            "tv_show_directory": "D:/labspace/tmp/test-media/Cycling/Hannah Corbin",
                            "season_number": 20,
                            "episode_number": 1
                        }
                    }
                }
            }
        }
        
        mock_file_handle = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file_handle
        
        with patch('src.io.file_manager.GenericEpisodeManager') as mock_manager_class:
            mock_manager = MagicMock()
            mock_manager_class.return_value = mock_manager
            
            file_manager = FileManager(
                media_dir="D:/labspace/tmp/test-media",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            # Call method
            result = file_manager.validate_and_resolve_subscription_conflicts()
            assert result is True

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
    
    def test_update_preset_media_directory(self):
        """Test that preset media directory is updated correctly."""
        with patch('src.io.file_manager.GenericEpisodeManager'):
            file_manager = FileManager(
                media_dir="/custom/media/path",
                subs_file="/test/subs.yaml",
                validate_and_repair=False,
                episode_parsers=["parser1"]
            )
            
            # Test data with old hardcoded path
            subs_data = {
                "__preset__": {
                    "overrides": {"tv_show_directory": "/media/peloton"}
                }
            }
            
            # Update preset
            file_manager._update_preset_media_directory(subs_data)
            
            # Verify it was updated to the configured path
            assert subs_data["__preset__"]["overrides"]["tv_show_directory"] == "/custom/media/path"
            
            # Verify defaults are added
            assert subs_data["__preset__"]["overrides"]["only_recent_date_range"] == "24months"
            assert subs_data["__preset__"]["overrides"]["only_recent_max_files"] == 300
            assert "output_options" in subs_data["__preset__"]


def mock_open_multiple_files():
    """Helper to mock opening multiple files for read/write."""
    from unittest.mock import mock_open
    return mock_open(read_data="test data")


class TestSubscriptionCleanup:
    """Test subscription cleanup functionality."""
    
    def test_cleanup_subscriptions_removes_existing_episodes(self, tmp_path):
        """Test that cleanup_subscriptions removes episodes that exist on disk."""
        # Create test media directory structure with .info.json file
        media_dir = tmp_path / "media"
        episode_dir = media_dir / "Strength" / "Rebecca Kennedy" / "S20E151 - 20250924 - 20 min Core Strength Benchmark with Rebecca Kennedy"
        episode_dir.mkdir(parents=True)
        
        # Create .info.json with class ID
        info_json = episode_dir / "S20E151 - 20250924 - 20 min Core Strength Benchmark with Rebecca Kennedy.info.json"
        info_json.write_text('{"id": "ebbc14101ce94f69905463fb3e3f7720"}')
        
        # Create .mp4 file
        mp4_file = episode_dir / "S20E151 - 20250924 - 20 min Core Strength Benchmark with Rebecca Kennedy.mp4"
        mp4_file.write_text("fake video content")
        
        # Create subscriptions file with the episode
        subs_file = tmp_path / "subscriptions.yaml"
        subs_data = {
            "Plex TV Show by Date": {
                "= Strength (20 min)": {
                    "20 min Core Strength Benchmark with Rebecca Kennedy": {
                        "download": "https://members.onepeloton.com/classes/player/ebbc14101ce94f69905463fb3e3f7720",
                        "overrides": {
                            "tv_show_directory": str(media_dir / "Strength" / "Rebecca Kennedy"),
                            "season_number": 20,
                            "episode_number": 152
                        }
                    },
                    "20 min Upper Body Strength with Callie Gullickson": {
                        "download": "https://members.onepeloton.com/classes/player/d0a2ff052ff94bbe9f0f668d68f48307",
                        "overrides": {
                            "tv_show_directory": str(media_dir / "Strength" / "Callie Gullickson"),
                            "season_number": 20,
                            "episode_number": 153
                        }
                    }
                }
            }
        }
        
        import yaml
        with open(subs_file, 'w', encoding='utf-8') as f:
            yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True)
        
        # Create FileManager and run cleanup
        file_manager = FileManager(
            media_dir=str(media_dir),
            subs_file=str(subs_file),
            validate_and_repair=False,
            episode_parsers=[
                "src.io.peloton.episodes_from_disk:EpisodesFromDisk",
                "src.io.peloton.episodes_from_subscriptions:EpisodesFromSubscriptions"
            ]
        )
        
        # Verify episode exists in subscriptions before cleanup
        with open(subs_file, 'r', encoding='utf-8') as f:
            before_cleanup = yaml.safe_load(f)
        
        strength_section = before_cleanup["Plex TV Show by Date"]["= Strength (20 min)"]
        assert "20 min Core Strength Benchmark with Rebecca Kennedy" in strength_section
        assert "20 min Upper Body Strength with Callie Gullickson" in strength_section
        
        # Run cleanup
        changes_made = file_manager.cleanup_subscriptions()
        assert changes_made is True
        
        # Verify episode was removed from subscriptions
        with open(subs_file, 'r', encoding='utf-8') as f:
            after_cleanup = yaml.safe_load(f)
        
        strength_section_after = after_cleanup["Plex TV Show by Date"]["= Strength (20 min)"]
        assert "20 min Core Strength Benchmark with Rebecca Kennedy" not in strength_section_after
        assert "20 min Upper Body Strength with Callie Gullickson" in strength_section_after  # Should still be there
        
    def test_cleanup_subscriptions_no_changes_when_no_duplicates(self, tmp_path):
        """Test that cleanup_subscriptions returns False when no duplicates exist."""
        # Create empty media directory
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        
        # Create subscriptions file with episodes
        subs_file = tmp_path / "subscriptions.yaml"
        subs_data = {
            "Plex TV Show by Date": {
                "= Strength (20 min)": {
                    "20 min Upper Body Strength with Callie Gullickson": {
                        "download": "https://members.onepeloton.com/classes/player/d0a2ff052ff94bbe9f0f668d68f48307",
                        "overrides": {
                            "tv_show_directory": str(media_dir / "Strength" / "Callie Gullickson"),
                            "season_number": 20,
                            "episode_number": 153
                        }
                    }
                }
            }
        }
        
        import yaml
        with open(subs_file, 'w', encoding='utf-8') as f:
            yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True)
        
        # Create FileManager and run cleanup
        file_manager = FileManager(
            media_dir=str(media_dir),
            subs_file=str(subs_file),
            validate_and_repair=False,
            episode_parsers=[
                "src.io.peloton.episodes_from_disk:EpisodesFromDisk",
                "src.io.peloton.episodes_from_subscriptions:EpisodesFromSubscriptions"
            ]
        )
        
        # Run cleanup
        changes_made = file_manager.cleanup_subscriptions()
        assert changes_made is False
        
        # Verify no changes were made
        with open(subs_file, 'r', encoding='utf-8') as f:
            after_cleanup = yaml.safe_load(f)
        
        assert after_cleanup == subs_data


class TestConflictResolution:
    """Test conflict resolution for episodes with same name but different class IDs."""
    
    def test_add_subscriptions_deconflicts_same_name_different_class_id(self, tmp_path):
        """Test that episodes with same name but different class IDs get deconflicted."""
        # Create initial subscriptions file with one episode
        subs_file = tmp_path / "subscriptions.yaml"
        initial_data = {
            "Plex TV Show by Date": {
                "= Cycling (20 min)": {
                    "20 min Pick-Me-Up Ride with Hannah Corbin": {
                        "download": "https://members.onepeloton.com/classes/player/2a58af81c3504644898c82fdf81dd040",
                        "overrides": {
                            "tv_show_directory": str(tmp_path / "media" / "Cycling" / "Hannah Corbin"),
                            "season_number": 20,
                            "episode_number": 138
                        }
                    }
                }
            }
        }
        
        import yaml
        with open(subs_file, 'w', encoding='utf-8') as f:
            yaml.dump(initial_data, f, sort_keys=False, allow_unicode=True)
        
        # Create FileManager
        file_manager = FileManager(
            media_dir=str(tmp_path / "media"),
            subs_file=str(subs_file),
            validate_and_repair=False,
            episode_parsers=["src.io.peloton.episodes_from_subscriptions:EpisodesFromSubscriptions"]
        )
        
        # Try to add the same episode with different class ID
        new_subscriptions = {
            "= Cycling (20 min)": {
                "20 min Pick-Me-Up Ride with Hannah Corbin": {
                    "download": "https://members.onepeloton.com/classes/player/97209d52427247b995645c70479a8e2d",
                    "overrides": {
                        "tv_show_directory": str(tmp_path / "media" / "Cycling" / "Hannah Corbin"),
                        "season_number": 20,
                        "episode_number": 145
                    }
                }
            }
        }
        
        # This should trigger conflict resolution
        success = file_manager.add_new_subscriptions(new_subscriptions)
        assert success is True
        
        # Read the result
        with open(subs_file, 'r', encoding='utf-8') as f:
            result_data = yaml.safe_load(f)
        
        cycling_section = result_data["Plex TV Show by Date"]["= Cycling (20 min)"]
        
        # Should have two episodes with different names
        assert len(cycling_section) == 2
        
        episode_titles = list(cycling_section.keys())
        
        # Original episode should still exist unchanged
        assert "20 min Pick-Me-Up Ride with Hannah Corbin" in episode_titles
        
        # New episode should have class ID suffix
        deconflicted_title = None
        for title in episode_titles:
            if "97209d5" in title:
                deconflicted_title = title
                break
        
        assert deconflicted_title is not None
        assert deconflicted_title == "20 min Pick-Me-Up Ride with Hannah Corbin 97209d5"
        
        # Verify class IDs are correct
        original_episode = cycling_section["20 min Pick-Me-Up Ride with Hannah Corbin"]
        deconflicted_episode = cycling_section[deconflicted_title]
        
        assert "2a58af81c3504644898c82fdf81dd040" in original_episode["download"]
        assert "97209d52427247b995645c70479a8e2d" in deconflicted_episode["download"]
    
    def test_add_subscriptions_no_conflict_same_class_id(self, tmp_path):
        """Test that episodes with same name and same class ID don't create conflicts."""
        # Create initial subscriptions file with one episode
        subs_file = tmp_path / "subscriptions.yaml"
        initial_data = {
            "Plex TV Show by Date": {
                "= Cycling (20 min)": {
                    "20 min Pick-Me-Up Ride with Hannah Corbin": {
                        "download": "https://members.onepeloton.com/classes/player/97209d52427247b995645c70479a8e2d",
                        "overrides": {
                            "tv_show_directory": str(tmp_path / "media" / "Cycling" / "Hannah Corbin"),
                            "season_number": 20,
                            "episode_number": 138
                        }
                    }
                }
            }
        }
        
        import yaml
        with open(subs_file, 'w', encoding='utf-8') as f:
            yaml.dump(initial_data, f, sort_keys=False, allow_unicode=True)
        
        # Create FileManager
        file_manager = FileManager(
            media_dir=str(tmp_path / "media"),
            subs_file=str(subs_file),
            validate_and_repair=False,
            episode_parsers=["src.io.peloton.episodes_from_subscriptions:EpisodesFromSubscriptions"]
        )
        
        # Try to add the same episode with same class ID (should just overwrite)
        new_subscriptions = {
            "= Cycling (20 min)": {
                "20 min Pick-Me-Up Ride with Hannah Corbin": {
                    "download": "https://members.onepeloton.com/classes/player/97209d52427247b995645c70479a8e2d",
                    "overrides": {
                        "tv_show_directory": str(tmp_path / "media" / "Cycling" / "Hannah Corbin"),
                        "season_number": 20,
                        "episode_number": 145  # Different episode number
                    }
                }
            }
        }
        
        success = file_manager.add_new_subscriptions(new_subscriptions)
        assert success is True
        
        # Read the result
        with open(subs_file, 'r', encoding='utf-8') as f:
            result_data = yaml.safe_load(f)
        
        cycling_section = result_data["Plex TV Show by Date"]["= Cycling (20 min)"]
        
        # Should have only one episode (overwritten)
        assert len(cycling_section) == 1
        assert "20 min Pick-Me-Up Ride with Hannah Corbin" in cycling_section
        
        # Episode number should be updated
        episode = cycling_section["20 min Pick-Me-Up Ride with Hannah Corbin"]
        assert episode["overrides"]["episode_number"] == 145
