"""Tests for episode parsing functionality."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ytdl_sub_config_manager.io.file_manager import FileManager
from ytdl_sub_config_manager.io.filesystem_parser import FilesystemEpisodeParser
from ytdl_sub_config_manager.io.subscriptions_parser import SubscriptionsEpisodeParser
from ytdl_sub_config_manager.io.episode_parser import EpisodeMerger
from ytdl_sub_config_manager.core.models import Activity, ActivityData


class TestFilesystemEpisodeParser:
    """Test filesystem episode parsing."""
    
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
        parser = FilesystemEpisodeParser(temp_media_dir)
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
        parser = FilesystemEpisodeParser(temp_media_dir)
        class_ids = parser.find_existing_class_ids()
        
        # Should find the test123 ID from all the created files
        assert "test123" in class_ids
        assert len(class_ids) >= 1
    
    def test_nonexistent_directory(self):
        """Test behavior with nonexistent media directory."""
        parser = FilesystemEpisodeParser("/nonexistent/path")
        results = parser.parse_episodes()
        
        assert results == {}
    
    def test_activity_mapping(self, temp_media_dir):
        """Test activity name mapping from directory names."""
        parser = FilesystemEpisodeParser(temp_media_dir)
        
        # Test direct mapping
        assert parser._map_activity_name("cycling") == Activity.CYCLING
        assert parser._map_activity_name("yoga") == Activity.YOGA
        assert parser._map_activity_name("strength") == Activity.STRENGTH
        
        # Test special mappings
        assert parser._map_activity_name("tread bootcamp") == Activity.BOOTCAMP
        assert parser._map_activity_name("bike bootcamp") == Activity.BIKE_BOOTCAMP
        assert parser._map_activity_name("row bootcamp") == Activity.ROW_BOOTCAMP
        
        # Test invalid mapping
        assert parser._map_activity_name("invalid_activity") is None


class TestSubscriptionsEpisodeParser:
    """Test subscriptions YAML episode parsing."""
    
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
        parser = SubscriptionsEpisodeParser(sample_subscriptions_yaml)
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
        parser = SubscriptionsEpisodeParser(sample_subscriptions_yaml)
        class_ids = parser.find_subscription_class_ids()
        
        expected_ids = {"abc123", "def456", "ghi789"}
        assert class_ids == expected_ids
    
    def test_nonexistent_file(self):
        """Test behavior with nonexistent subscriptions file."""
        parser = SubscriptionsEpisodeParser("/nonexistent/file.yaml")
        results = parser.parse_episodes()
        
        assert results == {}
    
    def test_extract_activity_from_directory(self, sample_subscriptions_yaml):
        """Test activity extraction from tv_show_directory."""
        parser = SubscriptionsEpisodeParser(sample_subscriptions_yaml)
        
        # Test valid paths
        assert parser._extract_activity_from_directory("/media/peloton/Cycling/Hannah") == Activity.CYCLING
        assert parser._extract_activity_from_directory("/media/peloton/Yoga/Aditi") == Activity.YOGA
        assert parser._extract_activity_from_directory("/media/peloton/Strength/Andy") == Activity.STRENGTH
        
        # Test invalid paths
        assert parser._extract_activity_from_directory("/invalid/path") is None
        assert parser._extract_activity_from_directory("") is None


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
        
        file_manager = FileManager(media_dir, subs_file)
        
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
    """Integration test using the real subscriptions.example.yaml file."""
    # This test uses the actual example file in the project
    subs_file = "subscriptions.example.yaml"
    
    if not Path(subs_file).exists():
        pytest.skip("subscriptions.example.yaml not found")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create minimal media structure
        media_dir = Path(temp_dir) / "media"
        media_dir.mkdir()
        
        file_manager = FileManager(str(media_dir), subs_file)
        
        # Should be able to parse the example file
        merged_data = file_manager.get_merged_episode_data()
        assert len(merged_data) > 0
        
        # Should find class IDs from the example file
        class_ids = file_manager.find_all_existing_class_ids()
        assert len(class_ids) > 0
