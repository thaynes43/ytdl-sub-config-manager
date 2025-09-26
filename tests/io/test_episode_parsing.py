"""Tests for episode parsing functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.io.file_manager import FileManager
from src.io.peloton.episodes_from_disk import EpisodesFromDisk
from src.io.peloton.episodes_from_subscriptions import EpisodesFromSubscriptions
from src.io.episode_parser import EpisodeMerger
from src.core.models import Activity, ActivityData


class TestEpisodesFromDisk:
    """Test episodes from disk parsing."""
    
    @pytest.fixture
    def temp_media_dir(self):
        """Create a temporary media directory with test structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media" / "peloton"
            
            # Create test directories with S{season}E{episode} pattern
            test_dirs = [
                "Cycling/Hannah Frankson/S20E001 - 2024-01-15 - 20 min Pop Ride",
                "Cycling/Hannah Frankson/S20E002 - 2024-01-16 - 20 min Rock Ride", 
                "Cycling/Hannah Frankson/S30E001 - 2024-01-15 - 30 min HIIT Ride",
                "Cycling/Sam Yo/S20E001 - 2024-01-15 - 20 min Low Impact",
                "Cycling/Sam Yo/S45E001 - 2024-01-15 - 45 min Power Zone",
                "Yoga/Aditi Shah/S30E001 - 2024-01-15 - 30 min Flow",
                "Yoga/Aditi Shah/S45E001 - 2024-01-15 - 45 min Power Flow",
                "Strength/Andy Speer/S10E001 - 2024-01-15 - 10 min Core",
                "Strength/Andy Speer/S20E001 - 2024-01-15 - 20 min Upper Body",
            ]
            
            for dir_path in test_dirs:
                full_path = media_dir / dir_path
                full_path.mkdir(parents=True, exist_ok=True)
                
                # Create a dummy .info.json file
                info_file = full_path / f"{full_path.name}.info.json"
                info_file.write_text('{"id": "test123"}')
            
            yield str(media_dir.parent)
    
    def test_parse_episodes_from_filesystem(self, temp_media_dir):
        """Test parsing episodes from filesystem structure."""
        parser = EpisodesFromDisk(temp_media_dir)
        results = parser.parse_episodes()
        
        # Should find 3 activities
        assert len(results) == 3
        assert Activity.CYCLING in results
        assert Activity.YOGA in results
        assert Activity.STRENGTH in results
        
        # Check cycling episodes
        cycling_data = results[Activity.CYCLING]
        assert cycling_data.max_episode[20] == 2  # Hannah has 2 episodes, Sam has 1
        assert cycling_data.max_episode[30] == 1  # Hannah has 1
        assert cycling_data.max_episode[45] == 1  # Sam has 1
        
        # Check yoga episodes
        yoga_data = results[Activity.YOGA]
        assert yoga_data.max_episode[30] == 1
        assert yoga_data.max_episode[45] == 1
        
        # Check strength episodes
        strength_data = results[Activity.STRENGTH]
        assert strength_data.max_episode[10] == 1
        assert strength_data.max_episode[20] == 1
    
    def test_find_existing_class_ids(self, temp_media_dir):
        """Test finding class IDs from .info.json files."""
        parser = EpisodesFromDisk(temp_media_dir)
        class_ids = parser.find_existing_class_ids()
        
        # Should find the test123 ID from all the created files
        assert "test123" in class_ids
        assert len(class_ids) >= 1
    
    def test_nonexistent_directory(self):
        """Test behavior with nonexistent media directory."""
        parser = EpisodesFromDisk("/nonexistent/path")
        results = parser.parse_episodes()
        
        assert results == {}
    
    def test_activity_mapping(self, temp_media_dir):
        """Test activity name mapping from directory names."""
        parser = EpisodesFromDisk(temp_media_dir)
        
        # Test activity mapping via strategy (moved from parser)
        from src.io.peloton.activity_based_path_strategy import ActivityBasedPathStrategy
        strategy = ActivityBasedPathStrategy()
        
        # Test direct mapping
        assert strategy._map_activity_name("cycling") == Activity.CYCLING
        assert strategy._map_activity_name("yoga") == Activity.YOGA
        assert strategy._map_activity_name("strength") == Activity.STRENGTH
        
        # Test special mappings
        assert strategy._map_activity_name("tread bootcamp") == Activity.BOOTCAMP
        assert strategy._map_activity_name("bike bootcamp") == Activity.BIKE_BOOTCAMP
        assert strategy._map_activity_name("row bootcamp") == Activity.ROW_BOOTCAMP
        
        # Test invalid mapping
        assert strategy._map_activity_name("invalid_activity") is None
    
    def test_50_50_folder_handling(self):
        """Test handling of problematic 50/50 folders from legacy implementation.
        
        The 50/50 pattern creates extra directory levels that break the expected structure:
        Expected: /media/peloton/{Activity}/{Instructor}/S{season}E{episode}
        Problematic: /media/peloton/Bootcamp 50/50/{Instructor}/S{season}E{episode}
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media" / "peloton"
            
            # Create problematic directories with 50/50 pattern that creates extra subdirectories
            problematic_structures = [
                # This represents "Bootcamp: 50/50" -> creates extra directory level
                "Bootcamp 50/50/Instructor/S30E001 - 2024-01-15 - 30 min Bootcamp",
                # Regular 50-50 pattern (replacement fix) - still problematic activity name
                "Bootcamp 50-50/Instructor/S30E002 - 2024-01-16 - 30 min Mixed",
                # Other bootcamp 50 patterns
                "Tread Bootcamp 50/Instructor/S30E003 - 2024-01-17 - Bootcamp 50 min",
            ]
            
            # Create valid directories that should be processed
            valid_dirs = [
                "Cycling/Hannah Frankson/S20E001 - 2024-01-15 - 20 min Pop Ride",
                "Strength/Andy Speer/S10E001 - 2024-01-15 - 10 min Core",
                # Valid bootcamp without 50/50 issues
                "Bootcamp/Jess Sims/S30E001 - 2024-01-15 - 30 min Regular Bootcamp",
            ]
            
            # Create all directories
            all_dirs = problematic_structures + valid_dirs
            for dir_path in all_dirs:
                full_path = media_dir / dir_path
                full_path.mkdir(parents=True, exist_ok=True)
                
                # Create dummy .info.json files
                info_file = full_path / f"{full_path.name}.info.json"
                info_file.write_text('{"id": "test123"}')
            
            parser = EpisodesFromDisk(str(media_dir.parent))
            results = parser.parse_episodes()
            
            # The 50/50 structures should be skipped due to:
            # 1. Wrong directory depth (extra level breaks parsing)
            # 2. Activity name filtering (50/50 patterns are filtered out)
            
            # Should find valid activities (Cycling, Strength, valid Bootcamp)
            # Should NOT find any episodes from problematic 50/50 structures
            assert len(results) == 3
            assert Activity.CYCLING in results
            assert Activity.STRENGTH in results
            assert Activity.BOOTCAMP in results
            
            # Verify the valid episodes were parsed correctly
            cycling_data = results[Activity.CYCLING]
            assert cycling_data.max_episode[20] == 1
            
            strength_data = results[Activity.STRENGTH]
            assert strength_data.max_episode[10] == 1
            
        # Should only have the valid bootcamp episode, not the 50/50 ones
        bootcamp_data = results[Activity.BOOTCAMP]
        assert bootcamp_data.max_episode[30] == 1  # Only the valid one
    
    def test_50_slash_50_directory_structure_issue(self):
        """Test the specific 50/50 directory structure issue from old implementation.
        
        This test demonstrates the exact problem: when a class title contains "50/50",
        it creates an extra directory level that breaks the expected parsing structure.
        
        Example problematic structure:
        /media/peloton/Bootcamp 50/50/Instructor/S30E001 - title
        
        Instead of the expected:
        /media/peloton/Bootcamp/Instructor/S30E001 - title
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Simulate the actual problematic structure that would be created
            # when ytdl-sub downloads a class with "50/50" in the title
            problematic_path = (
                temp_path / "media" / "peloton" / 
                "Bootcamp 50" / "50" /  # This is what happens with "50/50" in name
                "Jess Sims" / 
                "S30E001 - 2024-01-15 - 30 min Full Body Bootcamp"
            )
            problematic_path.mkdir(parents=True)
            
            # Create info file
            info_file = problematic_path / f"{problematic_path.name}.info.json"
            info_file.write_text('{"id": "problematic123"}')
            
            # Also create a normal bootcamp for comparison
            normal_path = (
                temp_path / "media" / "peloton" /
                "Bootcamp" /
                "Jess Sims" /
                "S30E002 - 2024-01-16 - 30 min Upper Body Bootcamp"
            )
            normal_path.mkdir(parents=True)
            normal_info = normal_path / f"{normal_path.name}.info.json"
            normal_info.write_text('{"id": "normal123"}')
            
            parser = EpisodesFromDisk(str(temp_path))
            results = parser.parse_episodes()
            
            # The problematic structure should be ignored because:
            # 1. The activity name "Bootcamp 50" doesn't match our Activity enum
            # 2. The "50/50" pattern is explicitly filtered out
            # 3. The directory structure is wrong (too deep)
            
            # Should only find the normal bootcamp
            assert len(results) == 1
            assert Activity.BOOTCAMP in results
            
            bootcamp_data = results[Activity.BOOTCAMP]
            assert bootcamp_data.max_episode[30] == 2  # Only the normal episode
            
            # Note: find_existing_class_ids() scans ALL .info.json files regardless of structure
            # This is correct behavior - we want to know about all existing downloads
            # The episode parsing logic is what filters out problematic structures
            class_ids = parser.find_existing_class_ids()
            assert "normal123" in class_ids
            assert "problematic123" in class_ids  # Found by file scan, but ignored by episode parsing
    
    def test_activity_mapping_edge_cases(self, temp_media_dir):
        """Test edge cases in activity name mapping."""
        parser = EpisodesFromDisk(temp_media_dir)
        
        # Test activity mapping via strategy (moved from parser)
        from src.io.peloton.activity_based_path_strategy import ActivityBasedPathStrategy
        strategy = ActivityBasedPathStrategy()
        
        # Test 50/50 and 50-50 patterns - strategy now infers correct activity from corrupted patterns
        assert strategy._map_activity_name("bootcamp 50/50") == Activity.BOOTCAMP  # Strategy infers from corrupted pattern
        assert strategy._map_activity_name("bootcamp 50-50") == Activity.BOOTCAMP  # Strategy infers from corrupted pattern
        assert strategy._map_activity_name("50/50 bootcamp") == Activity.BOOTCAMP  # Strategy infers from corrupted pattern
        assert strategy._map_activity_name("50-50 bootcamp") == Activity.BOOTCAMP  # Strategy infers from corrupted pattern
        assert strategy._map_activity_name("tread bootcamp 50") == Activity.BOOTCAMP  # Strategy infers correct activity
        assert strategy._map_activity_name("bootcamp: 50") is None  # Colon pattern not handled
        
        # Test case variations (should work since input is already lowercased in parse logic)
        assert strategy._map_activity_name("cycling") == Activity.CYCLING
        assert strategy._map_activity_name("yoga") == Activity.YOGA
        assert strategy._map_activity_name("tread bootcamp") == Activity.BOOTCAMP


class TestEpisodesFromSubscriptions:
    """Test episodes from subscriptions parsing."""
    
    @pytest.fixture
    def sample_subscriptions_yaml(self):
        """Create a temporary subscriptions YAML file."""
        yaml_content = """Plex TV Show by Date:
  = Cycling (20 min):
    20 min Pop Ride with Hannah Frankson:
      download: https://members.onepeloton.com/classes/player/abc123
      overrides:
        tv_show_directory: /media/peloton/Cycling/Hannah Frankson
        season_number: 20
        episode_number: 10
    20 min Rock Ride with Sam Yo:
      download: https://members.onepeloton.com/classes/player/def456
      overrides:
        tv_show_directory: /media/peloton/Cycling/Sam Yo
        season_number: 20
        episode_number: 5
  = Yoga (30 min):
    30 min Flow with Aditi Shah:
      download: https://members.onepeloton.com/classes/player/ghi789
      overrides:
        tv_show_directory: /media/peloton/Yoga/Aditi Shah
        season_number: 30
        episode_number: 15
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()  # Ensure content is written
            temp_file = f.name
        
        try:
            yield temp_file
        finally:
            # Cleanup
            Path(temp_file).unlink(missing_ok=True)
    
    def test_parse_episodes_from_subscriptions(self, sample_subscriptions_yaml):
        """Test parsing episodes from subscriptions YAML."""
        parser = EpisodesFromSubscriptions(sample_subscriptions_yaml)
        results = parser.parse_episodes()
        
        # Should find 2 activities
        assert len(results) == 2
        assert Activity.CYCLING in results
        assert Activity.YOGA in results
        
        # Check cycling episodes
        cycling_data = results[Activity.CYCLING]
        assert cycling_data.max_episode[20] == 10  # Max between Hannah(10) and Sam(5)
        
        # Check yoga episodes
        yoga_data = results[Activity.YOGA]
        assert yoga_data.max_episode[30] == 15
    
    def test_find_subscription_class_ids(self, sample_subscriptions_yaml):
        """Test finding class IDs from subscription URLs."""
        parser = EpisodesFromSubscriptions(sample_subscriptions_yaml)
        class_ids = parser.find_subscription_class_ids()
        
        expected_ids = {"abc123", "def456", "ghi789"}
        assert class_ids == expected_ids
    
    def test_nonexistent_file(self):
        """Test behavior with nonexistent subscriptions file."""
        parser = EpisodesFromSubscriptions("/nonexistent/file.yaml")
        results = parser.parse_episodes()
        
        assert results == {}
    
    def test_remove_existing_classes_success(self, tmp_path):
        """Test removing existing class IDs from subscriptions file."""
        subs_file = tmp_path / "subscriptions.yaml"
        
        # Create a subscriptions file with multiple episodes
        subs_data = {
            "Plex TV Show by Date": {
                "= Cycling (20 min)": {
                    "20 min Ride with Hannah": {
                        "download": "https://members.onepeloton.com/classes/player/abc123",
                        "overrides": {"season_number": 20, "episode_number": 1}
                    },
                    "20 min Ride with Sam": {
                        "download": "https://members.onepeloton.com/classes/player/def456",
                        "overrides": {"season_number": 20, "episode_number": 2}
                    }
                },
                "= Yoga (30 min)": {
                    "30 min Flow with Aditi": {
                        "download": "https://members.onepeloton.com/classes/player/ghi789",
                        "overrides": {"season_number": 30, "episode_number": 1}
                    }
                }
            }
        }
        
        import yaml
        with open(subs_file, 'w', encoding='utf-8') as f:
            yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True)
        
        parser = EpisodesFromSubscriptions(str(subs_file))
        
        # Remove one class ID
        existing_class_ids = {"abc123"}
        result = parser.remove_existing_classes(existing_class_ids)
        
        assert result is True
        
        # Verify the file was modified
        with open(subs_file, 'r', encoding='utf-8') as f:
            modified_data = yaml.safe_load(f)
        
        # Check that abc123 episode was removed
        cycling_section = modified_data["Plex TV Show by Date"]["= Cycling (20 min)"]
        assert "20 min Ride with Hannah" not in cycling_section
        assert "20 min Ride with Sam" in cycling_section  # Should still be there
        
        # Check that other sections are unchanged
        assert "= Yoga (30 min)" in modified_data["Plex TV Show by Date"]
        yoga_section = modified_data["Plex TV Show by Date"]["= Yoga (30 min)"]
        assert "30 min Flow with Aditi" in yoga_section
    
    def test_remove_existing_classes_removes_empty_duration_group(self, tmp_path):
        """Test that removing all episodes from a duration group removes the group entirely."""
        subs_file = tmp_path / "subscriptions.yaml"
        
        # Create a subscriptions file with one episode in a duration group
        subs_data = {
            "Plex TV Show by Date": {
                "= Cycling (20 min)": {
                    "20 min Ride with Hannah": {
                        "download": "https://members.onepeloton.com/classes/player/abc123",
                        "overrides": {"season_number": 20, "episode_number": 1}
                    }
                },
                "= Yoga (30 min)": {
                    "30 min Flow with Aditi": {
                        "download": "https://members.onepeloton.com/classes/player/ghi789",
                        "overrides": {"season_number": 30, "episode_number": 1}
                    }
                }
            }
        }
        
        import yaml
        with open(subs_file, 'w', encoding='utf-8') as f:
            yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True)
        
        parser = EpisodesFromSubscriptions(str(subs_file))
        
        # Remove the only class ID from the cycling group
        existing_class_ids = {"abc123"}
        result = parser.remove_existing_classes(existing_class_ids)
        
        assert result is True
        
        # Verify the file was modified
        with open(subs_file, 'r', encoding='utf-8') as f:
            modified_data = yaml.safe_load(f)
        
        # Check that the entire cycling duration group was removed
        assert "= Cycling (20 min)" not in modified_data["Plex TV Show by Date"]
        
        # Check that yoga section is still there
        assert "= Yoga (30 min)" in modified_data["Plex TV Show by Date"]
        yoga_section = modified_data["Plex TV Show by Date"]["= Yoga (30 min)"]
        assert "30 min Flow with Aditi" in yoga_section
    
    def test_remove_existing_classes_no_matches(self, tmp_path):
        """Test removing class IDs that don't exist in the subscriptions file."""
        subs_file = tmp_path / "subscriptions.yaml"
        
        # Create a subscriptions file
        subs_data = {
            "Plex TV Show by Date": {
                "= Cycling (20 min)": {
                    "20 min Ride with Hannah": {
                        "download": "https://members.onepeloton.com/classes/player/abc123",
                        "overrides": {"season_number": 20, "episode_number": 1}
                    }
                }
            }
        }
        
        import yaml
        with open(subs_file, 'w', encoding='utf-8') as f:
            yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True)
        
        parser = EpisodesFromSubscriptions(str(subs_file))
        
        # Try to remove a class ID that doesn't exist
        existing_class_ids = {"nonexistent123"}
        result = parser.remove_existing_classes(existing_class_ids)
        
        assert result is False  # No changes made
        
        # Verify the file was not modified
        with open(subs_file, 'r', encoding='utf-8') as f:
            modified_data = yaml.safe_load(f)
        
        # Should be identical to original
        assert modified_data == subs_data
    
    def test_remove_existing_classes_empty_class_ids(self, tmp_path):
        """Test removing with empty class IDs set."""
        subs_file = tmp_path / "subscriptions.yaml"
        
        # Create a subscriptions file
        subs_data = {
            "Plex TV Show by Date": {
                "= Cycling (20 min)": {
                    "20 min Ride with Hannah": {
                        "download": "https://members.onepeloton.com/classes/player/abc123",
                        "overrides": {"season_number": 20, "episode_number": 1}
                    }
                }
            }
        }
        
        import yaml
        with open(subs_file, 'w', encoding='utf-8') as f:
            yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True)
        
        parser = EpisodesFromSubscriptions(str(subs_file))
        
        # Try to remove with empty set
        existing_class_ids = set()
        result = parser.remove_existing_classes(existing_class_ids)
        
        assert result is False  # No changes made
        
        # Verify the file was not modified
        with open(subs_file, 'r', encoding='utf-8') as f:
            modified_data = yaml.safe_load(f)
        
        # Should be identical to original
        assert modified_data == subs_data
    
    def test_remove_existing_classes_nonexistent_file(self):
        """Test removing from nonexistent subscriptions file."""
        parser = EpisodesFromSubscriptions("/nonexistent/file.yaml")
        
        existing_class_ids = {"abc123"}
        result = parser.remove_existing_classes(existing_class_ids)
        
        assert result is False
    
    def test_remove_existing_classes_invalid_yaml(self, tmp_path):
        """Test removing from invalid YAML file."""
        subs_file = tmp_path / "subscriptions.yaml"
        
        # Create invalid YAML
        with open(subs_file, 'w', encoding='utf-8') as f:
            f.write("invalid: yaml: content: [")
        
        parser = EpisodesFromSubscriptions(str(subs_file))
        
        existing_class_ids = {"abc123"}
        result = parser.remove_existing_classes(existing_class_ids)
        
        assert result is False
    
    def test_remove_existing_classes_empty_file(self, tmp_path):
        """Test removing from empty subscriptions file."""
        subs_file = tmp_path / "subscriptions.yaml"
        subs_file.touch()  # Create empty file
        
        parser = EpisodesFromSubscriptions(str(subs_file))
        
        existing_class_ids = {"abc123"}
        result = parser.remove_existing_classes(existing_class_ids)
        
        assert result is False
    
    # test_extract_activity_from_directory removed - internal implementation moved to strategy


class TestEpisodeMerger:
    """Test episode data merging logic."""
    
    def test_merge_sources(self):
        """Test merging episode data from multiple sources."""
        # Create test data
        source1 = {
            Activity.CYCLING: ActivityData(Activity.CYCLING),
            Activity.YOGA: ActivityData(Activity.YOGA),
        }
        source1[Activity.CYCLING].update(20, 5)
        source1[Activity.CYCLING].update(30, 3)
        source1[Activity.YOGA].update(30, 10)
        
        source2 = {
            Activity.CYCLING: ActivityData(Activity.CYCLING),
            Activity.STRENGTH: ActivityData(Activity.STRENGTH),
        }
        source2[Activity.CYCLING].update(20, 8)  # Higher than source1
        source2[Activity.CYCLING].update(45, 2)  # New season
        source2[Activity.STRENGTH].update(10, 5)
        
        merger = EpisodeMerger()
        merged = merger.merge_sources(source1, source2)
        
        # Check merged results
        assert len(merged) == 3  # CYCLING, YOGA, STRENGTH
        
        # CYCLING should have max from both sources
        cycling_data = merged[Activity.CYCLING]
        assert cycling_data.max_episode[20] == 8  # Max of 5 and 8
        assert cycling_data.max_episode[30] == 3  # Only in source1
        assert cycling_data.max_episode[45] == 2  # Only in source2
        
        # YOGA should be unchanged from source1
        yoga_data = merged[Activity.YOGA]
        assert yoga_data.max_episode[30] == 10
        
        # STRENGTH should be from source2
        strength_data = merged[Activity.STRENGTH]
        assert strength_data.max_episode[10] == 5
    
    def test_get_next_episode_number(self):
        """Test getting next episode number."""
        # Create test data
        merged_data = {
            Activity.CYCLING: ActivityData(Activity.CYCLING),
        }
        merged_data[Activity.CYCLING].update(20, 5)
        merged_data[Activity.CYCLING].update(30, 3)
        
        merger = EpisodeMerger()
        
        # Test existing seasons
        assert merger.get_next_episode_number(merged_data, Activity.CYCLING, 20) == 6
        assert merger.get_next_episode_number(merged_data, Activity.CYCLING, 30) == 4
        
        # Test new season
        assert merger.get_next_episode_number(merged_data, Activity.CYCLING, 45) == 1
        
        # Test new activity
        assert merger.get_next_episode_number(merged_data, Activity.YOGA, 30) == 1


class TestFileManager:
    """Test the complete file manager integration."""
    
    @pytest.fixture
    def temp_setup(self):
        """Set up temporary media directory and subscriptions file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create media structure
            media_dir = temp_path / "media" / "peloton"
            test_dirs = [
                "Cycling/Hannah Frankson/S20E001 - 2024-01-15 - 20 min Pop Ride",
                "Yoga/Aditi Shah/S30E001 - 2024-01-15 - 30 min Flow",
            ]
            
            for dir_path in test_dirs:
                full_path = media_dir / dir_path
                full_path.mkdir(parents=True, exist_ok=True)
                info_file = full_path / f"{full_path.name}.info.json"
                info_file.write_text('{"id": "filesystem123"}')
            
            # Create subscriptions file
            subs_file = temp_path / "subscriptions.yaml"
            subs_content = """Plex TV Show by Date:
  = Cycling (20 min):
    20 min Test Ride:
      download: https://members.onepeloton.com/classes/player/subs456
      overrides:
        tv_show_directory: /media/peloton/Cycling/Test Instructor
        season_number: 20
        episode_number: 10
"""
            subs_file.write_text(subs_content)
            
            yield str(media_dir.parent), str(subs_file)
    
    def test_file_manager_integration(self, temp_setup):
        """Test complete file manager functionality."""
        media_dir, subs_file = temp_setup
        
        file_manager = FileManager(
            media_dir=media_dir, 
            subs_file=subs_file,
            validate_and_repair=False,  # Skip validation for this integration test
            episode_parsers=[
                "src.io.peloton.episodes_from_disk:EpisodesFromDisk",
                "src.io.peloton.episodes_from_subscriptions:EpisodesFromSubscriptions"
            ]
        )
        
        # Test validation
        assert file_manager.validate_directories() is True
        
        # Test merged episode data
        merged_data = file_manager.get_merged_episode_data()
        assert Activity.CYCLING in merged_data
        assert Activity.YOGA in merged_data
        
        # Cycling should have max episode from subscriptions (10 > 1)
        cycling_data = merged_data[Activity.CYCLING]
        assert cycling_data.max_episode[20] == 10
        
        # Test next episode calculation
        next_cycling = file_manager.get_next_episode_number(Activity.CYCLING, 20)
        assert next_cycling == 11  # 10 + 1
        
        next_yoga = file_manager.get_next_episode_number(Activity.YOGA, 30)
        assert next_yoga == 2  # 1 + 1
        
        # Test class ID detection
        all_ids = file_manager.find_all_existing_class_ids()
        assert "filesystem123" in all_ids
        assert "subs456" in all_ids
        assert len(all_ids) >= 2


def test_integration_with_real_example():
    """Integration test using the real subscriptions file."""
    # This test uses the actual subscriptions file in the project
    # Try multiple possible subscription files
    possible_files = ["subscriptions.example.yaml", "subscriptions.yaml", "subscriptions.test.yaml"]
    subs_file = None
    
    for file_path in possible_files:
        if Path(file_path).exists():
            subs_file = file_path
            break
    
    if subs_file is None:
        pytest.skip("No subscriptions file found (tried: {})".format(", ".join(possible_files)))
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal media structure
        media_dir = Path(temp_dir) / "media"
        media_dir.mkdir()
        
        file_manager = FileManager(
            media_dir=str(media_dir), 
            subs_file=subs_file,
            validate_and_repair=False,  # Skip validation for this test
            episode_parsers=[
                "src.io.peloton.episodes_from_disk:EpisodesFromDisk",
                "src.io.peloton.episodes_from_subscriptions:EpisodesFromSubscriptions"
            ]
        )
        
        # Should be able to parse the example file
        merged_data = file_manager.get_merged_episode_data()
        assert len(merged_data) > 0
        
        # Should find class IDs from the example file
        class_ids = file_manager.find_all_existing_class_ids()
        assert len(class_ids) > 0
