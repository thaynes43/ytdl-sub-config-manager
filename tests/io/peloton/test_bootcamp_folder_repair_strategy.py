"""Tests for bootcamp folder repair strategy."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from src.io.peloton.bootcamp_folder_repair_strategy import BootcampFolderRepairStrategy
from src.io.media_source_strategy import DirectoryPattern


class TestBootcampFolderRepairStrategy:
    """Test the bootcamp folder repair strategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = BootcampFolderRepairStrategy()
        self.mock_pattern = Mock(spec=DirectoryPattern)
    
    def test_can_repair_bootcamp_directory(self):
        """Test that strategy can repair incorrect Bootcamp directory."""
        # Test case: /media/peloton/Bootcamp/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp
        path = Path("/media/peloton/Bootcamp/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp")
        
        assert self.strategy.can_repair(path, self.mock_pattern) is True
    
    def test_can_repair_case_insensitive(self):
        """Test that strategy works with case-insensitive bootcamp detection."""
        path = Path("/media/peloton/bootcamp/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp")
        
        assert self.strategy.can_repair(path, self.mock_pattern) is True
    
    def test_cannot_repair_tread_bootcamp_directory(self):
        """Test that strategy does not repair correct Tread Bootcamp directory."""
        path = Path("/media/peloton/Tread Bootcamp/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp")
        
        assert self.strategy.can_repair(path, self.mock_pattern) is False
    
    def test_cannot_repair_other_activities(self):
        """Test that strategy does not repair other activity directories."""
        path = Path("/media/peloton/Cycling/Andy Speer/S45E114 - 20250902 - 45 min Power Zone Ride")
        
        assert self.strategy.can_repair(path, self.mock_pattern) is False
    
    def test_cannot_repair_short_path(self):
        """Test that strategy cannot repair paths that are too short."""
        path = Path("/media/peloton/Bootcamp")
        
        assert self.strategy.can_repair(path, self.mock_pattern) is False
    
    def test_cannot_repair_non_episode_folder(self):
        """Test that strategy cannot repair paths without episode pattern."""
        path = Path("/media/peloton/Bootcamp/Andy Speer/Some Random Folder")
        
        assert self.strategy.can_repair(path, self.mock_pattern) is False
    
    @patch('pathlib.Path.exists')
    def test_generate_repair_actions_no_conflict(self, mock_exists):
        """Test repair action generation when no conflicts exist."""
        mock_exists.return_value = False
        
        path = Path("/media/peloton/Bootcamp/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp")
        
        actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == "move"
        assert action.source_path == path
        assert action.target_path == Path("/media/peloton/Tread Bootcamp/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp")
        assert "Bootcamp" in action.reason
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    def test_generate_repair_actions_with_conflict(self, mock_iterdir, mock_exists):
        """Test repair action generation when episode conflicts exist."""
        mock_exists.return_value = True
        
        # Mock existing episodes in target directory
        existing_episode = Mock()
        existing_episode.name = "S45E100 - 20250801 - 45 min HIIT Bootcamp"
        existing_episode.is_dir.return_value = True
        mock_iterdir.return_value = [existing_episode]
        
        path = Path("/media/peloton/Bootcamp/Andy Speer/S45E50 - 20250902 - 45 min HIIT Bootcamp")
        
        actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == "move"
        assert action.source_path == path
        # Should resolve conflict by using next available episode number (101)
        assert action.target_path == Path("/media/peloton/Tread Bootcamp/Andy Speer/S45E101 - 20250902 - 45 min HIIT Bootcamp")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    def test_generate_repair_actions_no_conflict_when_target_exists(self, mock_iterdir, mock_exists):
        """Test repair action generation when target exists but no episode conflict."""
        mock_exists.return_value = True
        
        # Mock existing episodes in target directory with different season
        existing_episode = Mock()
        existing_episode.name = "S30E100 - 20250801 - 30 min HIIT Bootcamp"
        existing_episode.is_dir.return_value = True
        mock_iterdir.return_value = [existing_episode]
        
        path = Path("/media/peloton/Bootcamp/Andy Speer/S45E50 - 20250902 - 45 min HIIT Bootcamp")
        
        actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        # No conflict because different season (S45 vs S30)
        assert action.target_path == Path("/media/peloton/Tread Bootcamp/Andy Speer/S45E50 - 20250902 - 45 min HIIT Bootcamp")
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    def test_resolve_episode_conflict_same_season(self, mock_iterdir, mock_exists):
        """Test episode conflict resolution for same season."""
        mock_exists.return_value = True
        
        target_dir = Path("/media/peloton/Tread Bootcamp/Andy Speer")
        episode_folder = "S45E50 - 20250902 - 45 min HIIT Bootcamp"
        
        # Create mock existing episodes
        existing_episode = Mock()
        existing_episode.name = "S45E100 - 20250801 - 45 min HIIT Bootcamp"
        existing_episode.is_dir.return_value = True
        mock_iterdir.return_value = [existing_episode]
        
        new_folder = self.strategy._resolve_episode_conflict(target_dir, episode_folder)
        
        # Should resolve to next available episode number
        assert new_folder == "S45E101 - 20250902 - 45 min HIIT Bootcamp"
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    def test_resolve_episode_conflict_different_season(self, mock_iterdir, mock_exists):
        """Test episode conflict resolution for different season (no conflict)."""
        mock_exists.return_value = True
        
        target_dir = Path("/media/peloton/Tread Bootcamp/Andy Speer")
        episode_folder = "S45E50 - 20250902 - 45 min HIIT Bootcamp"
        
        # Create mock existing episodes from different season
        existing_episode = Mock()
        existing_episode.name = "S30E100 - 20250801 - 30 min HIIT Bootcamp"
        existing_episode.is_dir.return_value = True
        mock_iterdir.return_value = [existing_episode]
        
        new_folder = self.strategy._resolve_episode_conflict(target_dir, episode_folder)
        
        # No conflict because different season, should return original
        assert new_folder == episode_folder
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    def test_resolve_episode_conflict_no_existing_episodes(self, mock_iterdir, mock_exists):
        """Test episode conflict resolution when no existing episodes."""
        mock_exists.return_value = True
        mock_iterdir.return_value = []
        
        target_dir = Path("/media/peloton/Tread Bootcamp/Andy Speer")
        episode_folder = "S45E50 - 20250902 - 45 min HIIT Bootcamp"
        
        new_folder = self.strategy._resolve_episode_conflict(target_dir, episode_folder)
        
        # No conflict, should return original
        assert new_folder == episode_folder
    
    def test_resolve_episode_conflict_invalid_episode_name(self):
        """Test episode conflict resolution with invalid episode name."""
        target_dir = Path("/media/peloton/Tread Bootcamp/Andy Speer")
        episode_folder = "Invalid Episode Name"
        
        new_folder = self.strategy._resolve_episode_conflict(target_dir, episode_folder)
        
        # Should return original when parsing fails
        assert new_folder == episode_folder
    
    def test_can_repair_all_bootcamp_variants(self):
        """Test that strategy can repair all bootcamp activity variants."""
        bootcamp_variants = [
            "bootcamp",
            "Bootcamp", 
            "BOOTCAMP",
            "bOoTcAmP"
        ]
        
        for variant in bootcamp_variants:
            path = Path(f"/media/peloton/{variant}/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp")
            assert self.strategy.can_repair(path, self.mock_pattern) is True, f"Failed for variant: {variant}"
    
    def test_cannot_repair_correct_bootcamp_variants(self):
        """Test that strategy does not repair correct bootcamp folder names."""
        correct_variants = [
            "Tread Bootcamp",
            "Bike Bootcamp", 
            "Row Bootcamp",
            "tread bootcamp",
            "bike bootcamp",
            "row bootcamp"
        ]
        
        for variant in correct_variants:
            path = Path(f"/media/peloton/{variant}/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp")
            assert self.strategy.can_repair(path, self.mock_pattern) is False, f"Should not repair correct variant: {variant}"
    
    @patch('pathlib.Path.exists')
    def test_real_world_path_example(self, mock_exists):
        """Test repair action generation with real-world path example."""
        mock_exists.return_value = False
        
        # Real path from user's example
        path = Path("/cephfs-hdd/media/peloton/Bootcamp/Matty Maggiacomo/S30E228 - 20250926 - 30 min Walking Bootcamp")
        
        actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == "move"
        assert action.source_path == path
        assert action.target_path == Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Matty Maggiacomo/S30E228 - 20250926 - 30 min Walking Bootcamp")
        assert "Bootcamp" in action.reason
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    def test_real_world_path_with_episode_conflict(self, mock_iterdir, mock_exists):
        """Test repair action generation with real-world path and episode conflict."""
        mock_exists.return_value = True
        
        # Mock existing episodes in target directory that would conflict
        existing_episodes = []
        episode_names = [
            "S30E225 - 20250923 - 30 min Walking Bootcamp",
            "S30E226 - 20250924 - 30 min Walking Bootcamp", 
            "S30E227 - 20250925 - 30 min Walking Bootcamp",
            "S30E228 - 20250925 - 30 min Walking Bootcamp"  # This conflicts!
        ]
        for name in episode_names:
            episode = Mock()
            episode.name = name
            episode.is_dir.return_value = True
            existing_episodes.append(episode)
        mock_iterdir.return_value = existing_episodes
        
        # Real path from user's example
        path = Path("/cephfs-hdd/media/peloton/Bootcamp/Matty Maggiacomo/S30E228 - 20250926 - 30 min Walking Bootcamp")
        
        actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == "move"
        assert action.source_path == path
        # Should resolve conflict by using next available episode number (229)
        assert action.target_path == Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Matty Maggiacomo/S30E229 - 20250926 - 30 min Walking Bootcamp")
        assert "Bootcamp" in action.reason
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.iterdir')
    def test_episode_conflict_resolution_with_multiple_seasons(self, mock_iterdir, mock_exists):
        """Test episode conflict resolution when target has episodes from multiple seasons."""
        mock_exists.return_value = True
        
        # Mock existing episodes from different seasons
        existing_episodes = []
        episode_names = [
            "S20E100 - 20250901 - 20 min HIIT Bootcamp",
            "S30E50 - 20250902 - 30 min HIIT Bootcamp",
            "S30E51 - 20250903 - 30 min HIIT Bootcamp",
            "S45E200 - 20250904 - 45 min HIIT Bootcamp",
        ]
        for name in episode_names:
            episode = Mock()
            episode.name = name
            episode.is_dir.return_value = True
            existing_episodes.append(episode)
        mock_iterdir.return_value = existing_episodes
        
        # Try to move S30E50 (should conflict and become S30E52)
        path = Path("/media/peloton/Bootcamp/Andy Speer/S30E50 - 20250905 - 30 min HIIT Bootcamp")
        
        actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        # Should resolve to S30E52 (next available for season 30)
        assert action.target_path == Path("/media/peloton/Tread Bootcamp/Andy Speer/S30E52 - 20250905 - 30 min HIIT Bootcamp")
    
    def test_path_reconstruction_logic(self):
        """Test that path reconstruction works correctly for various path structures."""
        test_cases = [
            {
                "input": "/media/peloton/Bootcamp/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp",
                "expected": "/media/peloton/Tread Bootcamp/Andy Speer/S45E114 - 20250902 - 45 min HIIT Bootcamp"
            },
            {
                "input": "/cephfs-hdd/media/peloton/Bootcamp/Matty Maggiacomo/S30E228 - 20250926 - 30 min Walking Bootcamp",
                "expected": "/cephfs-hdd/media/peloton/Tread Bootcamp/Matty Maggiacomo/S30E228 - 20250926 - 30 min Walking Bootcamp"
            },
            {
                "input": "/mnt/storage/peloton/Bootcamp/Emma Lovewell/S20E50 - 20250901 - 20 min HIIT Bootcamp",
                "expected": "/mnt/storage/peloton/Tread Bootcamp/Emma Lovewell/S20E50 - 20250901 - 20 min HIIT Bootcamp"
            }
        ]
        
        for test_case in test_cases:
            with patch('pathlib.Path.exists', return_value=False):
                path = Path(test_case["input"])
                actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
                
                assert len(actions) == 1
                action = actions[0]
                # Normalize paths for cross-platform comparison
                actual_path = str(action.target_path).replace('\\', '/')
                expected_path = test_case["expected"]
                assert actual_path == expected_path, f"Failed for input: {test_case['input']}"
