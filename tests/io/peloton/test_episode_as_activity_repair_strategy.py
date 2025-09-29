"""Test the episode as activity repair strategy."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from src.io.peloton.episode_as_activity_repair_strategy import EpisodeAsActivityRepairStrategy
from src.io.media_source_strategy import DirectoryPattern


class TestEpisodeAsActivityRepairStrategy:
    """Test the episode as activity repair strategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = EpisodeAsActivityRepairStrategy()
        self.mock_pattern = MagicMock(spec=DirectoryPattern)
    
    def test_can_repair_detects_episode_as_activity_corruption(self):
        """Test that can_repair detects episode names used as activity names."""
        # Test cases from the actual log warnings
        test_cases = [
            's30e412 - 20250624 - 30 min bootcamp: 50',
            's30e250 - 20250723 - 30 min bootcamp: 50',
            's45e128 - 20250916 - 45 min bootcamp: 50'
        ]
        
        for corrupted_activity in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_path = Path(temp_dir) / corrupted_activity / 'Instructor' / 'Episode'
                test_path.mkdir(parents=True)
                
                result = self.strategy.can_repair(test_path, self.mock_pattern)
                
                assert result is True, f"Should detect corruption in: {corrupted_activity}"
    
    def test_cannot_repair_normal_activity_names(self):
        """Test that can_repair does not detect normal activity names."""
        normal_activities = [
            'Tread Bootcamp',
            'Bike Bootcamp', 
            'Row Bootcamp',
            'Cycling',
            'Strength'
        ]
        
        for activity in normal_activities:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_path = Path(temp_dir) / activity / 'Instructor' / 'S30E1 - Episode'
                test_path.mkdir(parents=True)
                
                result = self.strategy.can_repair(test_path, self.mock_pattern)
                
                assert result is False, f"Should not detect corruption in: {activity}"
    
    def test_cannot_repair_non_bootcamp_episode_corruption(self):
        """Test that can_repair only detects bootcamp-related episode corruption."""
        # Episode patterns without bootcamp should not be detected
        test_path = Path('/media/peloton/s30e1 - cycling class/Instructor/Episode')
        
        result = self.strategy.can_repair(test_path, self.mock_pattern)
        
        assert result is False
    
    def test_generate_repair_actions_creates_correct_target(self):
        """Test that repair actions create correct target paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            corrupted_activity = 's30e412 - 20250624 - 30 min bootcamp: 50'
            test_path = Path(temp_dir) / corrupted_activity / 'Jess Sims' / 'S30E1 - Episode'
            test_path.mkdir(parents=True)
            
            actions = self.strategy.generate_repair_actions(test_path, self.mock_pattern)
            
            assert len(actions) == 1
            action = actions[0]
            
            assert action.action_type == "move"
            assert action.source_path == test_path
            
            # Should move to Tread Bootcamp
            expected_target = Path(temp_dir) / 'Tread Bootcamp' / 'Jess Sims' / 'S30E1 - Episode'
            assert action.target_path == expected_target
            
            assert "Fix episode-as-activity corruption" in action.reason
    
    def test_infer_correct_activity_for_bootcamp_variants(self):
        """Test that _infer_correct_activity works for different bootcamp types."""
        test_cases = [
            ('s30e1 - bootcamp class', 'Tread Bootcamp'),
            ('s45e1 - bike bootcamp class', 'Bike Bootcamp'),
            ('s60e1 - row bootcamp class', 'Row Bootcamp'),
            ('s30e1 - some other class', None)  # Non-bootcamp should return None
        ]
        
        for corrupted_name, expected_activity in test_cases:
            result = self.strategy._infer_correct_activity(corrupted_name)
            assert result == expected_activity, f"Failed for: {corrupted_name}"
    
    def test_real_world_corruption_examples(self):
        """Test with the exact corruption examples from the logs."""
        real_examples = [
            ('s30e412 - 20250624 - 30 min bootcamp: 50', 'Tread Bootcamp'),
            ('s30e250 - 20250723 - 30 min bootcamp: 50', 'Tread Bootcamp'),
            ('s45e128 - 20250916 - 45 min bootcamp: 50', 'Tread Bootcamp')
        ]
        
        for corrupted_activity, expected_target_activity in real_examples:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_path = Path(temp_dir) / corrupted_activity / 'Instructor' / 'Episode'
                test_path.mkdir(parents=True)
                
                # Test detection
                can_repair = self.strategy.can_repair(test_path, self.mock_pattern)
                assert can_repair is True, f"Should detect: {corrupted_activity}"
                
                # Test repair action
                actions = self.strategy.generate_repair_actions(test_path, self.mock_pattern)
                assert len(actions) == 1
                
                action = actions[0]
                expected_target = Path(temp_dir) / expected_target_activity / 'Instructor' / 'Episode'
                assert action.target_path == expected_target
