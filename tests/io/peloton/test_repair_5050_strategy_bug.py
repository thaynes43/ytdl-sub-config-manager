"""Tests for 50/50 repair strategy bug reproduction and fix."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.io.peloton.repair_5050_strategy import Repair5050Strategy
from src.io.media_source_strategy import DirectoryPattern


class TestRepair5050StrategyBug:
    """Test the 50/50 repair strategy bug reproduction and fix."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = Repair5050Strategy()
        self.mock_pattern = Mock(spec=DirectoryPattern)
    
    def test_folder_filename_mismatch_bug_reproduction(self):
        """Test that reproduces the folder/filename mismatch bug.
        
        This test reproduces the bug where the repair strategy creates a folder
        that doesn't match the file name inside it.
        
        Starting corrupted path: /cephfs-hdd/media/peloton/Tread Bootcamp/Selena Samuela/S30E11 - 20250103 - 30 min Bootcamp: 50/50/S30E11 - 20250103 - 30 min Bootcamp: 50/50.mp4
        
        Expected result: Folder and file should both be "S30E11 - 20250103 - 30 min Bootcamp: 50-50"
        Actual bug result: Folder becomes "S30E11 - 20250103 - 30 min Bootcamp-" but file stays "S30E11 - 20250103 - 30 min Bootcamp: 50-50.mp4"
        """
        # Simulate the corrupted path structure with 50/50 creating extra directory levels
        corrupted_path = Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Selena Samuela/S30E11 - 20250103 - 30 min Bootcamp: 50/50")
        
        # Mock the path to exist so we can test the repair logic
        with patch('pathlib.Path.exists', return_value=True):
            actions = self.strategy.generate_repair_actions(corrupted_path, self.mock_pattern)
            
            # Should generate repair actions
            assert len(actions) > 0
            
            # The repaired folder name should match what the file inside should be named
            repaired_path = actions[0].target_path
            assert repaired_path is not None, "Target path should not be None"
            
            # Extract the episode folder name from the repaired path
            episode_folder_name = repaired_path.parts[-1]
            
            # The folder name should match the expected file name pattern
            # Expected file: S30E11 - 20250103 - 30 min Bootcamp: 50-50.mp4
            # So folder should be: S30E11 - 20250103 - 30 min Bootcamp: 50-50
            assert "S30E11" in episode_folder_name, f"Expected S30E11 in folder name, got: {episode_folder_name}"
            assert "20250103" in episode_folder_name, f"Expected date in folder name, got: {episode_folder_name}"
            assert "30 min Bootcamp: 50-50" in episode_folder_name, f"Expected ': 50-50' in folder name, got: {episode_folder_name}"
            
            # Should NOT have the incorrect format that causes mismatch
            assert not episode_folder_name.endswith("-"), f"Should not end with dash (causes mismatch), got: {episode_folder_name}"
            assert ": 50-50" in episode_folder_name, f"Should preserve ': 50-50' format, got: {episode_folder_name}"
    
    def test_can_repair_detects_50_slash_50_corruption(self):
        """Test that can_repair detects 50/50 corruption patterns."""
        # Test path with 50/50 corruption (creates extra directory levels)
        corrupted_path = Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Selena Samuela/S30E11 - 20250103 - 30 min Bootcamp: 50/50")
        
        # Should detect this as needing repair
        can_repair = self.strategy.can_repair(corrupted_path, self.mock_pattern)
        
        assert can_repair is True, f"Should detect '50/50' as corruption, but can_repair returned {can_repair}"
    
    def test_clean_episode_name_preserves_50_50_format(self):
        """Test that _clean_episode_name preserves the correct 50-50 format."""
        # Test case: episode name with 50/50 that should be converted to 50-50
        episode_name_with_50_slash_50 = "S30E11 - 20250103 - 30 min Bootcamp: 50/50"
        
        cleaned_name = self.strategy._clean_episode_name(episode_name_with_50_slash_50)
        
        # Should convert 50/50 to 50-50, not remove it entirely
        assert ": 50-50" in cleaned_name, f"Should convert ': 50/50' to ': 50-50', got: {cleaned_name}"
        assert "S30E11" in cleaned_name, f"Expected S30E11 in cleaned name, got: {cleaned_name}"
        assert "20250103" in cleaned_name, f"Expected date in cleaned name, got: {cleaned_name}"
        assert "30 min Bootcamp: 50-50" in cleaned_name, f"Expected full activity name with ': 50-50', got: {cleaned_name}"
        
        # Should NOT have the slash version
        assert ": 50/50" not in cleaned_name, f"Should not have ': 50/50' in cleaned name, got: {cleaned_name}"
        assert not cleaned_name.endswith("-"), f"Should not end with dash, got: {cleaned_name}"
    
    def test_clean_episode_name_handles_various_corruption_patterns(self):
        """Test that _clean_episode_name handles various corruption patterns correctly."""
        test_cases = [
            {
                "input": "S30E11 - 20250103 - 30 min Bootcamp: 50/50",
                "expected": "S30E11 - 20250103 - 30 min Bootcamp: 50-50",
                "description": "Convert 50/50 to 50-50"
            },
            {
                "input": "S30E11 - 20250103 - 30 min Bootcamp: 50",
                "expected": "S30E11 - 20250103 - 30 min Bootcamp",
                "description": "Remove standalone : 50"
            },
            {
                "input": "S30E11 - 20250103 - 30 min Bootcamp 50",
                "expected": "S30E11 - 20250103 - 30 min Bootcamp",
                "description": "Remove trailing 50"
            },
            {
                "input": "S30E11 - 20250103 - 30 min Bootcamp: 50-50",
                "expected": "S30E11 - 20250103 - 30 min Bootcamp: 50-50",
                "description": "Preserve correct 50-50 format"
            }
        ]
        
        for test_case in test_cases:
            cleaned = self.strategy._clean_episode_name(test_case["input"])
            
            assert cleaned == test_case["expected"], f"{test_case['description']}: Expected '{test_case['expected']}', got '{cleaned}' from input '{test_case['input']}'"
    
    def test_generate_repair_actions_fixes_50_slash_50_corruption(self):
        """Test that generate_repair_actions fixes 50/50 corruption properly."""
        # Mock Path.exists to return True so we can test the repair logic
        with patch('pathlib.Path.exists', return_value=True):
            # Test path with 50/50 corruption
            corrupted_path = Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Selena Samuela/S30E11 - 20250103 - 30 min Bootcamp: 50/50")
            
            actions = self.strategy.generate_repair_actions(corrupted_path, self.mock_pattern)
            
            # Should generate repair actions
            assert len(actions) > 0
            
            # The repaired folder name should be correct
            repaired_path = actions[0].target_path
            assert repaired_path is not None, "Target path should not be None"
            episode_folder_name = repaired_path.parts[-1]
            
            # Should have the correct format that matches the expected file name
            assert "S30E11" in episode_folder_name, f"Should preserve episode number, got: {episode_folder_name}"
            assert "20250103" in episode_folder_name, f"Should preserve date, got: {episode_folder_name}"
            assert "30 min Bootcamp: 50-50" in episode_folder_name, f"Should have correct activity format, got: {episode_folder_name}"
            assert ": 50-50" in episode_folder_name, f"Should preserve ': 50-50' format, got: {episode_folder_name}"
            assert not episode_folder_name.endswith("-"), f"Should not end with dash, got: {episode_folder_name}"
