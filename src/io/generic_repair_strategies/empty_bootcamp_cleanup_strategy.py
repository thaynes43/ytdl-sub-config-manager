"""Empty bootcamp directory cleanup strategy."""

import os
from pathlib import Path
from typing import List
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class EmptyBootcampCleanupStrategy(DirectoryRepairStrategy):
    """Repair strategy for cleaning up empty bootcamp directories.
    
    This handles cases where:
    - Episodes have been moved from incorrect bootcamp folders (Bootcamp, Bike_Bootcamp, Row_Bootcamp)
    - Only empty instructor directories remain
    - Solution: Delete the empty directory structure
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this is an empty bootcamp directory that can be cleaned up.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        # Only process directories
        if not path.is_dir():
            return False
        
        # Check if this is one of the incorrect bootcamp directories
        folder_name = path.name.lower()
        if folder_name not in ["bootcamp", "bike_bootcamp", "row_bootcamp"]:
            return False
        
        # Check if the directory is effectively empty (only contains empty instructor dirs or download archives)
        if self._is_effectively_empty_bootcamp_dir(path):
            self.logger.debug(f"EmptyBootcampCleanupStrategy detected empty bootcamp directory: {path}")
            return True
        
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for empty bootcamp directory cleanup.
        
        Args:
            path: Path that needs repair
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        folder_name = path.name
        
        # Create delete action for the empty directory
        actions.append(RepairAction(
            action_type="delete",
            source_path=path,
            target_path=None,
            reason=f"Delete empty bootcamp directory: '{folder_name}' (episodes already moved to correct location)"
        ))
        
        self.logger.info(f"Cleaning up empty bootcamp directory: {path}")
        
        return actions
    
    def _is_effectively_empty_bootcamp_dir(self, directory: Path) -> bool:
        """Check if a bootcamp directory is effectively empty.
        
        A directory is considered effectively empty if it contains:
        - Only completely empty subdirectories (no files at all)
        - No files anywhere in the directory tree
        - No episode directories (SxxExx pattern)
        
        Args:
            directory: Directory to check
            
        Returns:
            True if directory is effectively empty
        """
        try:
            for root, dirs, files in os.walk(directory):
                # If we find ANY files anywhere, it's not empty
                if files:
                    self.logger.debug(f"Found files in {root}: {files}")
                    return False
                
                # Check for episode directories
                for dir_name in dirs:
                    if self._has_episode_pattern(dir_name):
                        self.logger.debug(f"Found episode directory: {Path(root) / dir_name}")
                        return False
            
            # No files or episode directories found anywhere
            return True
            
        except OSError as e:
            self.logger.warning(f"Error scanning directory {directory}: {e}")
            return False
    
    def _has_episode_pattern(self, name: str) -> bool:
        """Check if a directory name has an episode pattern (SxxExx).
        
        Args:
            name: Directory name to check
            
        Returns:
            True if name contains episode pattern
        """
        import re
        return bool(re.search(r'S\d+E\d+', name))
