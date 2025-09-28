"""Corrupted folder deletion strategy for removing completely corrupted directories."""

import re
from pathlib import Path
from typing import List
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class CorruptedFolderDeletionStrategy(DirectoryRepairStrategy):
    """Repair strategy for deleting completely corrupted folders.
    
    This handles cases where:
    - Folder name is completely corrupted (e.g., just "50")
    - All files in the folder are also corrupted (e.g., "50.mp4", "50.info.json")
    - Solution: Delete the entire folder since it's unrecoverable
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this is a completely corrupted folder that should be deleted.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        if not path.is_dir():
            return False
        
        folder_name = path.name
        
        # Check if folder name is completely corrupted (common patterns)
        corrupted_folder_patterns = [
            r'^50$',        # Just "50"
            r'^50-$',       # "50-"
            r'^\d{1,2}$',   # Any 1-2 digit number
        ]
        
        folder_is_corrupted = any(re.match(pattern, folder_name) for pattern in corrupted_folder_patterns)
        if not folder_is_corrupted:
            return False
        
        # Find all files in the directory
        all_files = self._find_all_files(path)
        if not all_files:
            # Empty corrupted folder - can delete
            self.logger.debug(f"CorruptedFolderDeletionStrategy detected empty corrupted folder: '{folder_name}'")
            return True
        
        # Check if ALL files are also corrupted
        all_files_corrupted = True
        for file_path in all_files:
            file_stem = file_path.stem
            
            # Handle special cases like "-thumb" suffix
            base_stem = file_stem
            if file_stem.endswith('-thumb'):
                base_stem = file_stem[:-6]  # Remove "-thumb"
            
            # If any file has correct SxxExx format, don't delete the folder
            if (len(base_stem) >= 5 and 
                base_stem.startswith('S') and 
                re.search(r'S\d+E\d+', base_stem)):
                all_files_corrupted = False
                break
        
        if all_files_corrupted:
            self.logger.debug(f"CorruptedFolderDeletionStrategy detected completely corrupted folder: '{folder_name}' with {len(all_files)} corrupted files")
            return True
        
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for completely corrupted folders.
        
        Args:
            path: Path that needs repair
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        # Create delete action for the entire folder
        actions.append(RepairAction(
            action_type="delete",
            source_path=path,
            target_path=None,  # No target for delete operations
            reason=f"Delete completely corrupted folder: '{path.name}' and all its corrupted files"
        ))
        
        self.logger.info(f"Deleting completely corrupted folder: {path}")
        
        return actions
    
    def _find_all_files(self, directory: Path) -> List[Path]:
        """Find all files in the given directory.
        
        Args:
            directory: Directory to search for files
            
        Returns:
            List of file paths
        """
        all_files = []
        
        try:
            for item in directory.iterdir():
                if item.is_file():
                    all_files.append(item)
        except OSError as e:
            self.logger.debug(f"Error scanning directory {directory}: {e}")
        
        return all_files
