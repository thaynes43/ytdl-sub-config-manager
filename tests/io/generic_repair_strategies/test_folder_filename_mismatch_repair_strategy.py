"""Tests for folder/filename mismatch repair strategy."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.io.generic_repair_strategies.folder_filename_mismatch_repair_strategy import FolderFilenameMismatchRepairStrategy
from src.io.media_source_strategy import DirectoryPattern


class TestFolderFilenameMismatchRepairStrategy:
    """Test the folder/filename mismatch repair strategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = FolderFilenameMismatchRepairStrategy()
        self.mock_pattern = Mock(spec=DirectoryPattern)
    
    def test_can_repair_detects_folder_filename_mismatch(self):
        """Test that can_repair detects folder/filename mismatches."""
        # Create a mock directory with mismatched folder and file names
        mock_dir = Mock(spec=Path)
        mock_dir.is_dir.return_value = True
        mock_dir.name = "S30E213 - 20250103 - 30 min Bootcamp-"
        
        # Mock video file with different name
        mock_video_file = Mock(spec=Path)
        mock_video_file.is_file.return_value = True
        mock_video_file.suffix = ".mp4"
        mock_video_file.stem = "S30E11 - 20250103 - 30 min Bootcamp: 50-50"
        
        # Mock directory iteration
        mock_dir.iterdir.return_value = [mock_video_file]
        
        # Should detect the mismatch
        can_repair = self.strategy.can_repair(mock_dir, self.mock_pattern)
        
        assert can_repair is True, "Should detect folder/filename mismatch"
    
    def test_can_repair_no_mismatch_when_names_match(self):
        """Test that can_repair returns False when folder and file names match."""
        # Create a mock directory with matching folder and file names
        mock_dir = Mock(spec=Path)
        mock_dir.is_dir.return_value = True
        mock_dir.name = "S30E11 - 20250103 - 30 min Bootcamp: 50-50"
        
        # Mock video file with matching name
        mock_video_file = Mock(spec=Path)
        mock_video_file.is_file.return_value = True
        mock_video_file.suffix = ".mp4"
        mock_video_file.stem = "S30E11 - 20250103 - 30 min Bootcamp: 50-50"
        
        # Mock directory iteration
        mock_dir.iterdir.return_value = [mock_video_file]
        
        # Should not detect mismatch
        can_repair = self.strategy.can_repair(mock_dir, self.mock_pattern)
        
        assert can_repair is False, "Should not detect mismatch when names match"
    
    def test_can_repair_returns_false_for_files(self):
        """Test that can_repair returns False for files (not directories)."""
        mock_file = Mock(spec=Path)
        mock_file.is_dir.return_value = False
        
        can_repair = self.strategy.can_repair(mock_file, self.mock_pattern)
        
        assert can_repair is False, "Should not repair files, only directories"
    
    def test_can_repair_returns_false_for_directories_without_videos(self):
        """Test that can_repair returns False for directories without video files."""
        mock_dir = Mock(spec=Path)
        mock_dir.is_dir.return_value = True
        mock_dir.name = "Some Folder"
        
        # Mock non-video file
        mock_text_file = Mock(spec=Path)
        mock_text_file.is_file.return_value = True
        mock_text_file.suffix = ".txt"
        
        # Mock directory iteration
        mock_dir.iterdir.return_value = [mock_text_file]
        
        can_repair = self.strategy.can_repair(mock_dir, self.mock_pattern)
        
        assert can_repair is False, "Should not repair directories without video files"
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.iterdir')
    def test_generate_repair_actions_fixes_mismatch(self, mock_iterdir, mock_is_dir, mock_exists):
        """Test that generate_repair_actions fixes folder/filename mismatches."""
        mock_exists.return_value = False  # Target doesn't exist
        mock_is_dir.return_value = True
        
        # Create source path
        source_path = Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Selena Samuela/S30E213 - 20250103 - 30 min Bootcamp-")
        
        # Create mock video file
        mock_video_file = Mock(spec=Path)
        mock_video_file.is_file.return_value = True
        mock_video_file.suffix = ".mp4"
        mock_video_file.stem = "S30E11 - 20250103 - 30 min Bootcamp: 50-50"
        
        mock_iterdir.return_value = [mock_video_file]
        
        actions = self.strategy.generate_repair_actions(source_path, self.mock_pattern)
        
        # Should generate repair action
        assert len(actions) == 1
        action = actions[0]
        
        assert action.action_type == "move"
        assert action.source_path == source_path
        assert action.target_path == Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Selena Samuela/S30E11 - 20250103 - 30 min Bootcamp: 50-50")
        assert "folder/filename mismatch" in action.reason
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.iterdir')
    def test_generate_repair_actions_skips_when_target_exists(self, mock_iterdir, mock_is_dir, mock_exists):
        """Test that generate_repair_actions skips repair when target already exists."""
        mock_exists.return_value = True  # Target exists
        mock_is_dir.return_value = True
        
        # Create source path
        source_path = Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Selena Samuela/S30E213 - 20250103 - 30 min Bootcamp-")
        
        # Create mock video file
        mock_video_file = Mock(spec=Path)
        mock_video_file.is_file.return_value = True
        mock_video_file.suffix = ".mp4"
        mock_video_file.stem = "S30E11 - 20250103 - 30 min Bootcamp: 50-50"
        
        mock_iterdir.return_value = [mock_video_file]
        
        actions = self.strategy.generate_repair_actions(source_path, self.mock_pattern)
        
        # Should not generate repair action when target exists
        assert len(actions) == 0
    
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.iterdir')
    def test_generate_repair_actions_no_video_files(self, mock_iterdir, mock_is_dir):
        """Test that generate_repair_actions returns empty list when no video files found."""
        mock_is_dir.return_value = True
        
        # Create source path
        source_path = Path("/some/path")
        
        # Mock empty directory
        mock_iterdir.return_value = []
        
        actions = self.strategy.generate_repair_actions(source_path, self.mock_pattern)
        
        # Should not generate repair action
        assert len(actions) == 0
    
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.is_dir')
    @patch('pathlib.Path.iterdir')
    def test_real_world_example(self, mock_iterdir, mock_is_dir, mock_exists):
        """Test the specific real-world example from the user."""
        mock_exists.return_value = False  # Target doesn't exist
        mock_is_dir.return_value = True
        
        # Test the exact scenario described by the user
        source_path = Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Selena Samuela/S30E213 - 20250103 - 30 min Bootcamp-")
        expected_target = Path("/cephfs-hdd/media/peloton/Tread Bootcamp/Selena Samuela/S30E11 - 20250103 - 30 min Bootcamp: 50-50")
        
        # Create mock video file with the exact name from the user's example
        mock_video_file = Mock(spec=Path)
        mock_video_file.is_file.return_value = True
        mock_video_file.suffix = ".mp4"
        mock_video_file.stem = "S30E11 - 20250103 - 30 min Bootcamp: 50-50"
        
        mock_iterdir.return_value = [mock_video_file]
        
        # Test can_repair
        can_repair = self.strategy.can_repair(source_path, self.mock_pattern)
        assert can_repair is True, "Should detect the real-world mismatch"
        
        # Test generate_repair_actions
        actions = self.strategy.generate_repair_actions(source_path, self.mock_pattern)
        
        assert len(actions) == 1
        action = actions[0]
        assert action.action_type == "move"
        assert action.source_path == source_path
        assert action.target_path == expected_target
        assert "S30E11 - 20250103 - 30 min Bootcamp: 50-50" in str(action.target_path)
    
    def test_find_video_files_detects_various_formats(self):
        """Test that _find_video_files detects various video formats."""
        mock_dir = Mock(spec=Path)
        
        # Create mock video files with different extensions
        video_files = []
        extensions = ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v']
        
        for ext in extensions:
            mock_file = Mock(spec=Path)
            mock_file.is_file.return_value = True
            mock_file.suffix = ext
            video_files.append(mock_file)
        
        # Add a non-video file
        mock_text_file = Mock(spec=Path)
        mock_text_file.is_file.return_value = True
        mock_text_file.suffix = '.txt'
        
        # Mock directory iteration
        mock_dir.iterdir.return_value = video_files + [mock_text_file]
        
        found_videos = self.strategy._find_video_files(mock_dir)
        
        # Should find all video files but not the text file
        assert len(found_videos) == len(extensions)
        for video_file in found_videos:
            assert video_file.suffix.lower() in {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
    
    def test_find_video_files_handles_os_error(self):
        """Test that _find_video_files handles OSError gracefully."""
        mock_dir = Mock(spec=Path)
        mock_dir.iterdir.side_effect = OSError("Permission denied")
        
        found_videos = self.strategy._find_video_files(mock_dir)
        
        # Should return empty list on error
        assert len(found_videos) == 0
