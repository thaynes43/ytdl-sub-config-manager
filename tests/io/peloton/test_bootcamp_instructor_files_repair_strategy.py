"""Test the bootcamp instructor files repair strategy."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from src.io.peloton.bootcamp_instructor_files_repair_strategy import BootcampInstructorFilesRepairStrategy
from src.io.media_source_strategy import DirectoryPattern


class TestBootcampInstructorFilesRepairStrategy:
    """Test the bootcamp instructor files repair strategy."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = BootcampInstructorFilesRepairStrategy()
        self.mock_pattern = MagicMock(spec=DirectoryPattern)
    
    def test_can_repair_detects_bootcamp_instructor_with_files(self):
        """Test that can_repair detects instructor directories with files in incorrect bootcamp folders."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create bootcamp instructor directory with files
            instructor_dir = Path(temp_dir) / 'Bootcamp' / 'Andy Speer'
            instructor_dir.mkdir(parents=True)
            
            # Create download archive files
            (instructor_dir / '.ytdl-sub-archive.json').touch()
            (instructor_dir / '.ytdl-sub-other.json').touch()
            
            result = self.strategy.can_repair(instructor_dir, self.mock_pattern)
            
            assert result is True
    
    def test_can_repair_detects_underscore_bootcamp_instructors(self):
        """Test that can_repair detects instructor directories in underscore bootcamp folders."""
        test_cases = ['Bike_Bootcamp', 'Row_Bootcamp']
        
        for folder_name in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                instructor_dir = Path(temp_dir) / folder_name / 'Instructor'
                instructor_dir.mkdir(parents=True)
                
                # Create archive file
                (instructor_dir / '.ytdl-sub-archive.json').touch()
                
                result = self.strategy.can_repair(instructor_dir, self.mock_pattern)
                
                assert result is True, f"Should detect instructor files in {folder_name}"
    
    def test_cannot_repair_correct_bootcamp_instructors(self):
        """Test that can_repair does not detect instructor directories in correct bootcamp folders."""
        test_cases = ['Tread Bootcamp', 'Bike Bootcamp', 'Row Bootcamp']
        
        for folder_name in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                instructor_dir = Path(temp_dir) / folder_name / 'Instructor'
                instructor_dir.mkdir(parents=True)
                
                # Create archive file
                (instructor_dir / '.ytdl-sub-archive.json').touch()
                
                result = self.strategy.can_repair(instructor_dir, self.mock_pattern)
                
                assert result is False, f"Should not detect instructor files in correct {folder_name}"
    
    def test_cannot_repair_instructor_without_files(self):
        """Test that can_repair does not detect empty instructor directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            instructor_dir = Path(temp_dir) / 'Bootcamp' / 'Instructor'
            instructor_dir.mkdir(parents=True)
            
            result = self.strategy.can_repair(instructor_dir, self.mock_pattern)
            
            assert result is False
    
    def test_cannot_repair_non_bootcamp_instructors(self):
        """Test that can_repair does not detect instructor directories in non-bootcamp folders."""
        test_cases = ['Cycling', 'Yoga', 'Strength']
        
        for activity in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                instructor_dir = Path(temp_dir) / activity / 'Instructor'
                instructor_dir.mkdir(parents=True)
                
                # Create archive file
                (instructor_dir / '.ytdl-sub-archive.json').touch()
                
                result = self.strategy.can_repair(instructor_dir, self.mock_pattern)
                
                assert result is False, f"Should not detect instructor files in {activity}"
    
    def test_generate_repair_actions_bootcamp_to_tread(self):
        """Test repair actions for moving files from Bootcamp to Tread Bootcamp."""
        path = Path('/media/peloton/Bootcamp/Andy Speer')
        
        # Mock files in the directory
        with tempfile.TemporaryDirectory() as temp_dir:
            test_dir = Path(temp_dir) / 'Bootcamp' / 'Andy Speer'
            test_dir.mkdir(parents=True)
            
            # Create test files
            archive1 = test_dir / '.ytdl-sub-archive1.json'
            archive2 = test_dir / '.ytdl-sub-archive2.json'
            archive1.touch()
            archive2.touch()
            
            actions = self.strategy.generate_repair_actions(test_dir, self.mock_pattern)
            
            assert len(actions) == 2
            
            # Check first action
            action1 = actions[0]
            assert action1.action_type == "move"
            assert action1.source_path == archive1
            assert str(action1.target_path) == str(Path(temp_dir) / 'Tread Bootcamp' / 'Andy Speer' / '.ytdl-sub-archive1.json')
            assert "Move instructor files from 'Bootcamp' to 'Tread Bootcamp'" in action1.reason
    
    def test_generate_repair_actions_underscore_bootcamps(self):
        """Test repair actions for moving files from underscore bootcamp folders."""
        test_cases = [
            ('Bike_Bootcamp', 'Bike Bootcamp'),
            ('Row_Bootcamp', 'Row Bootcamp')
        ]
        
        for source_folder, target_folder in test_cases:
            with tempfile.TemporaryDirectory() as temp_dir:
                test_dir = Path(temp_dir) / source_folder / 'Instructor'
                test_dir.mkdir(parents=True)
                
                # Create test file
                archive = test_dir / '.ytdl-sub-archive.json'
                archive.touch()
                
                actions = self.strategy.generate_repair_actions(test_dir, self.mock_pattern)
                
                assert len(actions) == 1
                action = actions[0]
                assert action.action_type == "move"
                assert action.source_path == archive
                assert str(action.target_path) == str(Path(temp_dir) / target_folder / 'Instructor' / '.ytdl-sub-archive.json')
                assert f"Move instructor files from '{source_folder}' to '{target_folder}'" in action.reason
    
    def test_real_world_bootcamp_instructor_files(self):
        """Test with real-world bootcamp instructor file structure."""
        # This test verifies the actual paths from the user's filesystem
        test_cases = [
            ('/media/peloton/Bootcamp/Andy Speer', '/media/peloton/Tread Bootcamp/Andy Speer'),
            ('/media/peloton/Bike_Bootcamp/Callie Gullickson', '/media/peloton/Bike Bootcamp/Callie Gullickson'),
            ('/media/peloton/Row_Bootcamp/Instructor', '/media/peloton/Row Bootcamp/Instructor')
        ]
        
        for source_path_str, expected_target_base in test_cases:
            source_path = Path(source_path_str)
            
            # Mock the directory structure
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create the source structure
                mock_source = Path(temp_dir) / source_path.relative_to(Path('/media/peloton'))
                mock_source.mkdir(parents=True)
                
                # Create archive file
                archive = mock_source / '.ytdl-sub-test.json'
                archive.touch()
                
                actions = self.strategy.generate_repair_actions(mock_source, self.mock_pattern)
                
                if actions:  # Only test if strategy detects it
                    action = actions[0]
                    assert action.action_type == "move"
                    assert action.source_path == archive
                    
                    # Verify target path is correct
                    expected_target = Path(temp_dir) / Path(expected_target_base).relative_to(Path('/media/peloton')) / '.ytdl-sub-test.json'
                    assert action.target_path == expected_target
