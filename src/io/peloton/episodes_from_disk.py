"""Episodes from disk parser for Peloton content."""

import os
from pathlib import Path
from typing import Dict, Set
from ..episode_parser import EpisodeParser
from ...core.models import Activity, ActivityData
from ...core.logging import get_logger


class EpisodesFromDisk(EpisodeParser):
    """Parses episode numbers from Peloton files on disk."""
    
    def __init__(self, media_dir: str, path_strategy=None):
        """Initialize the disk episode parser.
        
        Args:
            media_dir: Root directory containing downloaded media files
            path_strategy: Optional path validation strategy (injected)
        """
        super().__init__("filesystem")
        self.media_dir = Path(media_dir)
        self.path_strategy = path_strategy
        self.logger = get_logger(__name__)
    
    def parse_episodes(self) -> Dict[Activity, ActivityData]:
        """Parse episode numbers from the filesystem.
        
        Returns:
            Dictionary mapping Activity to ActivityData with episode information
        """
        if not self.media_dir.exists():
            self.logger.warning(f"Media directory does not exist: {self.media_dir}")
            return {}
        
        self.logger.info(f"Scanning filesystem: {self.media_dir}")
        results = {}
        
        # Walk through all directories looking for episode folders
        for root, dirs, files in os.walk(self.media_dir):
            # Only process leaf directories (no subdirectories)
            if dirs:
                continue
            
            root_path = Path(root)
            
            # Use path strategy if available, otherwise try to parse directly
            if self.path_strategy:
                episode_info = self.path_strategy.parse_episode_info(root_path)
            else:
                episode_info = self._fallback_parse_episode_info(root_path)
            
            if not episode_info:
                continue
            
            activity, instructor, season, episode, title = episode_info
            
            # Initialize ActivityData if needed
            if activity not in results:
                results[activity] = self._create_activity_data(activity)
            
            # Update with this episode
            self._update_activity_data(results[activity], season, episode)
        
        self.logger.info(f"Found {len(results)} activities with episodes on filesystem")
        return results
    
    def find_existing_class_ids(self) -> Set[str]:
        """Find all existing class IDs from .info.json files.
        
        Returns:
            Set of existing class IDs
        """
        if not self.media_dir.exists():
            self.logger.warning(f"Media directory does not exist: {self.media_dir}")
            return set()
        
        self.logger.info(f"Scanning for existing class IDs in: {self.media_dir}")
        class_ids = set()
        
        # Walk through all directories looking for .info.json files
        for root, dirs, files in os.walk(self.media_dir):
            for file in files:
                if file.endswith('.info.json'):
                    # Read the JSON file to extract the actual class ID
                    info_file_path = Path(root) / file
                    try:
                        import json
                        with open(info_file_path, 'r', encoding='utf-8') as f:
                            info_data = json.load(f)
                        
                        # Extract class ID from the JSON content
                        class_id = info_data.get('id')
                        if class_id:
                            class_ids.add(class_id)
                    except Exception as e:
                        self.logger.warning(f"Could not read class ID from {info_file_path}: {e}")
                        continue
        
        self.logger.info(f"Found {len(class_ids)} existing class IDs")
        return class_ids
    
    def _fallback_parse_episode_info(self, path: Path):
        """Fallback episode parsing when no path strategy is available."""
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
        
        # Try to extract activity and instructor from path
        if len(parts) < 3:
            return None
        
        activity_name = parts[-3].lower()
        instructor = parts[-2]
        
        # Simple activity mapping (could be enhanced)
        activity_map = {a.value.lower(): a for a in Activity}
        activity = activity_map.get(activity_name)
        
        if not activity:
            return None
        
        return activity, instructor, season, episode, title
