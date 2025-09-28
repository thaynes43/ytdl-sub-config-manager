"""Bootcamp instructor files repair strategy for Peloton content."""

import re
from pathlib import Path
from typing import List
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class BootcampInstructorFilesRepairStrategy(DirectoryRepairStrategy):
    """Repair strategy for moving loose instructor files from incorrect bootcamp directories.
    
    This handles cases where:
    - Instructor directories contain loose files (.json archives, etc.)
    - Files need to be moved from incorrect bootcamp folders to correct ones
    - Maintains file integrity for download tracking
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this is an instructor directory with files that need to be moved.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        parts = path.parts
        
        # Need at least 2 parts: Activity/Instructor
        if len(parts) < 2:
            return False
        
        # Check if this is an instructor directory in incorrect bootcamp folder
        activity_name = parts[-2].lower()
        
        # Only handle incorrect bootcamp directories
        if activity_name not in ["bootcamp", "bike_bootcamp", "row_bootcamp"]:
            return False
        
        # Check if directory contains files (not just subdirectories)
        if not path.is_dir():
            return False
        
        try:
            # Look for any files in this instructor directory
            files = [item for item in path.iterdir() if item.is_file()]
            if files:
                self.logger.debug(f"BootcampInstructorFilesRepairStrategy detected instructor files to move: {path}")
                return True
        except OSError as e:
            self.logger.debug(f"Error scanning instructor directory {path}: {e}")
        
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for moving instructor files.
        
        Args:
            path: Path that needs repair (instructor directory)
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        parts = list(path.parts)
        activity_name = parts[-2].lower()
        instructor_name = parts[-1]
        
        # Determine the correct target activity folder
        if activity_name == "bootcamp":
            target_activity = "Tread Bootcamp"
            reason_prefix = "Move instructor files from 'Bootcamp' to 'Tread Bootcamp'"
        elif activity_name == "bike_bootcamp":
            target_activity = "Bike Bootcamp"
            reason_prefix = "Move instructor files from 'Bike_Bootcamp' to 'Bike Bootcamp'"
        elif activity_name == "row_bootcamp":
            target_activity = "Row Bootcamp"
            reason_prefix = "Move instructor files from 'Row_Bootcamp' to 'Row Bootcamp'"
        else:
            self.logger.error(f"Unknown bootcamp activity: {activity_name}")
            return actions
        
        # Create target instructor directory path
        target_parts = parts[:-2] + [target_activity, instructor_name]
        target_instructor_dir = Path(*target_parts)
        
        try:
            # Move all files from source instructor directory to target instructor directory
            for item in path.iterdir():
                if item.is_file():
                    target_file_path = target_instructor_dir / item.name
                    
                    actions.append(RepairAction(
                        action_type="move",
                        source_path=item,
                        target_path=target_file_path,
                        reason=f"{reason_prefix}: '{item.name}'"
                    ))
                    
                    self.logger.info(f"Moving instructor file: {item} -> {target_file_path}")
        
        except OSError as e:
            self.logger.error(f"Error scanning instructor directory {path}: {e}")
        
        return actions
