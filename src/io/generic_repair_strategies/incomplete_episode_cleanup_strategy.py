"""Incomplete episode cleanup strategy for removing episodes with missing required files."""

import re
from pathlib import Path
from typing import List, Set
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class IncompleteEpisodeCleanupStrategy(DirectoryRepairStrategy):
    """Repair strategy for cleaning up incomplete episode directories.
    
    This handles cases where:
    - Episode directory exists but is missing required files
    - Required files: .mp4 (video), .info.json (metadata), -thumb.jpg (thumbnail)
    - Solution: Delete the entire episode directory as a last resort
    
    This runs LAST after all other repair strategies have attempted fixes.
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this is an incomplete episode directory that should be deleted.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        # Only process directories
        if not path.is_dir():
            return False
        
        # Only process episode directories (must have SxxExx pattern)
        folder_name = path.name
        if not self._has_episode_pattern(folder_name):
            return False
        
        # Check if directory is missing required files
        if self._is_incomplete_episode_directory(path):
            self.logger.warning(f"IncompleteEpisodeCleanupStrategy detected incomplete episode: {path}")
            return True
        
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for incomplete episode cleanup.
        
        Args:
            path: Path that needs repair (incomplete episode directory)
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        # Get the expected base name for the episode
        folder_name = path.name
        
        # List what files are missing for logging
        missing_files = self._get_missing_files(path)
        missing_list = ", ".join(missing_files)
        
        # Create delete action for the incomplete episode
        actions.append(RepairAction(
            action_type="delete",
            source_path=path,
            target_path=None,
            reason=f"Delete incomplete episode directory: '{folder_name}' (missing: {missing_list})"
        ))
        
        self.logger.warning(f"Deleting incomplete episode directory: {path} (missing: {missing_list})")
        
        return actions
    
    def _is_incomplete_episode_directory(self, directory: Path) -> bool:
        """Check if an episode directory is missing required files.
        
        Args:
            directory: Episode directory to check
            
        Returns:
            True if directory is missing required files
        """
        folder_name = directory.name
        
        # Expected file patterns based on folder name
        expected_files = {
            f"{folder_name}.mp4",           # Video file
            f"{folder_name}.info.json",     # Metadata file  
            f"{folder_name}-thumb.jpg"      # Thumbnail file
        }
        
        # Check which files actually exist
        existing_files = set()
        try:
            for item in directory.iterdir():
                if item.is_file():
                    existing_files.add(item.name)
        except OSError as e:
            self.logger.debug(f"Error scanning episode directory {directory}: {e}")
            return True  # Assume incomplete if we can't scan
        
        # Check if any required files are missing
        missing_files = expected_files - existing_files
        
        if missing_files:
            self.logger.debug(f"Episode {directory} missing files: {missing_files}")
            return True
        
        return False
    
    def _get_missing_files(self, directory: Path) -> List[str]:
        """Get list of missing required files for an episode directory.
        
        Args:
            directory: Episode directory to check
            
        Returns:
            List of missing file names
        """
        folder_name = directory.name
        
        # Expected file patterns
        expected_files = {
            f"{folder_name}.mp4",
            f"{folder_name}.info.json", 
            f"{folder_name}-thumb.jpg"
        }
        
        # Check which files exist
        existing_files = set()
        try:
            for item in directory.iterdir():
                if item.is_file():
                    existing_files.add(item.name)
        except OSError:
            # If we can't scan, assume all files are missing
            return list(expected_files)
        
        # Return missing files
        missing_files = expected_files - existing_files
        return sorted(list(missing_files))
    
    def _has_episode_pattern(self, name: str) -> bool:
        """Check if a directory name has an episode pattern (SxxExx).
        
        Args:
            name: Directory name to check
            
        Returns:
            True if name contains episode pattern
        """
        return bool(re.search(r'S\d+E\d+', name))
