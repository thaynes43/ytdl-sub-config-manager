"""Subscriptions YAML parser for extracting episode numbers from ytdl-sub config."""

import re
import yaml
from typing import Dict, Set
from pathlib import Path

from .episode_parser import EpisodeParser
from ..core.models import Activity, ActivityData
from ..core.logging import get_logger

logger = get_logger(__name__)


class SubscriptionsEpisodeParser(EpisodeParser):
    """Parses episode numbers from ytdl-sub subscriptions YAML file."""
    
    def __init__(self, subs_file: str):
        """Initialize the subscriptions parser.
        
        Args:
            subs_file: Path to the subscriptions YAML file
        """
        super().__init__("subscriptions")
        self.subs_file = Path(subs_file)
        
        # Activity name mapping from directory paths to enum values
        self.activity_map = {a.value.lower(): a for a in Activity}
        
        # Special case mappings for bootcamp variants
        self.special_mappings = {
            "tread bootcamp": Activity.BOOTCAMP,
            "row bootcamp": Activity.ROW_BOOTCAMP,
            "bike bootcamp": Activity.BIKE_BOOTCAMP
        }
    
    def parse_episodes(self) -> Dict[Activity, ActivityData]:
        """Parse episode numbers from subscriptions YAML file.
        
        Looks for episode configurations under 'Plex TV Show by Date' with
        overrides containing season_number and episode_number.
        
        Returns:
            Dictionary mapping Activity enum to ActivityData objects
        """
        if not self.subs_file.exists():
            self.logger.warning(f"Subscriptions file does not exist: {self.subs_file}")
            return {}
        
        self.logger.info(f"Parsing subscriptions file: {self.subs_file}")
        
        try:
            with open(self.subs_file, 'r') as f:
                subs_data = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading subscriptions YAML: {e}")
            return {}
        
        results = {}
        
        # Look for the main TV show section
        tv_shows = subs_data.get("Plex TV Show by Date", {})
        if not tv_shows:
            self.logger.warning("No 'Plex TV Show by Date' section found in subscriptions")
            return {}
        
        # Process each duration group (e.g., "= Cycling (20 min)")
        for duration_key, duration_val in tv_shows.items():
            if not isinstance(duration_val, dict):
                continue
            
            # Process each episode in the duration group
            for episode_title, episode_data in duration_val.items():
                episode_info = self._parse_episode_from_config(episode_data)
                if not episode_info:
                    continue
                
                activity, season, episode = episode_info
                
                # Initialize ActivityData if needed
                if activity not in results:
                    results[activity] = self._create_activity_data(activity)
                
                # Update with this episode
                self._update_activity_data(results[activity], season, episode)
        
        self.logger.info(f"Found {len(results)} activities with episodes in subscriptions")
        return results
    
    def _parse_episode_from_config(self, episode_data: dict) -> tuple[Activity, int, int] | None:
        """Parse activity, season, and episode from episode configuration.
        
        Args:
            episode_data: Episode configuration dictionary
            
        Returns:
            Tuple of (Activity, season, episode) or None if parsing fails
        """
        if not isinstance(episode_data, dict):
            return None
        
        overrides = episode_data.get("overrides", {})
        if not overrides:
            return None
        
        # Extract season and episode numbers
        season = overrides.get("season_number")
        episode = overrides.get("episode_number")
        
        if season is None or episode is None:
            return None
        
        # Extract activity from tv_show_directory
        tv_show_directory = overrides.get("tv_show_directory", "")
        activity = self._extract_activity_from_directory(tv_show_directory)
        
        if not activity:
            return None
        
        try:
            season = int(season)
            episode = int(episode)
        except (ValueError, TypeError):
            self.logger.error(f"Invalid season/episode numbers: {season}/{episode}")
            return None
        
        self.logger.debug(f"Parsed {activity.name} S{season}E{episode} from subscriptions")
        return activity, season, episode
    
    def _extract_activity_from_directory(self, tv_show_directory: str) -> Activity | None:
        """Extract activity from tv_show_directory path.
        
        Expected format: /media/peloton/{Activity}/{Instructor}
        
        Args:
            tv_show_directory: Directory path from overrides
            
        Returns:
            Activity enum or None if not recognized
        """
        if not tv_show_directory:
            return None
        
        # Split path and extract activity (should be 4th component)
        # Example: "/media/peloton/Cycling/Hannah Corbin"
        parts = tv_show_directory.split("/")
        if len(parts) < 4:
            self.logger.warning(f"Invalid tv_show_directory format: {tv_show_directory}")
            return None
        
        activity_name = parts[3].lower()
        return self._map_activity_name(activity_name)
    
    def _map_activity_name(self, activity_name: str) -> Activity | None:
        """Map activity name to Activity enum.
        
        Args:
            activity_name: Activity name (lowercase)
            
        Returns:
            Activity enum or None if not recognized
        """
        # Try direct mapping first
        if activity_name in self.activity_map:
            return self.activity_map[activity_name]
        
        # Try special mappings for bootcamp variants
        if activity_name in self.special_mappings:
            return self.special_mappings[activity_name]
        
        self.logger.error(f"Activity name '{activity_name}' does not map to a known activity")
        return None
    
    def find_subscription_class_ids(self) -> Set[str]:
        """Find class IDs that are configured in subscriptions.
        
        This method extracts class IDs from download URLs to determine
        which classes are already configured for download.
        
        Returns:
            Set of class IDs configured in subscriptions
        """
        if not self.subs_file.exists():
            self.logger.warning(f"Subscriptions file does not exist: {self.subs_file}")
            return set()
        
        self.logger.info(f"Scanning for subscription class IDs in: {self.subs_file}")
        
        try:
            with open(self.subs_file, 'r') as f:
                subs_data = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading subscriptions YAML: {e}")
            return set()
        
        ids = set()
        url_pattern = re.compile(r"https://members\.onepeloton\.com/classes/player/([a-f0-9]+)")
        
        # Process all categories
        for cat_key, cat_val in subs_data.items():
            if cat_key.startswith('__') or not isinstance(cat_val, dict):
                continue
            
            # Process duration groups
            for duration_key, duration_val in cat_val.items():
                if not isinstance(duration_val, dict):
                    continue
                
                # Process episodes
                for ep_title, ep_val in duration_val.items():
                    if not isinstance(ep_val, dict):
                        continue
                    
                    url = ep_val.get("download", "")
                    match = url_pattern.match(url)
                    if match:
                        ids.add(match.group(1))
        
        self.logger.info(f"Found {len(ids)} subscription class IDs")
        return ids
    
    def remove_existing_classes(self, existing_class_ids: Set[str]) -> bool:
        """Remove classes that have already been downloaded from subscriptions.
        
        Args:
            existing_class_ids: Set of class IDs that have been downloaded
            
        Returns:
            True if changes were made to the file, False otherwise
        """
        if not self.subs_file.exists():
            self.logger.warning(f"Subscriptions file does not exist: {self.subs_file}")
            return False
        
        self.logger.info(f"Removing {len(existing_class_ids)} existing classes from subscriptions")
        
        try:
            with open(self.subs_file, 'r') as f:
                subs_data = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Error loading subscriptions YAML: {e}")
            return False
        
        changed = False
        url_pattern = re.compile(r'/classes/player/([a-f0-9]+)')
        
        # Process 'Plex TV Show by Date' section
        shows = subs_data.get("Plex TV Show by Date", {})
        for group_key in list(shows.keys()):
            group_dict = shows[group_key]
            if not isinstance(group_dict, dict):
                continue
            
            for title in list(group_dict.keys()):
                item = group_dict[title]
                if not isinstance(item, dict):
                    continue
                
                url = item.get("download", "")
                match = url_pattern.search(url)
                if match:
                    class_id = match.group(1)
                    if class_id in existing_class_ids:
                        self.logger.info(f"Removing already-downloaded class: {title} ({class_id})")
                        del group_dict[title]
                        changed = True
            
            # Remove empty groups
            if not group_dict:
                self.logger.info(f"Removing empty group: {group_key}")
                del shows[group_key]
                changed = True
        
        if changed:
            try:
                with open(self.subs_file, 'w') as f:
                    yaml.dump(subs_data, f, default_flow_style=False, sort_keys=False, 
                             allow_unicode=True, width=4096)
                self.logger.info(f"Updated {self.subs_file} with already-downloaded classes removed")
            except Exception as e:
                self.logger.error(f"Error writing subscriptions YAML: {e}")
                return False
        else:
            self.logger.info("No changes made to subscriptions")
        
        return changed
