"""Missing instructor directory repair strategy for Peloton content."""

import re
from pathlib import Path
from typing import List
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class MissingInstructorRepairStrategy(DirectoryRepairStrategy):
    """Repair strategy for episodes missing the instructor directory level."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this is a missing instructor directory issue.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        parts = path.parts
        
        # Check if we have Activity/Episode structure instead of Activity/Instructor/Episode
        if len(parts) < 2:
            return False
        
        # Look for episode pattern in the folder name (last part)
        folder_name = parts[-1]
        episode_match = re.search(r'S(\d+)E(\d+)', folder_name)
        if not episode_match:
            return False
        
        # Check if we're missing the instructor level
        # Expected: Activity/Instructor/Episode, but we have Activity/Episode
        if len(parts) >= 2:
            activity_name = parts[-2].lower()
            # Check if this looks like an activity name
            known_activities = {
                'cycling', 'yoga', 'strength', 'running', 'walking', 
                'stretching', 'meditation', 'cardio', 'rowing',
                'bootcamp', 'bike bootcamp', 'row bootcamp', 'tread bootcamp'
            }
            
            if activity_name in known_activities:
                self.logger.debug(f"Detected missing instructor directory for: {path}")
                return True
        
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for missing instructor directory.
        
        Args:
            path: Path that needs repair
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        # Extract episode information from the folder name
        folder_name = path.parts[-1]
        
        # Extract instructor from the episode title
        # Pattern: S{season}E{episode} - {date} - {title} with {instructor}
        title_match = re.search(r'S\d+E\d+\s*-\s*[^-]+\s*-\s*(.+)', folder_name)
        if not title_match:
            self.logger.warning(f"Could not extract title from folder: {folder_name}")
            return actions
        
        title = title_match.group(1)
        
        # Extract instructor from title (assumes format "... with {instructor}")
        instructor_match = re.search(r'\bwith\s+(.+?)(?:\s+\d+[a-f0-9]{6})?$', title, re.IGNORECASE)
        if not instructor_match:
            self.logger.warning(f"Could not extract instructor from title: {title}")
            return actions
        
        instructor = instructor_match.group(1).strip()
        
        # Create target path with instructor directory
        # Current: Activity/Episode -> Target: Activity/Instructor/Episode
        path_parts = list(path.parts)
        
        # Insert instructor directory before the episode folder
        path_parts.insert(-1, instructor)
        target_path = Path(*path_parts)
        
        actions.append(RepairAction(
            action_type="move",
            source_path=path,
            target_path=target_path,
            reason=f"Add missing instructor directory: {instructor}"
        ))
        
        self.logger.info(f"Generated repair action: {path} -> {target_path}")
        
        return actions
