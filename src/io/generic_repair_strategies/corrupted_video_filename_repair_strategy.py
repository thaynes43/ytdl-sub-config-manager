"""Corrupted video filename repair strategy for fixing video files with invalid names."""

import re
from pathlib import Path
from typing import List
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class CorruptedVideoFilenameRepairStrategy(DirectoryRepairStrategy):
    """Repair strategy for fixing corrupted video filenames when folder name is correct.
    
    This handles cases where:
    - Folder name has correct SxxExx format (e.g., "S30E1 - Episode Title")
    - Video file has corrupted name (e.g., "50.mp4" from 50/50 corruption)
    - Solution: Rename video file to match folder name
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this directory has corrupted video filenames that can be repaired.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        if not path.is_dir():
            return False
        
        # Check if folder name has correct SxxExx format
        folder_name = path.name
        if not re.search(r'S\d+E\d+', folder_name):
            return False
        
        # Look for all files in the directory
        all_files = self._find_all_files(path)
        if not all_files:
            return False
        
        # Check if any file has corrupted name
        for file_path in all_files:
            file_stem = file_path.stem
            
            # Handle special cases like "-thumb" suffix
            base_stem = file_stem
            if file_stem.endswith('-thumb'):
                base_stem = file_stem[:-6]  # Remove "-thumb"
            
            # If file name is corrupted (doesn't have SxxExx or is too short)
            if (len(base_stem) < 5 or 
                not base_stem.startswith('S') or 
                not re.search(r'S\d+E\d+', base_stem)):
                
                self.logger.debug(f"CorruptedVideoFilenameRepairStrategy detected corrupted file: '{file_stem}' in folder '{folder_name}'")
                return True
        
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for corrupted video filenames.
        
        Args:
            path: Path that needs repair
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        # Find all files in the directory
        all_files = self._find_all_files(path)
        if not all_files:
            self.logger.warning(f"No files found in directory: {path}")
            return actions
        
        folder_name = path.name
        
        # Rename corrupted files to match folder name
        for file_path in all_files:
            file_stem = file_path.stem
            file_extension = file_path.suffix
            
            # Handle special cases like "-thumb" suffix
            base_stem = file_stem
            thumb_suffix = ""
            if file_stem.endswith('-thumb'):
                base_stem = file_stem[:-6]  # Remove "-thumb"
                thumb_suffix = "-thumb"
            
            # Check if this file is corrupted
            if (len(base_stem) < 5 or 
                not base_stem.startswith('S') or 
                not re.search(r'S\d+E\d+', base_stem)):
                
                # Create new filename based on folder name
                # Handle compound extensions like .info.json
                if file_path.name.endswith('.info.json'):
                    new_file_name = folder_name + thumb_suffix + '.info.json'
                else:
                    new_file_name = folder_name + thumb_suffix + file_extension
                target_path = path / new_file_name
                
                # Check if target already exists
                if target_path.exists():
                    self.logger.warning(f"Target file already exists: {target_path}")
                    continue
                
                # Create repair action
                actions.append(RepairAction(
                    action_type="move",
                    source_path=file_path,
                    target_path=target_path,
                    reason=f"Fix corrupted filename: '{file_stem}{file_extension}' -> '{new_file_name}'"
                ))
                
                self.logger.info(f"Repairing corrupted filename: {file_path} -> {target_path}")
        
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
