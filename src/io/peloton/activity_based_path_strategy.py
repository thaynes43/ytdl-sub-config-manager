"""Activity-based path validation strategy for Peloton content."""

from pathlib import Path
from typing import Optional, Tuple
from ..media_source_strategy import DirectoryPattern
from ...core.models import Activity
from ...core.logging import get_logger


class ActivityBasedPathStrategy:
    """Validates Peloton directory structure based on Activity/Instructor/Episode pattern."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # Activity name mapping
        self.activity_map = {a.value.lower(): a for a in Activity}
        self.special_mappings = {
            "tread bootcamp": Activity.BOOTCAMP,
            "row bootcamp": Activity.ROW_BOOTCAMP,
            "bike bootcamp": Activity.BIKE_BOOTCAMP
        }
    
    def get_directory_pattern(self) -> DirectoryPattern:
        """Get the expected directory pattern for Peloton content."""
        return DirectoryPattern(
            pattern="{activity}/{instructor}/S{season}E{episode}",
            expected_levels=3,  # Activity/Instructor/Episode
            has_source_subdir=False
        )
    
    def validate_path(self, path: Path) -> bool:
        """Validate if a path matches the expected Peloton structure.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path matches expected structure
        """
        parts = path.parts
        
        # Need at least 3 parts: Activity/Instructor/Episode
        if len(parts) < 3:
            return False
        
        # Check if we can parse episode info
        episode_info = self.parse_episode_info(path)
        return episode_info is not None
    
    def parse_episode_info(self, path: Path) -> Optional[Tuple[Activity, str, int, int, str]]:
        """Parse episode information from a Peloton path.
        
        Args:
            path: Path to parse
            
        Returns:
            Tuple of (activity, instructor, season, episode, title) or None
        """
        import re
        
        parts = path.parts
        
        # Look for S{season}E{episode} pattern in the folder name
        folder_name = parts[-1]
        episode_match = re.search(r'S(\d+)E(\d+)', folder_name)
        if not episode_match:
            return None
        
        season = int(episode_match.group(1))
        episode = int(episode_match.group(2))
        
        # Extract title from folder name
        title_match = re.search(r'S\d+E\d+\s*-\s*(.+)', folder_name)
        title = title_match.group(1) if title_match else folder_name
        
        # Expected structure: {Activity}/{Instructor}/S{season}E{episode}
        if len(parts) < 3:
            self.logger.warning(f"Path too short for Peloton format: {path}")
            return None
        
        # Activity is 2nd to last, Instructor is 3rd to last
        activity_name = parts[-3].lower()
        instructor = parts[-2]
        
        # Map activity name to enum
        activity = self._map_activity_name(activity_name)
        if not activity:
            self.logger.warning(f"  Full path being parsed: {path}")
            self.logger.warning(f"  Path parts: {list(parts)}")
            self.logger.warning(f"  Activity part (parts[-3]): '{parts[-3] if len(parts) >= 3 else 'N/A'}'")
            self.logger.warning(f"  Instructor part (parts[-2]): '{parts[-2] if len(parts) >= 2 else 'N/A'}'")
            self.logger.warning(f"  Episode part (parts[-1]): '{parts[-1] if len(parts) >= 1 else 'N/A'}'")
            return None
        
        return activity, instructor, season, episode, title
    
    def _map_activity_name(self, activity_name: str) -> Optional[Activity]:
        """Map activity name from filesystem to Activity enum."""
        # Try direct mapping first (case-insensitive)
        activity_lower = activity_name.lower()
        if activity_lower in self.activity_map:
            return self.activity_map[activity_lower]
        
        # Try special mappings for bootcamp variants (case-insensitive)
        if activity_lower in self.special_mappings:
            return self.special_mappings[activity_lower]
        
        # Handle edge cases (case-insensitive)
        if any(pattern in activity_lower for pattern in ["50/50", "50-50", "bootcamp 50"]):
            self.logger.warning(f"Problematic activity name with 50/50 pattern: {activity_name}")
            # Try to infer correct activity
            if "bike" in activity_lower:
                return Activity.BIKE_BOOTCAMP
            elif "row" in activity_lower:
                return Activity.ROW_BOOTCAMP
            elif "bootcamp" in activity_lower:
                return Activity.BOOTCAMP
        
        self.logger.warning(f"Unknown activity name: {activity_name}")
        return None
