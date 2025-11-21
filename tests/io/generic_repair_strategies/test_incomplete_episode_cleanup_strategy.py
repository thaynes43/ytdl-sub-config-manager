"""Test the incomplete episode cleanup strategy."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from src.io.generic_repair_strategies.incomplete_episode_cleanup_strategy import IncompleteEpisodeCleanupStrategy
from src.io.media_source_strategy import DirectoryPattern


class TestIncompleteEpisodeCleanupStrategy:
    """Test the incomplete episode cleanup strategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = IncompleteEpisodeCleanupStrategy()
        self.mock_pattern = MagicMock(spec=DirectoryPattern)
    
    def test_cannot_repair_complete_episode(self):
        """Test that complete episodes are not detected for deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir) / 'S30E16 - 20250511 - 30 min 80s Rock Ride'
            episode_dir.mkdir()
            
            # Create all required files
            (episode_dir / 'S30E16 - 20250511 - 30 min 80s Rock Ride.mp4').touch()
            (episode_dir / 'S30E16 - 20250511 - 30 min 80s Rock Ride.info.json').touch()
            (episode_dir / 'S30E16 - 20250511 - 30 min 80s Rock Ride-thumb.jpg').touch()
            
            result = self.strategy.can_repair(episode_dir, self.mock_pattern)
            
            assert result is False
    
    def test_can_repair_episode_missing_video(self):
        """Test that episodes missing video files are detected for deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir) / 'S30E1 - Episode'
            episode_dir.mkdir()
            
            # Missing .mp4 file
            (episode_dir / 'S30E1 - Episode.info.json').touch()
            (episode_dir / 'S30E1 - Episode-thumb.jpg').touch()
            
            result = self.strategy.can_repair(episode_dir, self.mock_pattern)
            
            assert result is True
    
    def test_can_repair_episode_missing_metadata(self):
        """Test that episodes missing metadata files are detected for deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir) / 'S45E5 - Test Episode'
            episode_dir.mkdir()
            
            # Missing .info.json file
            (episode_dir / 'S45E5 - Test Episode.mp4').touch()
            (episode_dir / 'S45E5 - Test Episode-thumb.jpg').touch()
            
            result = self.strategy.can_repair(episode_dir, self.mock_pattern)
            
            assert result is True
    
    def test_can_repair_episode_missing_thumbnail(self):
        """Test that episodes missing ONLY thumbnail files ARE detected for repair (generation)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir) / 'S60E3 - Test Episode'
            episode_dir.mkdir()
            
            # Missing -thumb.jpg file
            (episode_dir / 'S60E3 - Test Episode.mp4').touch()
            (episode_dir / 'S60E3 - Test Episode.info.json').touch()
            
            result = self.strategy.can_repair(episode_dir, self.mock_pattern)
            
            assert result is True, "Episode missing thumbnail SHOULD be detected for repair (generation)"
            
            actions = self.strategy.generate_repair_actions(episode_dir, self.mock_pattern)
            assert len(actions) == 1
            assert actions[0].action_type == "generate_thumbnail"
            assert actions[0].source_path == episode_dir / 'S60E3 - Test Episode.mp4'
            assert actions[0].target_path == episode_dir / 'S60E3 - Test Episode-thumb.jpg'
    
    def test_can_repair_episode_missing_multiple_files(self):
        """Test that episodes missing multiple files are detected for deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir) / 'S20E10 - Test Episode'
            episode_dir.mkdir()
            
            # Only has video file, missing metadata and thumbnail
            (episode_dir / 'S20E10 - Test Episode.mp4').touch()
            
            result = self.strategy.can_repair(episode_dir, self.mock_pattern)
            
            assert result is True
    
    def test_cannot_repair_non_episode_directories(self):
        """Test that non-episode directories are not detected for deletion."""
        test_cases = ['Instructor Name', 'Random Folder', '50', 'Archive']
        
        for folder_name in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_dir = Path(temp_dir) / folder_name
                test_dir.mkdir()
                
                result = self.strategy.can_repair(test_dir, self.mock_pattern)
                
                assert result is False, f"Should not detect non-episode directory: {folder_name}"
    
    def test_cannot_repair_files(self):
        """Test that files are not detected for deletion."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / 'S30E1 - Episode.mp4'
            test_file.touch()
            
            result = self.strategy.can_repair(test_file, self.mock_pattern)
            
            assert result is False
    
    def test_generate_repair_actions_creates_delete_action(self):
        """Test that generate_repair_actions creates delete action with proper reason."""
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir) / 'S30E1 - Episode'
            episode_dir.mkdir()
            
            # Missing video file
            (episode_dir / 'S30E1 - Episode.info.json').touch()
            (episode_dir / 'S30E1 - Episode-thumb.jpg').touch()
            
            actions = self.strategy.generate_repair_actions(episode_dir, self.mock_pattern)
            
            assert len(actions) == 1
            action = actions[0]
            assert action.action_type == "delete"
            assert action.source_path == episode_dir
            assert action.target_path is None
            assert "Delete incomplete episode directory: 'S30E1 - Episode'" in action.reason
            assert "missing: S30E1 - Episode.mp4" in action.reason
    
    def test_get_missing_files_identifies_all_missing(self):
        """Test that _get_missing_files correctly identifies all missing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir) / 'S30E1 - Episode'
            episode_dir.mkdir()
            
            # Only create thumbnail file
            (episode_dir / 'S30E1 - Episode-thumb.jpg').touch()
            
            missing_files = self.strategy._get_missing_files(episode_dir)
            
            expected_missing = [
                'S30E1 - Episode.info.json',
                'S30E1 - Episode.mp4'
            ]
            assert missing_files == expected_missing
    
    def test_has_episode_pattern_detection(self):
        """Test that episode pattern detection works correctly."""
        test_cases = [
            ('S30E1 - Episode', True),
            ('S45E123 - Another Episode', True),
            ('S60E5 - Test', True),
            ('Regular Folder', False),
            ('Instructor Name', False),
            ('50', False),
            ('Archive', False)
        ]
        
        for name, expected in test_cases:
            result = self.strategy._has_episode_pattern(name)
            assert result == expected, f"Pattern detection failed for: {name}"
    
    def test_real_world_complete_episode_example(self):
        """Test with the exact file structure from the user's example."""
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_name = 'S30E16 - 20250511 - 30 min 80s Rock Ride'
            episode_dir = Path(temp_dir) / episode_name
            episode_dir.mkdir()
            
            # Create the exact files from user's example
            (episode_dir / f'{episode_name}.info.json').touch()
            (episode_dir / f'{episode_name}.mp4').touch()
            (episode_dir / f'{episode_name}-thumb.jpg').touch()
            
            result = self.strategy.can_repair(episode_dir, self.mock_pattern)
            
            assert result is False, "Complete episode should not be detected for deletion"
    
    def test_real_world_incomplete_episode_example(self):
        """Test with an incomplete episode that should be deleted."""
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_name = 'S30E16 - 20250511 - 30 min 80s Rock Ride'
            episode_dir = Path(temp_dir) / episode_name
            episode_dir.mkdir()
            
            # Missing video file (common corruption scenario)
            (episode_dir / f'{episode_name}.info.json').touch()
            (episode_dir / f'{episode_name}-thumb.jpg').touch()
            
            result = self.strategy.can_repair(episode_dir, self.mock_pattern)
            
            assert result is True, "Incomplete episode should be detected for deletion"
            
            actions = self.strategy.generate_repair_actions(episode_dir, self.mock_pattern)
            assert len(actions) == 1
            assert "missing: S30E16 - 20250511 - 30 min 80s Rock Ride.mp4" in actions[0].reason
