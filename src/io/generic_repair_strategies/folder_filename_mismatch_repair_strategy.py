"""Folder/filename mismatch repair strategy."""

from pathlib import Path
from typing import List
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class FolderFilenameMismatchRepairStrategy(DirectoryRepairStrategy):
    """Repair strategy for folder/filename mismatches.
    
    This strategy detects when a folder name doesn't match the video file name inside it
    (minus the extension) and repairs the mismatch by renaming the folder to match the file.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this path has a folder/filename mismatch that can be repaired.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        # Only process directories
        if not path.is_dir():
            return False
        
        # Look for video files in the directory
        video_files = self._find_video_files(path)
        if not video_files:
            return False
        
        # Check if any video file name doesn't match the folder name
        folder_name = path.name
        for video_file in video_files:
            video_name_without_ext = video_file.stem  # filename without extension
            
            # Skip corrupted video files (like "50" from 50/50 corruption)
            if len(video_name_without_ext) < 5 or not video_name_without_ext.startswith('S'):
                self.logger.debug(f"FolderFilenameMismatchRepairStrategy skipping corrupted video file: '{video_name_without_ext}'")
                continue
            
            # If folder name doesn't match video name, we can repair it
            if folder_name != video_name_without_ext:
                self.logger.info(f"FolderFilenameMismatchRepairStrategy detected mismatch:")
                self.logger.info(f"  Folder name: '{folder_name}'")
                self.logger.info(f"  Video file name: '{video_name_without_ext}'")
                self.logger.info(f"  Video file path: '{video_file}'")
                return True
        
        # No mismatch detected - no need to log every directory
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for folder/filename mismatches.
        
        Args:
            path: Path that needs repair
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        # Find video files in the directory
        video_files = self._find_video_files(path)
        if not video_files:
            self.logger.warning(f"No video files found in directory: {path}")
            return actions
        
        # Find the first valid video file's name (without extension) as the target folder name
        target_folder_name = None
        folder_name = path.name
        
        self.logger.info(f"Analyzing folder/filename mismatch for: {path}")
        self.logger.info(f"  Current folder name: '{folder_name}'")
        self.logger.info(f"  Found {len(video_files)} video files:")
        
        for video_file in video_files:
            video_name_without_ext = video_file.stem
            self.logger.info(f"    Video file: '{video_file.name}' (stem: '{video_name_without_ext}')")
            
            # Skip corrupted video files (like "50" from 50/50 corruption)
            if len(video_name_without_ext) >= 5 and video_name_without_ext.startswith('S'):
                if not target_folder_name:  # Use the first valid one
                    target_folder_name = video_name_without_ext
                    self.logger.info(f"  Selected video file name as target: '{target_folder_name}'")
        
        if not target_folder_name:
            self.logger.warning(f"No valid video files found in directory: {path}")
            return actions
        
        # Create the target path
        target_path = path.parent / target_folder_name
        
        # Check if target already exists
        if target_path.exists():
            self.logger.warning(f"Target directory already exists: {target_path}")
            # For now, we'll skip repair if target exists
            # In the future, we could implement merging logic
            return actions
        
        # Create repair action
        actions.append(RepairAction(
            action_type="move",
            source_path=path,
            target_path=target_path,
            reason=f"Fix folder/filename mismatch: '{path.name}' -> '{target_folder_name}'"
        ))
        
        self.logger.info(f"Repairing folder/filename mismatch: {path} -> {target_path}")
        
        return actions
    
    def _find_video_files(self, directory: Path) -> List[Path]:
        """Find video files in a directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of video file paths
        """
        video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v'}
        video_files = []
        
        try:
            for item in directory.iterdir():
                if item.is_file() and item.suffix.lower() in video_extensions:
                    video_files.append(item)
        except OSError as e:
            self.logger.error(f"Error scanning directory {directory}: {e}")
        
        return video_files
