"""Test the corrupted video filename repair strategy."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from src.io.generic_repair_strategies.corrupted_video_filename_repair_strategy import CorruptedVideoFilenameRepairStrategy
from src.io.media_source_strategy import DirectoryPattern


class TestCorruptedVideoFilenameRepairStrategy:
    """Test the corrupted video filename repair strategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = CorruptedVideoFilenameRepairStrategy()
        self.mock_pattern = MagicMock(spec=DirectoryPattern)
    
    def test_can_repair_detects_corrupted_video_files(self):
        """Test that can_repair detects corrupted video files when folder name is correct."""
        path = Path('/media/peloton/Activity/Instructor/S30E1 - Episode')
        
        # Mock corrupted file
        mock_file = Mock(stem='50')
        
        with patch.object(self.strategy, '_find_all_files', return_value=[mock_file]):
            with patch('pathlib.Path.is_dir', return_value=True):
                result = self.strategy.can_repair(path, self.mock_pattern)
                
                assert result is True
    
    def test_cannot_repair_when_folder_name_has_no_episode_format(self):
        """Test that can_repair returns False when folder name doesn't have SxxExx format."""
        path = Path('/media/peloton/Activity/Instructor/Random Folder')
        
        with patch('pathlib.Path.is_dir', return_value=True):
            result = self.strategy.can_repair(path, self.mock_pattern)
            
            assert result is False
    
    def test_cannot_repair_when_video_files_are_correct(self):
        """Test that can_repair returns False when video files have correct names."""
        path = Path('/media/peloton/Activity/Instructor/S30E1 - Episode')
        
        # Mock correct file
        mock_file = Mock(stem='S30E1 - Episode')
        
        with patch.object(self.strategy, '_find_all_files', return_value=[mock_file]):
            with patch('pathlib.Path.is_dir', return_value=True):
                result = self.strategy.can_repair(path, self.mock_pattern)
                
                assert result is False
    
    def test_cannot_repair_files(self):
        """Test that can_repair returns False for files (not directories)."""
        path = Path('/media/peloton/Activity/Instructor/S30E1 - Episode.mp4')
        
        with patch('pathlib.Path.is_dir', return_value=False):
            result = self.strategy.can_repair(path, self.mock_pattern)
            
            assert result is False
    
    def test_cannot_repair_directories_without_videos(self):
        """Test that can_repair returns False for directories without video files."""
        path = Path('/media/peloton/Activity/Instructor/S30E1 - Episode')
        
        with patch.object(self.strategy, '_find_all_files', return_value=[]):
            with patch('pathlib.Path.is_dir', return_value=True):
                result = self.strategy.can_repair(path, self.mock_pattern)
                
                assert result is False
    
    @patch('pathlib.Path.exists')
    def test_generate_repair_actions_fixes_corrupted_filename(self, mock_exists):
        """Test that generate_repair_actions creates correct repair for corrupted video file."""
        mock_exists.return_value = False  # Target doesn't exist
        
        path = Path('/media/peloton/Activity/Instructor/S30E1 - Episode')
        
        # Mock corrupted file
        mock_file = Mock()
        mock_file.stem = '50'
        mock_file.suffix = '.mp4'
        mock_file.name = '50.mp4'
        mock_file.__str__ = Mock(return_value='/media/peloton/Activity/Instructor/S30E1 - Episode/50.mp4')
        
        with patch.object(self.strategy, '_find_all_files', return_value=[mock_file]):
            actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
            
            assert len(actions) == 1
            action = actions[0]
            assert action.action_type == "move"
            assert action.source_path == mock_file
            assert "Fix corrupted filename: '50.mp4' -> 'S30E1 - Episode.mp4'" in action.reason
    
    @patch('pathlib.Path.exists')
    def test_generate_repair_actions_skips_when_target_exists(self, mock_exists):
        """Test that generate_repair_actions skips repair when target file already exists."""
        mock_exists.return_value = True  # Target exists
        
        path = Path('/media/peloton/Activity/Instructor/S30E1 - Episode')
        
        # Mock corrupted file
        mock_file = Mock()
        mock_file.stem = '50'
        mock_file.suffix = '.mp4'
        
        with patch.object(self.strategy, '_find_all_files', return_value=[mock_file]):
            actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
            
            assert len(actions) == 0
    
    def test_generate_repair_actions_no_files(self):
        """Test that generate_repair_actions returns empty list when no files found."""
        path = Path('/media/peloton/Activity/Instructor/S30E1 - Episode')
        
        with patch.object(self.strategy, '_find_all_files', return_value=[]):
            actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
            
            assert actions == []
    
    def test_real_world_example(self):
        """Test with real-world path example from the log."""
        path = Path('/mnt/cephfs-hdd/data/media/peloton/Row Bootcamp/Katie Wang/S45E24 - 20250218 - 45 min Bootcamp')
        
        # Mock corrupted file (from the log)
        mock_file = Mock(stem='50')
        
        with patch.object(self.strategy, '_find_all_files', return_value=[mock_file]):
            with patch('pathlib.Path.is_dir', return_value=True):
                result = self.strategy.can_repair(path, self.mock_pattern)
                
                assert result is True
    
    def test_find_all_files_detects_all_file_types(self):
        """Test that _find_all_files detects all file types."""
        path = Path('/media/peloton/Activity/Instructor/Episode')
        
        # Mock directory with various files
        mock_files = [
            Mock(is_file=Mock(return_value=True), suffix='.mp4'),
            Mock(is_file=Mock(return_value=True), suffix='.info.json'),
            Mock(is_file=Mock(return_value=True), suffix='.jpg'),
            Mock(is_file=Mock(return_value=True), suffix='.txt'),
            Mock(is_file=Mock(return_value=False), suffix='.mp4'),  # Not a file
        ]
        
        with patch('pathlib.Path.iterdir', return_value=mock_files):
            all_files = self.strategy._find_all_files(path)
            
            assert len(all_files) == 4  # All files except the directory
    
    def test_find_all_files_handles_os_error(self):
        """Test that _find_all_files handles OS errors gracefully."""
        with patch('pathlib.Path.iterdir', side_effect=OSError("Permission denied")):
            path = Path('/media/peloton/Activity/Instructor/Episode')
            
            all_files = self.strategy._find_all_files(path)
            
            assert all_files == []
    
    def test_detects_various_corruption_patterns(self):
        """Test that can_repair detects various corruption patterns."""
        path = Path('/media/peloton/Activity/Instructor/S30E1 - Episode')
        
        corruption_patterns = [
            '50',           # Just "50"
            '',             # Empty name
            'E1',           # No 'S' prefix
            'video',        # Generic name
            'S30',          # Missing episode number
        ]
        
        for corrupted_name in corruption_patterns:
            mock_file = Mock(stem=corrupted_name)
            
            with patch.object(self.strategy, '_find_all_files', return_value=[mock_file]):
                with patch('pathlib.Path.is_dir', return_value=True):
                    result = self.strategy.can_repair(path, self.mock_pattern)
                    
                    assert result is True, f"Should detect corruption in: '{corrupted_name}'"
    
    def test_repairs_all_file_types_in_episode_directory(self):
        """Test that all file types in an episode directory are repaired."""
        path = Path('/media/peloton/Activity/Instructor/S45E21 - Episode')
        
        # Mock all the file types typically found in an episode directory
        mock_files = []
        
        # Create properly configured mock files
        file_configs = [
            ('50', '.mp4', '50.mp4'),
            ('50', '.info.json', '50.info.json'),  
            ('50-thumb', '.jpg', '50-thumb.jpg'),
        ]
        
        for stem, suffix, name in file_configs:
            mock_file = Mock()
            mock_file.stem = stem
            mock_file.suffix = suffix
            mock_file.name = name
            mock_files.append(mock_file)
        
        with patch.object(self.strategy, '_find_all_files', return_value=mock_files):
            with patch('pathlib.Path.exists', return_value=False):
                with patch('pathlib.Path.__truediv__') as mock_div:
                    # Mock the path division to return a proper path object
                    mock_div.return_value = Mock(name='S45E21 - Episode.mp4', exists=Mock(return_value=False))
                    
                    actions = self.strategy.generate_repair_actions(path, self.mock_pattern)
                    
                    assert len(actions) == 3
                    # Just verify we got the expected number of actions
                    # The actual path construction is mocked, so we can't test exact names
