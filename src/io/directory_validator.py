"""Directory structure validator and repair utility.

This module handles pre-processing validation and repair of the media directory
structure to ensure episode numbering consistency before parsing.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

from .episode_parser import EpisodeParser
from ..core.models import Activity
from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class EpisodeInfo:
    """Information about a single episode file/directory."""
    path: Path
    activity: Activity
    instructor: str
    season: int
    episode: int
    title: str
    is_corrupted_location: bool = False


@dataclass
class ConflictInfo:
    """Information about episode number conflicts."""
    activity: Activity
    season: int
    episode: int
    conflicting_paths: List[Path]


class DirectoryValidator:
    """Validates and repairs media directory structure before parsing."""
    
    def __init__(self, media_dir: str, dry_run: bool = False):
        """Initialize the directory validator.
        
        Args:
            media_dir: Root directory containing downloaded media files
            dry_run: If True, only report issues without making changes
        """
        self.media_dir = Path(media_dir)
        self.dry_run = dry_run
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Activity name mapping from directory names to enum values
        self.activity_map = {a.value.lower(): a for a in Activity}
        
        # Special case mappings for bootcamp variants
        self.special_mappings = {
            "tread bootcamp": Activity.BOOTCAMP,
            "row bootcamp": Activity.ROW_BOOTCAMP,
            "bike bootcamp": Activity.BIKE_BOOTCAMP
        }
    
    def validate_and_repair(self) -> bool:
        """Main entry point to validate and repair directory structure.
        
        Returns:
            True if validation passed or repairs were successful, False otherwise
        """
        if not self.media_dir.exists():
            self.logger.warning(f"Media directory does not exist: {self.media_dir}")
            return True  # Nothing to validate
        
        self.logger.info(f"Starting directory validation and repair: {self.media_dir}")
        
        # Step 1: Scan for all episode files and detect structural issues
        all_episodes = self._scan_all_episodes()
        
        # Step 2: Detect and fix corrupted directory structures (50/50 issues)
        corrupted_episodes = [ep for ep in all_episodes if ep.is_corrupted_location]
        if corrupted_episodes:
            self.logger.warning(f"Found {len(corrupted_episodes)} episodes in corrupted locations")
            if not self._repair_corrupted_locations(corrupted_episodes):
                return False
            # Re-scan after repairs
            all_episodes = self._scan_all_episodes()
        
        # Step 3: Detect episode number conflicts
        conflicts = self._detect_episode_conflicts(all_episodes)
        if conflicts:
            self.logger.warning(f"Found {len(conflicts)} episode number conflicts")
            if not self._resolve_episode_conflicts(conflicts, all_episodes):
                return False
        
        # Step 4: Final validation
        final_episodes = self._scan_all_episodes()
        final_conflicts = self._detect_episode_conflicts(final_episodes)
        
        if final_conflicts:
            self.logger.error(f"Still have {len(final_conflicts)} conflicts after repair!")
            return False
        
        self.logger.info("Directory validation and repair completed successfully")
        return True
    
    def _scan_all_episodes(self) -> List[EpisodeInfo]:
        """Scan all episode directories and extract episode information.
        
        Returns:
            List of EpisodeInfo objects for all found episodes
        """
        episodes = []
        
        for root, dirs, files in os.walk(self.media_dir):
            # Only process leaf directories (no subdirectories)
            if dirs:
                continue
            
            root_path = Path(root)
            episode_info = self._parse_episode_info(root_path)
            if episode_info:
                episodes.append(episode_info)
        
        self.logger.info(f"Found {len(episodes)} total episodes during scan")
        return episodes
    
    def _parse_episode_info(self, path: Path) -> Optional[EpisodeInfo]:
        """Parse episode information from a directory path.
        
        Args:
            path: Path to analyze
            
        Returns:
            EpisodeInfo object or None if parsing fails
        """
        parts = path.parts
        
        # Look for S{season}E{episode} pattern in the folder name
        folder_name = parts[-1]
        episode_match = re.search(r'S(\d+)E(\d+)', folder_name)
        if not episode_match:
            return None
        
        season = int(episode_match.group(1))
        episode = int(episode_match.group(2))
        
        # Extract title from folder name (everything after episode pattern)
        title_match = re.search(r'S\d+E\d+\s*-\s*(.+)', folder_name)
        title = title_match.group(1) if title_match else folder_name
        
        # Determine if this is in a corrupted location by checking directory depth
        # and looking for 50/50 patterns in the path
        is_corrupted = self._is_corrupted_location(path)
        
        # Extract activity and instructor - handle both normal and corrupted structures
        activity, instructor = self._extract_activity_instructor(path, is_corrupted)
        # Note: We still return the episode info even if activity is None
        # This allows us to detect and potentially repair corrupted structures
        
        return EpisodeInfo(
            path=path,
            activity=activity,
            instructor=instructor,
            season=season,
            episode=episode,
            title=title,
            is_corrupted_location=is_corrupted
        )
    
    def _is_corrupted_location(self, path: Path) -> bool:
        """Check if a path represents a corrupted directory structure.
        
        Args:
            path: Path to check
            
        Returns:
            True if the path appears to be in a corrupted location
        """
        path_str = str(path)
        
        # Check for 50/50 patterns in the path
        if ("50/50" in path_str or "/50/" in path_str or "\\50\\" in path_str or
            "50-50" in path_str):
            return True
        
        # Check if the directory depth is wrong (too deep)
        # Expected: media/peloton/{Activity}/{Instructor}/S{season}E{episode}
        # Corrupted: media/peloton/{Activity}/50/{Instructor}/S{season}E{episode}
        parts = path.parts
        
        # Find the "peloton" part and count levels after it
        try:
            peloton_index = next(i for i, part in enumerate(parts) if part.lower() == "peloton")
            levels_after_peloton = len(parts) - peloton_index - 1
            
            # Should be exactly 3 levels: Activity/Instructor/Episode
            if levels_after_peloton > 3:
                return True
        except StopIteration:
            # No "peloton" in path - might be a different structure
            pass
        
        return False
    
    def _extract_activity_instructor(self, path: Path, is_corrupted: bool) -> Tuple[Optional[Activity], str]:
        """Extract activity and instructor from path, handling corrupted structures.
        
        Args:
            path: Path to analyze
            is_corrupted: Whether this path is in a corrupted location
            
        Returns:
            Tuple of (Activity enum, instructor name) or (None, "") if extraction fails
        """
        parts = path.parts
        
        # Find the "peloton" part
        try:
            peloton_index = next(i for i, part in enumerate(parts) if part.lower() == "peloton")
        except StopIteration:
            self.logger.warning(f"No 'peloton' directory found in path: {path}")
            return None, ""
        
        if is_corrupted:
            # For corrupted structures, activity might be split across multiple parts
            # e.g., "Bootcamp 50/50/Instructor" -> activity is "Bootcamp 50"
            activity_parts = []
            instructor_part = None
            
            self.logger.debug(f"Processing corrupted path: {path}")
            self.logger.debug(f"Parts after peloton: {parts[peloton_index + 1:]}")
            
            for i in range(peloton_index + 1, len(parts) - 1):  # Exclude the episode folder
                part = parts[i]
                self.logger.debug(f"Processing part {i}: '{part}'")
                
                if part.isdigit() or part in ["50"]:
                    # This is likely part of the 50/50 corruption, but still part of activity name
                    if activity_parts:  # Only add if we already have activity parts
                        activity_parts.append(part)
                    self.logger.debug(f"  -> Added to activity parts: {activity_parts}")
                elif not activity_parts:
                    # First non-digit part after peloton is likely activity
                    activity_parts.append(part)
                    self.logger.debug(f"  -> Started activity parts: {activity_parts}")
                elif not instructor_part:
                    # This should be the instructor
                    instructor_part = part
                    self.logger.debug(f"  -> Set instructor: {instructor_part}")
                    break
            
            if not activity_parts:
                self.logger.warning(f"Could not extract activity from corrupted path: {path}")
                return None, ""
            
            activity_name = " ".join(activity_parts).lower()
            instructor = instructor_part or "Unknown"
            self.logger.debug(f"Extracted from corrupted path: activity='{activity_name}', instructor='{instructor}'")
        else:
            # Normal structure: peloton/{Activity}/{Instructor}/Episode
            if len(parts) < peloton_index + 3:
                self.logger.warning(f"Path too short to extract activity/instructor: {path}")
                return None, ""
            
            activity_name = parts[peloton_index + 1].lower()
            instructor = parts[peloton_index + 2]
        
        # Map activity name to enum
        activity = self._map_activity_name(activity_name)
        return activity, instructor
    
    def _map_activity_name(self, activity_name: str) -> Optional[Activity]:
        """Map activity name from filesystem to Activity enum.
        
        Args:
            activity_name: Activity name from filesystem (lowercase)
            
        Returns:
            Activity enum or None if not recognized
        """
        # Try direct mapping first
        if activity_name in self.activity_map:
            return self.activity_map[activity_name]
        
        # Try special mappings for bootcamp variants
        if activity_name in self.special_mappings:
            return self.special_mappings[activity_name]
        
        # Handle edge cases from legacy implementation
        # Skip problematic folders with 50/50 pattern (creates extra subdirectories)
        if ("50/50" in activity_name or "50-50" in activity_name or 
            "bootcamp 50" in activity_name.lower() or "bootcamp: 50" in activity_name.lower()):
            self.logger.warning(f"Skipping problematic folder with 50/50 pattern: {activity_name}")
            return None
        
        # If we can't map it, log but don't fail completely (might be fixable)
        self.logger.warning(f"Activity name '{activity_name}' does not map to a known activity")
        return None
    
    def _infer_activity_from_corrupted_path(self, path: Path) -> Optional[Activity]:
        """Try to infer the correct activity from a corrupted path.
        
        Args:
            path: Corrupted path to analyze
            
        Returns:
            Activity enum or None if inference fails
        """
        path_str = str(path).lower()
        
        # Look for activity keywords in the path
        if "bootcamp" in path_str:
            if "bike" in path_str:
                return Activity.BIKE_BOOTCAMP
            elif "row" in path_str:
                return Activity.ROW_BOOTCAMP  
            elif "tread" in path_str:
                return Activity.BOOTCAMP
            else:
                return Activity.BOOTCAMP  # Default bootcamp
        elif "cycling" in path_str or "bike" in path_str:
            return Activity.CYCLING
        elif "strength" in path_str:
            return Activity.STRENGTH
        elif "yoga" in path_str:
            return Activity.YOGA
        elif "running" in path_str or "tread" in path_str:
            return Activity.RUNNING
        elif "walking" in path_str:
            return Activity.WALKING
        elif "rowing" in path_str or "row" in path_str:
            return Activity.ROWING
        elif "cardio" in path_str:
            return Activity.CARDIO
        elif "stretching" in path_str:
            return Activity.STRETCHING
        elif "meditation" in path_str:
            return Activity.MEDITATION
        
        self.logger.warning(f"Could not infer activity from corrupted path: {path}")
        return None
    
    def _detect_episode_conflicts(self, episodes: List[EpisodeInfo]) -> List[ConflictInfo]:
        """Detect episode number conflicts within activity/season combinations.
        
        Args:
            episodes: List of all episodes to check
            
        Returns:
            List of ConflictInfo objects describing conflicts
        """
        conflicts = []
        
        # Group episodes by (activity, season, episode)
        episode_groups = defaultdict(list)
        for ep in episodes:
            if ep.activity:  # Skip episodes with unmappable activities
                key = (ep.activity, ep.season, ep.episode)
                episode_groups[key].append(ep)
        
        # Find groups with multiple episodes (conflicts)
        for (activity, season, episode), episode_list in episode_groups.items():
            if len(episode_list) > 1:
                conflicts.append(ConflictInfo(
                    activity=activity,
                    season=season,
                    episode=episode,
                    conflicting_paths=[ep.path for ep in episode_list]
                ))
        
        return conflicts
    
    def _repair_corrupted_locations(self, corrupted_episodes: List[EpisodeInfo]) -> bool:
        """Repair episodes in corrupted directory locations.
        
        Args:
            corrupted_episodes: List of episodes in corrupted locations
            
        Returns:
            True if repairs were successful, False otherwise
        """
        self.logger.info(f"Repairing {len(corrupted_episodes)} corrupted episode locations")
        
        for episode in corrupted_episodes:
            if not self._move_episode_to_correct_location(episode):
                return False
        
        return True
    
    def _move_episode_to_correct_location(self, episode: EpisodeInfo) -> bool:
        """Move an episode from a corrupted location to the correct location.
        
        Args:
            episode: Episode to move
            
        Returns:
            True if move was successful, False otherwise
        """
        # Try to infer the correct activity if it's None
        activity = episode.activity
        if not activity:
            activity = self._infer_activity_from_corrupted_path(episode.path)
            if not activity:
                self.logger.error(f"Cannot move episode with unknown activity: {episode.path}")
                return False
        
        # Construct the correct target path
        target_dir = (
            self.media_dir / "peloton" / 
            activity.value.title() /
            episode.instructor /
            episode.path.name  # Keep the same episode folder name
        )
        
        self.logger.info(f"Moving episode from corrupted location:")
        self.logger.info(f"  From: {episode.path}")
        self.logger.info(f"  To:   {target_dir}")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would move episode to correct location")
            return True
        
        # Create target parent directory if it doesn't exist
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if target already exists
        if target_dir.exists():
            self.logger.error(f"Target directory already exists: {target_dir}")
            return False
        
        try:
            shutil.move(str(episode.path), str(target_dir))
            self.logger.info(f"Successfully moved episode to correct location")
            return True
        except Exception as e:
            self.logger.error(f"Failed to move episode: {e}")
            return False
    
    def _resolve_episode_conflicts(self, conflicts: List[ConflictInfo], all_episodes: List[EpisodeInfo]) -> bool:
        """Resolve episode number conflicts by renumbering episodes.
        
        Args:
            conflicts: List of conflicts to resolve
            all_episodes: List of all episodes (for finding available numbers)
            
        Returns:
            True if conflicts were resolved, False otherwise
        """
        self.logger.info(f"Resolving {len(conflicts)} episode number conflicts")
        
        for conflict in conflicts:
            if not self._resolve_single_conflict(conflict, all_episodes):
                return False
        
        return True
    
    def _resolve_single_conflict(self, conflict: ConflictInfo, all_episodes: List[EpisodeInfo]) -> bool:
        """Resolve a single episode number conflict.
        
        Args:
            conflict: The conflict to resolve
            all_episodes: List of all episodes (for finding available numbers)
            
        Returns:
            True if conflict was resolved, False otherwise
        """
        self.logger.info(f"Resolving conflict: {conflict.activity.name} S{conflict.season}E{conflict.episode}")
        self.logger.info(f"Conflicting paths: {[str(p) for p in conflict.conflicting_paths]}")
        
        # Find the maximum episode number for this activity/season
        max_episode = 0
        for ep in all_episodes:
            if ep.activity == conflict.activity and ep.season == conflict.season:
                max_episode = max(max_episode, ep.episode)
        
        # Keep the first episode at its current number, renumber the rest
        paths_to_renumber = conflict.conflicting_paths[1:]  # Skip first one
        
        for i, path in enumerate(paths_to_renumber):
            new_episode_number = max_episode + i + 1
            if not self._renumber_episode(path, new_episode_number):
                return False
            max_episode = new_episode_number  # Update for next iteration
        
        return True
    
    def _renumber_episode(self, episode_path: Path, new_episode_number: int) -> bool:
        """Renumber an episode by renaming its directory.
        
        Args:
            episode_path: Path to the episode directory
            new_episode_number: New episode number to assign
            
        Returns:
            True if renumbering was successful, False otherwise
        """
        # Extract season from current path
        folder_name = episode_path.name
        season_match = re.search(r'S(\d+)E\d+', folder_name)
        if not season_match:
            self.logger.error(f"Cannot extract season from folder name: {folder_name}")
            return False
        
        season = int(season_match.group(1))
        
        # Create new folder name with updated episode number
        new_folder_name = re.sub(
            r'S(\d+)E\d+', 
            f'S{season}E{new_episode_number:03d}', 
            folder_name
        )
        
        new_path = episode_path.parent / new_folder_name
        
        self.logger.info(f"Renumbering episode:")
        self.logger.info(f"  From: {episode_path}")
        self.logger.info(f"  To:   {new_path}")
        
        if self.dry_run:
            self.logger.info("DRY RUN: Would renumber episode")
            return True
        
        # Check if target already exists
        if new_path.exists():
            self.logger.error(f"Target directory already exists: {new_path}")
            return False
        
        try:
            episode_path.rename(new_path)
            self.logger.info(f"Successfully renumbered episode")
            return True
        except Exception as e:
            self.logger.error(f"Failed to renumber episode: {e}")
            return False
