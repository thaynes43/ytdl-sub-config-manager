"""Tests for missing instructor repair strategy."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from src.io.peloton.missing_instructor_repair_strategy import MissingInstructorRepairStrategy
from src.io.media_source_strategy import DirectoryPattern


class TestMissingInstructorRepairStrategy:
    """Test the missing instructor repair strategy."""
    
    def test_can_repair_missing_instructor_directory(self):
        """Test can_repair identifies missing instructor directories."""
        strategy = MissingInstructorRepairStrategy()
        expected_pattern = DirectoryPattern(
            pattern="{activity}/{instructor}/S{season}E{episode}",
            expected_levels=3,
            has_source_subdir=False
        )
        
        # Test case that should be repairable (missing instructor)
        problematic_path = Path("D:/media/Strength/S20E150 - 20250924 - 20 min Core Strength with Rebecca Kennedy")
        assert strategy.can_repair(problematic_path, expected_pattern) is True
        
        # Test case that should NOT be repairable (correct structure)
        correct_path = Path("D:/media/Strength/Rebecca Kennedy/S20E150 - 20250924 - 20 min Core Strength")
        assert strategy.can_repair(correct_path, expected_pattern) is False
        
        # Test case without episode pattern
        no_episode_path = Path("D:/media/Strength/Some Random Folder")
        assert strategy.can_repair(no_episode_path, expected_pattern) is False
    
    def test_generate_repair_actions_success(self):
        """Test generate_repair_actions creates correct repair actions."""
        strategy = MissingInstructorRepairStrategy()
        expected_pattern = DirectoryPattern(
            pattern="{activity}/{instructor}/S{season}E{episode}",
            expected_levels=3,
            has_source_subdir=False
        )
        
        # Test with the problematic path from the error
        problematic_path = Path("D:/labspace/tmp/test-media/Strength/S20E150 - 20250924 - 20 min Core Strength Benchmark with Rebecca Kennedy")
        
        actions = strategy.generate_repair_actions(problematic_path, expected_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        
        assert action.action_type == "move"
        assert action.source_path == problematic_path
        
        # Should create path with instructor directory
        expected_target = Path("D:/labspace/tmp/test-media/Strength/Rebecca Kennedy/S20E150 - 20250924 - 20 min Core Strength Benchmark with Rebecca Kennedy")
        assert action.target_path == expected_target
        assert "Rebecca Kennedy" in action.reason
    
    def test_generate_repair_actions_with_hash_suffix(self):
        """Test generate_repair_actions handles titles with hash suffixes."""
        strategy = MissingInstructorRepairStrategy()
        expected_pattern = DirectoryPattern(
            pattern="{activity}/{instructor}/S{season}E{episode}",
            expected_levels=3,
            has_source_subdir=False
        )
        
        # Test with title that has hash suffix (from conflict resolution)
        path_with_hash = Path("D:/media/Cycling/S20E001 - 20250924 - 20 min Ride with Hannah Corbin 97209d5")
        
        actions = strategy.generate_repair_actions(path_with_hash, expected_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        
        # Should extract instructor name without the hash
        expected_target = Path("D:/media/Cycling/Hannah Corbin/S20E001 - 20250924 - 20 min Ride with Hannah Corbin 97209d5")
        assert action.target_path == expected_target
        assert "Hannah Corbin" in str(action.target_path)
    
    def test_generate_repair_actions_no_instructor_found(self):
        """Test generate_repair_actions when instructor cannot be extracted."""
        strategy = MissingInstructorRepairStrategy()
        expected_pattern = DirectoryPattern(
            pattern="{activity}/{instructor}/S{season}E{episode}",
            expected_levels=3,
            has_source_subdir=False
        )
        
        # Test with title without "with {instructor}" pattern
        problematic_path = Path("D:/media/Strength/S20E150 - 20250924 - 20 min Core Strength Benchmark")
        
        actions = strategy.generate_repair_actions(problematic_path, expected_pattern)
        
        # Should return empty list when instructor cannot be extracted
        assert len(actions) == 0
    
    def test_generate_repair_actions_invalid_title_format(self):
        """Test generate_repair_actions with invalid title format."""
        strategy = MissingInstructorRepairStrategy()
        expected_pattern = DirectoryPattern(
            pattern="{activity}/{instructor}/S{season}E{episode}",
            expected_levels=3,
            has_source_subdir=False
        )
        
        # Test with folder that doesn't match expected title pattern
        problematic_path = Path("D:/media/Strength/InvalidFolderName")
        
        actions = strategy.generate_repair_actions(problematic_path, expected_pattern)
        
        # Should return empty list for invalid format
        assert len(actions) == 0
