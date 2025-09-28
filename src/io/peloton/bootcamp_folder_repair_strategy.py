"""Bootcamp folder repair strategy for Peloton content."""

import re
import os
from pathlib import Path
from typing import List, Optional
from ..media_source_strategy import DirectoryRepairStrategy, DirectoryPattern, RepairAction
from ...core.logging import get_logger


class BootcampFolderRepairStrategy(DirectoryRepairStrategy):
    """Repair strategy for fixing bootcamp folder naming issues.
    
    Handles three cases:
    1. Move files from incorrect 'Bootcamp' directory to 'Tread Bootcamp' directory
    2. Move files from 'Bike_Bootcamp' directory to 'Bike Bootcamp' directory  
    3. Move files from 'Row_Bootcamp' directory to 'Row Bootcamp' directory
    """
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this is a bootcamp folder naming issue that can be repaired.
        
        Args:
            path: Path to check
            expected_pattern: Expected directory pattern
            
        Returns:
            True if this strategy can repair the path
        """
        parts = path.parts
        
        # Need at least 3 parts: Activity/Instructor/Episode
        if len(parts) < 3:
            return False
        
        # Check if the activity directory is incorrect bootcamp naming
        activity_name = parts[-3].lower()
        
        # Check for incorrect "Bootcamp" folder (should be "Tread Bootcamp")
        if activity_name == "bootcamp":
            episode_folder = parts[-1]
            if re.search(r'S\d+E\d+', episode_folder):
                self.logger.debug(f"BootcampFolderRepairStrategy detected incorrect Bootcamp directory: {path}")
                return True
        
        # Check for underscore versions that should be space versions
        if activity_name in ["bike_bootcamp", "row_bootcamp"]:
            episode_folder = parts[-1]
            if re.search(r'S\d+E\d+', episode_folder):
                self.logger.debug(f"BootcampFolderRepairStrategy detected underscore folder: {path}")
                return True
        
        # No repair needed - no need to log every directory
        return False
    
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for bootcamp folder naming issue.
        
        Args:
            path: Path that needs repair
            expected_pattern: Expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        actions = []
        
        # Extract current path components
        parts = list(path.parts)
        episode_folder = parts[-1]  # Episode folder
        activity_name = parts[-3].lower()
        
        # Determine the correct target folder name based on current folder
        if activity_name == "bootcamp":
            # Move from "Bootcamp" to "Tread Bootcamp"
            target_activity = "Tread Bootcamp"
            reason = "Move from incorrect 'Bootcamp' to correct 'Tread Bootcamp' directory"
        elif activity_name == "bike_bootcamp":
            # Move from "Bike_Bootcamp" to "Bike Bootcamp"
            target_activity = "Bike Bootcamp"
            reason = "Move from underscore folder 'Bike_Bootcamp' to correct 'Bike Bootcamp' directory"
        elif activity_name == "row_bootcamp":
            # Move from "Row_Bootcamp" to "Row Bootcamp"
            target_activity = "Row Bootcamp"
            reason = "Move from underscore folder 'Row_Bootcamp' to correct 'Row Bootcamp' directory"
        else:
            self.logger.error(f"Unknown bootcamp activity name: {activity_name}")
            return actions
        
        # Create target path with correct folder name
        target_parts = parts[:-3] + [target_activity] + parts[-2:]
        target_path = Path(*target_parts)
        
        # Check if target directory already exists
        if target_path.exists():
            self.logger.warning(f"Target directory already exists: {target_path}")
            
            # Check for episode number conflicts
            new_episode_folder = self._resolve_episode_conflict(target_path, episode_folder)
            if new_episode_folder != episode_folder:
                # Update target path with new episode folder name
                target_parts = parts[:-3] + [target_activity] + parts[-2:-1] + [new_episode_folder]
                target_path = Path(*target_parts)
                self.logger.info(f"Resolved episode conflict: {episode_folder} -> {new_episode_folder}")
        
        # Create the repair action
        actions.append(RepairAction(
            action_type="move",
            source_path=path,
            target_path=target_path,
            reason=reason
        ))
        
        self.logger.info(f"Repairing bootcamp folder naming: {path} -> {target_path}")
        
        return actions
    
    def _resolve_episode_conflict(self, target_dir: Path, episode_folder: str) -> str:
        """Resolve episode number conflicts by finding the next available episode number.
        
        Args:
            target_dir: Target directory path
            episode_folder: Current episode folder name
            
        Returns:
            New episode folder name with resolved conflict
        """
        # Extract current season and episode from folder name
        episode_match = re.search(r'S(\d+)E(\d+)', episode_folder)
        if not episode_match:
            self.logger.warning(f"Could not parse episode number from: {episode_folder}")
            return episode_folder
        
        current_season = int(episode_match.group(1))
        current_episode = int(episode_match.group(2))
        
        # Find the highest episode number for this season in the target directory
        max_episode = 0
        if target_dir.exists():
            try:
                for item in target_dir.iterdir():
                    if item.is_dir():
                        item_match = re.search(r'S(\d+)E(\d+)', item.name)
                        if item_match:
                            item_season = int(item_match.group(1))
                            item_episode = int(item_match.group(2))
                            if item_season == current_season:
                                max_episode = max(max_episode, item_episode)
            except OSError as e:
                self.logger.warning(f"Error scanning target directory {target_dir}: {e}")
        
        # If current episode conflicts, use next available number
        if current_episode <= max_episode:
            new_episode = max_episode + 1
            # Replace the episode number in the folder name
            new_episode_folder = re.sub(
                r'S\d+E\d+',
                f'S{current_season}E{new_episode}',
                episode_folder
            )
            self.logger.info(f"Episode conflict resolved: S{current_season}E{current_episode} -> S{current_season}E{new_episode}")
            return new_episode_folder
        
        # No conflict, return original folder name
        return episode_folder
