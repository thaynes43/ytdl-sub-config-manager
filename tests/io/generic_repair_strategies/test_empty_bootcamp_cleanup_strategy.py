"""Test the empty bootcamp cleanup strategy."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.io.generic_repair_strategies.empty_bootcamp_cleanup_strategy import EmptyBootcampCleanupStrategy
from src.io.media_source_strategy import DirectoryPattern


class TestEmptyBootcampCleanupStrategy:
    """Test the empty bootcamp cleanup strategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = EmptyBootcampCleanupStrategy()
        self.mock_pattern = MagicMock(spec=DirectoryPattern)
    
    def test_can_repair_detects_empty_bootcamp_directory(self):
        """Test that can_repair detects completely empty bootcamp directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create completely empty bootcamp directory structure
            bootcamp_dir = Path(temp_dir) / 'Bootcamp'
            bootcamp_dir.mkdir()
            
            # Create empty instructor directory (no files)
            instructor_dir = bootcamp_dir / 'Instructor'
            instructor_dir.mkdir()
            
            result = self.strategy.can_repair(bootcamp_dir, self.mock_pattern)
            
            assert result is True
    
    def test_can_repair_detects_underscore_bootcamp_directories(self):
        """Test that can_repair detects underscore bootcamp directories."""
        test_cases = ['Bike_Bootcamp', 'Row_Bootcamp']
        
        for folder_name in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                bootcamp_dir = Path(temp_dir) / folder_name
                bootcamp_dir.mkdir()
                
                # Create empty instructor directory
                instructor_dir = bootcamp_dir / 'Instructor'
                instructor_dir.mkdir()
                
                result = self.strategy.can_repair(bootcamp_dir, self.mock_pattern)
                
                assert result is True, f"Should detect {folder_name} as empty"
    
    def test_cannot_repair_non_bootcamp_directories(self):
        """Test that can_repair does not detect non-bootcamp directories."""
        test_cases = ['Cycling', 'Yoga', 'Strength']
        
        for folder_name in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_dir = Path(temp_dir) / folder_name
                test_dir.mkdir()
                
                result = self.strategy.can_repair(test_dir, self.mock_pattern)
                
                assert result is False, f"Should not detect {folder_name}"
    
    def test_cannot_repair_bootcamp_with_episodes(self):
        """Test that can_repair does not detect bootcamp directories with episodes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            bootcamp_dir = Path(temp_dir) / 'Bootcamp'
            bootcamp_dir.mkdir()
            
            # Create instructor directory with episode
            instructor_dir = bootcamp_dir / 'Instructor'
            instructor_dir.mkdir()
            episode_dir = instructor_dir / 'S30E1 - Episode'
            episode_dir.mkdir()
            
            result = self.strategy.can_repair(bootcamp_dir, self.mock_pattern)
            
            assert result is False
    
    def test_generate_repair_actions_creates_delete_action(self):
        """Test that generate_repair_actions creates delete action."""
        path = Path('/media/peloton/Bootcamp')
        
        actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == "delete"
        assert action.source_path == path
        assert action.target_path is None
        assert "Delete empty bootcamp directory: 'Bootcamp'" in action.reason
    
    def test_is_effectively_empty_with_only_empty_dirs(self):
        """Test that directories with only empty subdirectories are considered empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            
            # Create empty instructor directory
            instructor_dir = test_dir / 'Instructor'
            instructor_dir.mkdir()
            
            result = self.strategy._is_effectively_empty_bootcamp_dir(test_dir)
            
            assert result is True
    
    def test_is_not_empty_with_episode_directories(self):
        """Test that directories with episode directories are not considered empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            
            # Create instructor directory with episode
            instructor_dir = test_dir / 'Instructor'
            instructor_dir.mkdir()
            episode_dir = instructor_dir / 'S30E1 - Episode'
            episode_dir.mkdir()
            
            result = self.strategy._is_effectively_empty_bootcamp_dir(test_dir)
            
            assert result is False
    
    def test_is_not_empty_with_any_files(self):
        """Test that directories with any files are not considered empty."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir)
            
            # Create instructor directory with any file
            instructor_dir = test_dir / 'Instructor'
            instructor_dir.mkdir()
            (instructor_dir / '.ytdl-sub-archive.json').touch()  # Even archive files prevent cleanup
            
            result = self.strategy._is_effectively_empty_bootcamp_dir(test_dir)
            
            assert result is False
    
    def test_has_episode_pattern_detection(self):
        """Test that episode pattern detection works correctly."""
        test_cases = [
            ('S30E1 - Episode', True),
            ('S45E123 - Another Episode', True),
            ('Regular Folder', False),
            ('Instructor Name', False),
            ('50', False)
        ]
        
        for name, expected in test_cases:
            result = self.strategy._has_episode_pattern(name)
            assert result == expected, f"Pattern detection failed for: {name}"
