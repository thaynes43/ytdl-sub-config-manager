"""Episode as activity repair strategy for severe directory corruption."""

import re
from pathlib import Path
from typing import List, Optional
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class EpisodeAsActivityRepairStrategy(DirectoryRepairStrategy):
    """Repair strategy for fixing corruption where episode names become activity names.
    
    This handles cases where:
    - Episode folder name is used as activity name (e.g., 's30e412 - 20250624 - 30 min bootcamp: 50')
    - Creates deeply nested incorrect structure
    - Solution: Move episode to correct activity/instructor structure
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this is an episode-as-activity corruption that can be repaired.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        # Only process directories
        if not path.is_dir():
            return False
        
        parts = path.parts
        
        # Need at least 3 parts to check structure
        if len(parts) < 3:
            return False
        
        # Check if the activity name looks like an episode name
        activity_name = parts[-3].lower()
        
        # Look for episode pattern in activity name (severe corruption indicator)
        if re.search(r's\d+e\d+', activity_name, re.IGNORECASE):
            # Also check if it contains bootcamp keywords
            if 'bootcamp' in activity_name:
                self.logger.debug(f"EpisodeAsActivityRepairStrategy detected episode-as-activity corruption: {path}")
                return True
        
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for episode-as-activity corruption.
        
        Args:
            path: Path that needs repair
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        parts = list(path.parts)
        corrupted_activity_name = parts[-3]
        instructor = parts[-2]
        episode_folder = parts[-1]
        
        self.logger.info(f"Repairing episode-as-activity corruption:")
        self.logger.info(f"  Corrupted activity name: '{corrupted_activity_name}'")
        self.logger.info(f"  Instructor: '{instructor}'")
        self.logger.info(f"  Episode folder: '{episode_folder}'")
        
        # Determine correct activity from the corrupted activity name
        correct_activity = self._infer_correct_activity(corrupted_activity_name)
        if not correct_activity:
            self.logger.error(f"Cannot infer correct activity from: {corrupted_activity_name}")
            return actions
        
        # Create target path with correct structure
        target_parts = parts[:-3] + [correct_activity, instructor, episode_folder]
        target_path = Path(*target_parts)
        
        # Check if target directory already exists
        if target_path.exists():
            self.logger.warning(f"Target directory already exists: {target_path}")
            # Could implement conflict resolution here if needed
            return actions
        
        # Create move action
        actions.append(RepairAction(
            action_type="move",
            source_path=path,
            target_path=target_path,
            reason=f"Fix episode-as-activity corruption: move from '{corrupted_activity_name}' to '{correct_activity}'"
        ))
        
        self.logger.info(f"Moving episode from corrupted structure: {path} -> {target_path}")
        
        return actions
    
    def _infer_correct_activity(self, corrupted_name: str) -> Optional[str]:
        """Infer the correct activity name from a corrupted episode-as-activity name.
        
        Args:
            corrupted_name: Corrupted activity name that looks like an episode
            
        Returns:
            Correct activity name or None
        """
        corrupted_lower = corrupted_name.lower()
        
        # Look for bootcamp keywords to determine correct bootcamp type
        if 'bootcamp' in corrupted_lower:
            if 'bike' in corrupted_lower:
                return "Bike Bootcamp"
            elif 'row' in corrupted_lower:
                return "Row Bootcamp"
            else:
                # Default to Tread Bootcamp for generic bootcamp
                return "Tread Bootcamp"
        
        # Could add other activity mappings here if needed
        # For now, focus on bootcamp corruption since that's what we see in logs
        
        return None
