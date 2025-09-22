"""Filesystem episode parser for scanning downloaded media directories."""

import os
import re
from typing import Dict, Set
from pathlib import Path

from .episode_parser import EpisodeParser
from ..core.models import Activity, ActivityData
from ..core.logging import get_logger

logger = get_logger(__name__)


class FilesystemEpisodeParser(EpisodeParser):
    """Parses episode numbers from filesystem directory structure."""
    
    def __init__(self, media_dir: str):
        """Initialize the filesystem parser.
        
        Args:
            media_dir: Root directory containing downloaded media files
        """
        super().__init__("filesystem")
        self.media_dir = Path(media_dir)
        
        # Activity name mapping from directory names to enum values
        self.activity_map = {a.value.lower(): a for a in Activity}
        
        # Special case mappings for bootcamp variants
        self.special_mappings = {
            "tread bootcamp": Activity.BOOTCAMP,
            "row bootcamp": Activity.ROW_BOOTCAMP,
            "bike bootcamp": Activity.BIKE_BOOTCAMP
        }
    
    def parse_episodes(self) -> Dict[Activity, ActivityData]:
        """Parse episode numbers from filesystem directory structure.
        
        Scans the media directory for folders matching the pattern:
        /media/peloton/{Activity}/{Instructor}/S{season}E{episode} - {title}/
        
        Returns:
            Dictionary mapping Activity enum to ActivityData objects
        """
        if not self.media_dir.exists():
            self.logger.warning(f"Media directory does not exist: {self.media_dir}")
            return {}
        
        self.logger.info(f"Scanning filesystem: {self.media_dir}")
        results = {}
        
        # Walk through all directories
        for root, dirs, files in os.walk(self.media_dir):
            # Only process leaf directories (no subdirectories)
            if dirs:
                continue
            
            root_path = Path(root)
            
            # Parse season/episode from directory name
            episode_info = self._parse_episode_from_path(root_path)
            if not episode_info:
                continue
            
            activity, season, episode = episode_info
            
            # Initialize ActivityData if needed
            if activity not in results:
                results[activity] = self._create_activity_data(activity)
            
            # Update with this episode
            self._update_activity_data(results[activity], season, episode)
        
        self.logger.info(f"Found {len(results)} activities with episodes on filesystem")
        return results
    
    def _parse_episode_from_path(self, path: Path) -> tuple[Activity, int, int] | None:
        """Parse activity, season, and episode from a filesystem path.
        
        Expected path structure:
        /media/peloton/{Activity}/{Instructor}/S{season}E{episode} - {title}/
        
        Args:
            path: Path to analyze
            
        Returns:
            Tuple of (Activity, season, episode) or None if parsing fails
        """
        parts = path.parts
        
        # Need at least 3 parts after media root: activity, instructor, episode folder
        if len(parts) < 3:
            return None
        
        # Look for S{season}E{episode} pattern in the folder name
        folder_name = parts[-1]
        episode_match = re.search(r'S(\d+)E(\d+)', folder_name)
        if not episode_match:
            self.logger.debug(f"No S{season}E{episode} pattern found in: {folder_name}")
            return None
        
        season = int(episode_match.group(1))
        episode = int(episode_match.group(2))
        
        # Extract activity from path (should be 3rd from end)
        if len(parts) >= 3:
            activity_name = parts[-3].lower()
        else:
            self.logger.warning(f"Cannot extract activity from path: {path}")
            return None
        
        # Map activity name to enum
        activity = self._map_activity_name(activity_name)
        if not activity:
            return None
        
        self.logger.debug(f"Parsed {activity.name} S{season}E{episode} from {path}")
        return activity, season, episode
    
    def _map_activity_name(self, activity_name: str) -> Activity | None:
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
        if "50-50" in activity_name or "bootcamp: 50" in activity_name.lower():
            self.logger.warning(f"Skipping problematic folder with 50-50 pattern: {activity_name}")
            return None
        
        # If we can't map it, this is an error in the legacy implementation
        self.logger.error(f"Activity name '{activity_name}' does not map to a known activity")
        return None
    
    def find_existing_class_ids(self) -> Set[str]:
        """Find existing class IDs from .info.json files.
        
        This method scans for .info.json files and extracts the 'id' field
        to determine which classes have already been downloaded.
        
        Returns:
            Set of class IDs that have been downloaded
        """
        if not self.media_dir.exists():
            self.logger.warning(f"Media directory does not exist: {self.media_dir}")
            return set()
        
        self.logger.info(f"Scanning for existing class IDs in: {self.media_dir}")
        ids = set()
        
        for root, _, files in os.walk(self.media_dir):
            for file in files:
                if file.endswith(".info.json"):
                    file_path = Path(root) / file
                    try:
                        import json
                        with open(file_path, 'r') as f:
                            data = json.load(f)
                            if "id" in data:
                                ids.add(data["id"])
                    except Exception as e:
                        self.logger.error(f"Error reading {file_path}: {e}")
        
        self.logger.info(f"Found {len(ids)} existing class IDs")
        return ids
