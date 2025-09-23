"""Generic directory validator that uses injected strategies."""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

from .strategy_loader import strategy_loader
from .media_source_strategy import RepairAction
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


class GenericDirectoryValidator:
    """Generic directory validator that uses injected strategies."""
    
    def __init__(self, media_dir: str, validation_strategies: List[str], 
                 repair_strategies: List[str], dry_run: bool = False):
        """Initialize the generic directory validator.
        
        Args:
            media_dir: Root directory containing downloaded media files
            validation_strategies: List of validation strategy module paths
            repair_strategies: List of repair strategy module paths
            dry_run: If True, only report issues without making changes
        """
        self.media_dir = Path(media_dir)
        self.dry_run = dry_run
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Load validation strategies
        self.validation_strategies = []
        for strategy_path in validation_strategies:
            try:
                strategy = strategy_loader.instantiate_strategy(strategy_path)
                self.validation_strategies.append(strategy)
                self.logger.info(f"Loaded validation strategy: {strategy_path}")
            except Exception as e:
                self.logger.error(f"Failed to load validation strategy {strategy_path}: {e}")
        
        # Load repair strategies
        self.repair_strategies = []
        for strategy_path in repair_strategies:
            try:
                strategy = strategy_loader.instantiate_strategy(strategy_path)
                self.repair_strategies.append(strategy)
                self.logger.info(f"Loaded repair strategy: {strategy_path}")
            except Exception as e:
                self.logger.error(f"Failed to load repair strategy {strategy_path}: {e}")
    
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
        all_episodes = self._scan_all_episodes(log_context="initial")
        
        # Step 2: Detect and fix corrupted directory structures
        corrupted_episodes = [ep for ep in all_episodes if ep.is_corrupted_location]
        repaired_corrupted_count = 0
        if corrupted_episodes:
            self.logger.warning(f"Found {len(corrupted_episodes)} episodes in corrupted locations")
            if not self._repair_corrupted_locations(corrupted_episodes):
                return False
            repaired_corrupted_count = len(corrupted_episodes)
            # Re-scan after repairs
            all_episodes = self._scan_all_episodes(log_context="after corruption repair")
        
        # Step 3: Detect episode number conflicts
        conflicts = self._detect_episode_conflicts(all_episodes)
        repaired_conflicts_count = 0
        if conflicts:
            self.logger.warning(f"Found {len(conflicts)} episode number conflicts")
            if not self._resolve_episode_conflicts(conflicts, all_episodes):
                return False
            repaired_conflicts_count = len(conflicts)
        
        # Step 4: Final validation
        final_episodes = self._scan_all_episodes(log_context="final validation")
        final_conflicts = self._detect_episode_conflicts(final_episodes)
        
        if final_conflicts:
            self.logger.error(f"Still have {len(final_conflicts)} conflicts after repair!")
            return False
        
        # Log repair summary
        total_repairs = repaired_corrupted_count + repaired_conflicts_count
        if total_repairs > 0:
            self.logger.info(f"Repaired {total_repairs} directories ({repaired_corrupted_count} corrupted locations, {repaired_conflicts_count} episode conflicts)")
        else:
            self.logger.info("Repaired 0 directories")
        
        self.logger.info("Directory validation and repair completed successfully")
        return True
    
    def _scan_all_episodes(self, log_context: str = "") -> List[EpisodeInfo]:
        """Scan all episode directories and extract episode information.
        
        Args:
            log_context: Optional context for logging (e.g., "initial", "after repair")
        
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
        
        # Only log if context is provided (to avoid duplicate logs)
        if log_context:
            self.logger.info(f"Found {len(episodes)} total episodes during {log_context} scan")
        
        return episodes
    
    def _parse_episode_info(self, path: Path) -> Optional[EpisodeInfo]:
        """Parse episode information using validation strategies.
        
        Args:
            path: Path to analyze
            
        Returns:
            EpisodeInfo object or None if parsing fails
        """
        # Try each validation strategy until one succeeds
        for strategy in self.validation_strategies:
            if hasattr(strategy, 'parse_episode_info'):
                try:
                    parsed = strategy.parse_episode_info(path)
                    if parsed:
                        activity, instructor, season, episode, title = parsed
                        
                        # Check if this path is corrupted
                        is_corrupted = self._is_corrupted_location(path)
                        
                        return EpisodeInfo(
                            path=path,
                            activity=activity,
                            instructor=instructor,
                            season=season,
                            episode=episode,
                            title=title,
                            is_corrupted_location=is_corrupted
                        )
                except Exception as e:
                    self.logger.debug(f"Strategy {strategy.__class__.__name__} failed to parse {path}: {e}")
                    continue
        
        # If normal parsing failed, try to create a corrupted episode info
        # This allows us to detect and repair corrupted structures
        corrupted_info = self._try_parse_corrupted_episode(path)
        if corrupted_info:
            return corrupted_info
        
        return None
    
    def _try_parse_corrupted_episode(self, path: Path) -> Optional[EpisodeInfo]:
        """Try to parse episode info from a potentially corrupted path.
        
        Args:
            path: Path that failed normal parsing
            
        Returns:
            EpisodeInfo for corrupted episode or None
        """
        import re
        
        # Look for S{season}E{episode} pattern in the folder name
        folder_name = path.parts[-1]
        episode_match = re.search(r'S(\d+)E(\d+)', folder_name)
        if not episode_match:
            return None
        
        season = int(episode_match.group(1))
        episode = int(episode_match.group(2))
        
        # Extract title from folder name
        title_match = re.search(r'S\d+E\d+\s*-\s*(.+)', folder_name)
        title = title_match.group(1) if title_match else folder_name
        
        # For corrupted paths, try to infer activity and instructor
        # This is a best-effort attempt for repair purposes
        parts = path.parts
        
        # Try to find activity and instructor from the path parts
        activity = None
        instructor = "Unknown"
        
        # Look for activity keywords in all path parts
        for i, part in enumerate(parts):
            part_lower = part.lower()
            if "bootcamp" in part_lower:
                if "bike" in part_lower:
                    activity = Activity.BIKE_BOOTCAMP
                elif "row" in part_lower:
                    activity = Activity.ROW_BOOTCAMP
                else:
                    activity = Activity.BOOTCAMP
                
                # Try to find instructor in nearby parts
                for j in range(i + 1, len(parts) - 1):  # Exclude episode folder
                    candidate = parts[j]
                    if not candidate.isdigit() and candidate not in ["50"]:
                        instructor = candidate
                        break
                break
            elif part_lower in ["cycling", "strength", "yoga", "running", "walking", "rowing", "meditation", "stretching", "cardio"]:
                activity_map = {a.value.lower(): a for a in Activity}
                activity = activity_map.get(part_lower)
                
                # Instructor should be the next non-problematic part
                for j in range(i + 1, len(parts) - 1):
                    candidate = parts[j]
                    if not candidate.isdigit() and candidate not in ["50"]:
                        instructor = candidate
                        break
                break
        
        if activity:
            return EpisodeInfo(
                path=path,
                activity=activity,
                instructor=instructor,
                season=season,
                episode=episode,
                title=title,
                is_corrupted_location=True  # Mark as corrupted since normal parsing failed
            )
        
        return None
    
    def _is_corrupted_location(self, path: Path) -> bool:
        """Check if a path represents a corrupted directory structure.
        
        Args:
            path: Path to check
            
        Returns:
            True if the path appears to be in a corrupted location
        """
        # Check if any repair strategy can handle this path
        for repair_strategy in self.repair_strategies:
            if hasattr(repair_strategy, 'can_repair'):
                try:
                    if repair_strategy.can_repair(path, None):  # DirectoryPattern not needed for detection
                        return True
                except Exception as e:
                    self.logger.debug(f"Repair strategy {repair_strategy.__class__.__name__} failed to check {path}: {e}")
                    continue
        
        # Check for directory depth issues (too many levels)
        # Expected: {Activity}/{Instructor}/S{season}E{episode} = 3 levels from the actual media content
        try:
            # Check if path is relative to the media directory
            if self.media_dir.exists() and path.is_relative_to(self.media_dir):
                relative_path = path.relative_to(self.media_dir)
                levels = len(relative_path.parts)
                # Should be exactly 3 levels: Activity/Instructor/Episode
                if levels > 3:
                    return True
            else:
                # For non-existent paths or test paths, use a heuristic
                # Count from the end: Episode/Instructor/Activity should be last 3 parts
                parts = path.parts
                if len(parts) > 6:  # Arbitrary threshold for "too deep"
                    return True
        except (ValueError, OSError):
            pass
        
        return False
    
    def _repair_corrupted_locations(self, corrupted_episodes: List[EpisodeInfo]) -> bool:
        """Repair episodes in corrupted directory locations using strategies.
        
        Args:
            corrupted_episodes: List of episodes in corrupted locations
            
        Returns:
            True if repairs were successful, False otherwise
        """
        self.logger.info(f"Repairing {len(corrupted_episodes)} corrupted episode locations")
        
        for episode in corrupted_episodes:
            if not self._repair_single_episode(episode):
                return False
        
        return True
    
    def _repair_single_episode(self, episode: EpisodeInfo) -> bool:
        """Repair a single episode using available repair strategies.
        
        Args:
            episode: Episode to repair
            
        Returns:
            True if repair was successful, False otherwise
        """
        # Try each repair strategy until one succeeds
        for repair_strategy in self.repair_strategies:
            if hasattr(repair_strategy, 'can_repair') and hasattr(repair_strategy, 'generate_repair_actions'):
                try:
                    if repair_strategy.can_repair(episode.path, None):
                        actions = repair_strategy.generate_repair_actions(episode.path, None)
                        
                        if self._execute_repair_actions(actions):
                            self.logger.info(f"Successfully repaired episode using {repair_strategy.__class__.__name__}")
                            return True
                        else:
                            self.logger.warning(f"Failed to execute repair actions from {repair_strategy.__class__.__name__}")
                except Exception as e:
                    self.logger.error(f"Repair strategy {repair_strategy.__class__.__name__} failed: {e}")
                    continue
        
        self.logger.error(f"No repair strategy could handle episode: {episode.path}")
        return False
    
    def _execute_repair_actions(self, actions: List[RepairAction]) -> bool:
        """Execute a list of repair actions.
        
        Args:
            actions: List of repair actions to execute
            
        Returns:
            True if all actions were successful, False otherwise
        """
        if not actions:
            return True
        
        for action in actions:
            self.logger.info(f"Executing repair action: {action.action_type}")
            self.logger.info(f"  Reason: {action.reason}")
            self.logger.info(f"  From: {action.source_path}")
            if action.target_path:
                self.logger.info(f"  To: {action.target_path}")
            
            if self.dry_run:
                self.logger.info("DRY RUN: Would execute repair action")
                continue
            
            try:
                if action.action_type == "move":
                    if not action.target_path:
                        self.logger.error("Move action requires target_path")
                        return False
                    
                    # Store source parent for cleanup
                    source_parent = action.source_path.parent
                    
                    # Create target parent directory if needed
                    action.target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Check if target already exists
                    if action.target_path.exists():
                        self.logger.error(f"Target already exists: {action.target_path}")
                        return False
                    
                    import shutil
                    shutil.move(str(action.source_path), str(action.target_path))
                    
                    # Clean up empty parent directories
                    self._cleanup_empty_directories(source_parent)
                    
                elif action.action_type == "rename":
                    if not action.target_path:
                        self.logger.error("Rename action requires target_path")
                        return False
                    
                    # Store source parent for cleanup if moving to different directory
                    source_parent = action.source_path.parent if action.source_path.parent != action.target_path.parent else None
                    
                    action.source_path.rename(action.target_path)
                    
                    # Clean up empty parent directories if we moved to a different directory
                    if source_parent:
                        self._cleanup_empty_directories(source_parent)
                    
                elif action.action_type == "delete":
                    if action.source_path.is_dir():
                        import shutil
                        shutil.rmtree(action.source_path)
                    else:
                        action.source_path.unlink()
                        
                else:
                    self.logger.error(f"Unknown repair action type: {action.action_type}")
                    return False
                    
            except Exception as e:
                self.logger.error(f"Failed to execute repair action: {e}")
                return False
        
        return True
    
    def _cleanup_empty_directories(self, directory: Path) -> None:
        """Clean up empty parent directories after repair operations.
        
        Args:
            directory: Directory to check and clean up if empty
        """
        try:
            # Don't clean up the media directory itself
            if directory == self.media_dir or not directory.is_relative_to(self.media_dir):
                return
            
            # Check if directory exists and is empty
            if directory.exists() and directory.is_dir():
                try:
                    # Check if directory is empty (no files or subdirectories)
                    if not any(directory.iterdir()):
                        self.logger.info(f"Cleaning up empty directory: {directory}")
                        directory.rmdir()
                        
                        # Recursively clean up parent directories
                        self._cleanup_empty_directories(directory.parent)
                except OSError:
                    # Directory not empty or other OS error, skip
                    pass
        except Exception as e:
            self.logger.debug(f"Failed to cleanup directory {directory}: {e}")
    
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
        import re
        
        # Extract season from current path
        folder_name = episode_path.name
        season_match = re.search(r'S(\d+)E\d+', folder_name)
        if not season_match:
            self.logger.error(f"Cannot extract season from folder name: {folder_name}")
            return False
        
        season = int(season_match.group(1))
        
        # Create new folder name with updated episode number (no leading zeros)
        new_folder_name = re.sub(
            r'S(\d+)E\d+', 
            f'S{season}E{new_episode_number}', 
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
