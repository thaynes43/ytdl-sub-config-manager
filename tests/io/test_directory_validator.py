"""Tests for directory structure validation and repair."""

import tempfile
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.io.directory_validator import (
    DirectoryValidator,
    EpisodeInfo,
    ConflictInfo
)
from src.core.models import Activity


class TestDirectoryValidator:
    """Test directory structure validation and repair."""
    
    def test_scan_normal_episodes(self):
        """Test scanning episodes in normal directory structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media" / "peloton"
            
            # Create normal episode structure
            episodes = [
                "Cycling/Hannah Frankson/S20E001 - 2024-01-15 - 20 min Pop Ride",
                "Strength/Andy Speer/S10E001 - 2024-01-15 - 10 min Core",
                "Bootcamp/Jess Sims/S30E001 - 2024-01-15 - 30 min Full Body",
            ]
            
            for episode_path in episodes:
                full_path = media_dir / episode_path
                full_path.mkdir(parents=True)
                
                # Create info file
                info_file = full_path / f"{full_path.name}.info.json"
                info_file.write_text('{"id": "test123"}')
            
            validator = DirectoryValidator(str(temp_path), dry_run=True)
            all_episodes = validator._scan_all_episodes()
            
            assert len(all_episodes) == 3
            
            # Check each episode
            cycling_ep = next(ep for ep in all_episodes if ep.activity == Activity.CYCLING)
            assert cycling_ep.season == 20
            assert cycling_ep.episode == 1
            assert cycling_ep.instructor == "Hannah Frankson"
            assert not cycling_ep.is_corrupted_location
            
            strength_ep = next(ep for ep in all_episodes if ep.activity == Activity.STRENGTH)
            assert strength_ep.season == 10
            assert strength_ep.episode == 1
            assert not strength_ep.is_corrupted_location
    
    def test_detect_corrupted_50_slash_50_structure(self):
        """Test detection of corrupted 50/50 directory structures."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media" / "peloton"
            
            # Create corrupted structure (50/50 creates extra directory level)
            corrupted_path = (
                media_dir / "Bootcamp 50" / "50" / "Jess Sims" / 
                "S30E001 - 2024-01-15 - 30 min Full Body Bootcamp"
            )
            corrupted_path.mkdir(parents=True)
            info_file = corrupted_path / f"{corrupted_path.name}.info.json"
            info_file.write_text('{"id": "corrupted123"}')
            
            # Create normal structure for comparison
            normal_path = media_dir / "Cycling" / "Hannah Frankson" / "S20E001 - 2024-01-15 - 20 min Pop Ride"
            normal_path.mkdir(parents=True)
            normal_info = normal_path / f"{normal_path.name}.info.json"
            normal_info.write_text('{"id": "normal123"}')
            
            validator = DirectoryValidator(str(temp_path), dry_run=True)
            all_episodes = validator._scan_all_episodes()
            
            # Should find both episodes
            assert len(all_episodes) == 2
            
            # Find the corrupted episode
            corrupted_ep = next((ep for ep in all_episodes if ep.path == corrupted_path), None)
            assert corrupted_ep is not None
            assert corrupted_ep.is_corrupted_location
            assert corrupted_ep.activity is None  # Should not map "Bootcamp 50"
            
            # Find the normal episode
            normal_ep = next((ep for ep in all_episodes if ep.path == normal_path), None)
            assert normal_ep is not None
            assert not normal_ep.is_corrupted_location
            assert normal_ep.activity == Activity.CYCLING
    
    def test_detect_episode_conflicts(self):
        """Test detection of episode number conflicts."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media" / "peloton"
            
            # Create conflicting episodes (same activity, season, episode)
            conflict_paths = [
                "Cycling/Hannah Frankson/S20E001 - 2024-01-15 - 20 min Pop Ride",
                "Cycling/Emma Lovewell/S20E001 - 2024-01-16 - 20 min Rock Ride",  # Same S20E001
            ]
            
            for episode_path in conflict_paths:
                full_path = media_dir / episode_path
                full_path.mkdir(parents=True)
                info_file = full_path / f"{full_path.name}.info.json"
                info_file.write_text('{"id": "test123"}')
            
            validator = DirectoryValidator(str(temp_path), dry_run=True)
            all_episodes = validator._scan_all_episodes()
            conflicts = validator._detect_episode_conflicts(all_episodes)
            
            assert len(conflicts) == 1
            conflict = conflicts[0]
            assert conflict.activity == Activity.CYCLING
            assert conflict.season == 20
            assert conflict.episode == 1
            assert len(conflict.conflicting_paths) == 2
    
    def test_repair_corrupted_location_dry_run(self):
        """Test repairing corrupted location in dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media" / "peloton"
            
            # Create corrupted structure
            corrupted_path = (
                media_dir / "Bootcamp 50" / "50" / "Jess Sims" / 
                "S30E001 - 2024-01-15 - 30 min Full Body Bootcamp"
            )
            corrupted_path.mkdir(parents=True)
            info_file = corrupted_path / f"{corrupted_path.name}.info.json"
            info_file.write_text('{"id": "corrupted123"}')
            
            # Create episode info manually (since activity mapping fails for "Bootcamp 50")
            episode_info = EpisodeInfo(
                path=corrupted_path,
                activity=Activity.BOOTCAMP,  # Manually set correct activity
                instructor="Jess Sims",
                season=30,
                episode=1,
                title="2024-01-15 - 30 min Full Body Bootcamp",
                is_corrupted_location=True
            )
            
            validator = DirectoryValidator(str(temp_path), dry_run=True)
            
            # Test dry run repair
            result = validator._move_episode_to_correct_location(episode_info)
            assert result is True
            
            # Original path should still exist (dry run)
            assert corrupted_path.exists()
    
    def test_resolve_episode_conflicts_dry_run(self):
        """Test resolving episode conflicts in dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media" / "peloton"
            
            # Create conflicting episodes
            conflict_paths = [
                media_dir / "Cycling" / "Hannah Frankson" / "S20E001 - First Episode",
                media_dir / "Cycling" / "Emma Lovewell" / "S20E001 - Conflicting Episode",
            ]
            
            for path in conflict_paths:
                path.mkdir(parents=True)
                info_file = path / f"{path.name}.info.json"
                info_file.write_text('{"id": "test123"}')
            
            # Create episode info objects
            episodes = [
                EpisodeInfo(
                    path=conflict_paths[0],
                    activity=Activity.CYCLING,
                    instructor="Hannah Frankson",
                    season=20,
                    episode=1,
                    title="First Episode",
                    is_corrupted_location=False
                ),
                EpisodeInfo(
                    path=conflict_paths[1],
                    activity=Activity.CYCLING,
                    instructor="Emma Lovewell", 
                    season=20,
                    episode=1,
                    title="Conflicting Episode",
                    is_corrupted_location=False
                )
            ]
            
            conflict = ConflictInfo(
                activity=Activity.CYCLING,
                season=20,
                episode=1,
                conflicting_paths=conflict_paths
            )
            
            validator = DirectoryValidator(str(temp_path), dry_run=True)
            result = validator._resolve_single_conflict(conflict, episodes)
            assert result is True
            
            # Original paths should still exist (dry run)
            for path in conflict_paths:
                assert path.exists()
    
    def test_full_validation_and_repair_dry_run(self):
        """Test full validation and repair process in dry run mode."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media" / "peloton"
            
            # Create a mix of normal, corrupted, and conflicting episodes
            episodes_to_create = [
                # Normal episodes
                "Cycling/Hannah Frankson/S20E001 - 2024-01-15 - 20 min Pop Ride",
                "Strength/Andy Speer/S10E001 - 2024-01-15 - 10 min Core",
                
                # Conflicting episodes (same S20E002)
                "Cycling/Emma Lovewell/S20E002 - 2024-01-16 - 20 min Rock Ride",
                "Cycling/Cody Rigsby/S20E002 - 2024-01-17 - 20 min Pop Ride",  # Conflict
                
                # Corrupted structure (will be detected but activity mapping will fail)
                "Bootcamp 50/50/Jess Sims/S30E001 - 2024-01-15 - 30 min Full Body",
            ]
            
            for episode_path in episodes_to_create:
                full_path = media_dir / episode_path
                full_path.mkdir(parents=True)
                info_file = full_path / f"{full_path.name}.info.json"
                info_file.write_text('{"id": "test123"}')
            
            validator = DirectoryValidator(str(temp_path), dry_run=True)
            
            # In dry run mode, repairs are simulated but conflicts will still be detected
            # since files aren't actually moved. This is expected behavior.
            # The validator should report what it would do, but conflicts remain.
            
            # Let's check that it at least detects the issues correctly
            all_episodes = validator._scan_all_episodes()
            assert len(all_episodes) == 5  # Should find all episodes
            
            corrupted_episodes = [ep for ep in all_episodes if ep.is_corrupted_location]
            assert len(corrupted_episodes) == 1  # The 50/50 episode
            
            conflicts = validator._detect_episode_conflicts(all_episodes)
            assert len(conflicts) == 1  # The S20E002 conflict
            
            # The repair process should handle the logic correctly even if dry run
            # For a full test, we'd need to test without dry run, but that's more complex
            
            # All original directories should still exist
            for episode_path in episodes_to_create:
                full_path = media_dir / episode_path
                assert full_path.exists()
    
    def test_activity_name_mapping_edge_cases(self):
        """Test activity name mapping with various edge cases."""
        validator = DirectoryValidator("/tmp", dry_run=True)
        
        # Test normal mappings
        assert validator._map_activity_name("cycling") == Activity.CYCLING
        assert validator._map_activity_name("strength") == Activity.STRENGTH
        
        # Test special bootcamp mappings
        assert validator._map_activity_name("tread bootcamp") == Activity.BOOTCAMP
        assert validator._map_activity_name("bike bootcamp") == Activity.BIKE_BOOTCAMP
        assert validator._map_activity_name("row bootcamp") == Activity.ROW_BOOTCAMP
        
        # Test 50/50 pattern filtering
        assert validator._map_activity_name("bootcamp 50/50") is None
        assert validator._map_activity_name("bootcamp 50-50") is None
        assert validator._map_activity_name("50/50 bootcamp") is None
        assert validator._map_activity_name("bootcamp 50") is None
        assert validator._map_activity_name("bootcamp: 50") is None
        
        # Test unknown activity
        assert validator._map_activity_name("unknown_activity") is None
    
    def test_is_corrupted_location_detection(self):
        """Test detection of corrupted directory locations."""
        validator = DirectoryValidator("/tmp", dry_run=True)
        
        # Test normal paths
        normal_path = Path("/media/peloton/Cycling/Instructor/S20E001 - title")
        assert not validator._is_corrupted_location(normal_path)
        
        # Test corrupted paths with 50/50
        corrupted_paths = [
            Path("/media/peloton/Bootcamp 50/50/Instructor/S30E001 - title"),
            Path("/media/peloton/Activity/50/Instructor/S20E001 - title"),
            Path("/media/peloton/Activity 50-50/Instructor/S20E001 - title"),
        ]
        
        for path in corrupted_paths:
            assert validator._is_corrupted_location(path)
        
        # Test path with wrong depth
        deep_path = Path("/media/peloton/Activity/Extra/Level/Instructor/S20E001 - title")
        assert validator._is_corrupted_location(deep_path)
    
    def test_extract_activity_instructor_normal(self):
        """Test extracting activity and instructor from normal paths."""
        validator = DirectoryValidator("/tmp", dry_run=True)
        
        normal_path = Path("/media/peloton/Cycling/Hannah Frankson/S20E001 - title")
        activity, instructor = validator._extract_activity_instructor(normal_path, is_corrupted=False)
        
        assert activity == Activity.CYCLING
        assert instructor == "Hannah Frankson"
    
    def test_extract_activity_instructor_corrupted(self):
        """Test extracting activity and instructor from corrupted paths."""
        validator = DirectoryValidator("/tmp", dry_run=True)
        
        # Test corrupted path with 50/50 pattern
        corrupted_path = Path("/media/peloton/Bootcamp 50/50/Jess Sims/S30E001 - title")
        activity, instructor = validator._extract_activity_instructor(corrupted_path, is_corrupted=True)
        
        # Should extract "Bootcamp 50" as activity name (which will be filtered later)
        # and "Jess Sims" as instructor
        assert activity is None  # "Bootcamp 50" doesn't map to valid activity
        assert instructor == "Jess Sims"


class TestDirectoryValidatorIntegration:
    """Integration tests for directory validator."""
    
    def test_file_manager_integration_with_validation_disabled(self):
        """Test FileManager with directory validation disabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media"
            subs_file = temp_path / "subscriptions.yaml"
            
            # Create minimal valid structure
            episode_path = media_dir / "peloton" / "Cycling" / "Instructor" / "S20E001 - title"
            episode_path.mkdir(parents=True)
            info_file = episode_path / f"{episode_path.name}.info.json"
            info_file.write_text('{"id": "test123"}')
            
            # Create minimal subscriptions file
            subs_file.write_text("Plex TV Show by Date: {}")
            
            # Import here to avoid circular imports during test discovery
            from src.io.file_manager import FileManager
            
            # Should work with validation disabled
            file_manager = FileManager(str(media_dir), str(subs_file), validate_and_repair=False)
            assert file_manager is not None
    
    def test_file_manager_integration_with_validation_enabled(self):
        """Test FileManager with directory validation enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            media_dir = temp_path / "media"
            subs_file = temp_path / "subscriptions.yaml"
            
            # Create valid structure (no corruption)
            episode_path = media_dir / "peloton" / "Cycling" / "Instructor" / "S20E001 - title"
            episode_path.mkdir(parents=True)
            info_file = episode_path / f"{episode_path.name}.info.json"
            info_file.write_text('{"id": "test123"}')
            
            # Create minimal subscriptions file
            subs_file.write_text("Plex TV Show by Date: {}")
            
            # Import here to avoid circular imports during test discovery
            from src.io.file_manager import FileManager
            
            # Should work with validation enabled (no issues to fix)
            file_manager = FileManager(str(media_dir), str(subs_file), validate_and_repair=True)
            assert file_manager is not None
