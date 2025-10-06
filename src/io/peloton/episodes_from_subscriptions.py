"""Episodes from subscriptions parser for Peloton content."""

import re
import yaml
from pathlib import Path
from typing import Dict, Set
from ..episode_parser import EpisodeParser
from ...core.models import Activity, ActivityData
from ...core.logging import get_logger


class EpisodesFromSubscriptions(EpisodeParser):
    """Parses episode numbers from ytdl-sub subscriptions YAML files."""
    
    def __init__(self, subs_file: str):
        """Initialize the subscriptions parser.
        
        Args:
            subs_file: Path to the subscriptions YAML file
        """
        super().__init__("subscriptions")
        self.subs_file = Path(subs_file)
        self.logger = get_logger(__name__)
    
    def parse_episodes(self) -> Dict[Activity, ActivityData]:
        """Parse episode numbers from the subscriptions YAML file.
        
        Returns:
            Dictionary mapping Activity to ActivityData with episode information
        """
        if not self.subs_file.exists():
            self.logger.warning(f"Subscriptions file does not exist: {self.subs_file}")
            return {}
        
        self.logger.info(f"Parsing subscriptions file: {self.subs_file}")
        try:
            with open(self.subs_file, 'r', encoding='utf-8') as f:
                subs_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing subscriptions YAML file {self.subs_file}: {e}")
            return {}
        
        # Handle case where YAML is empty or None
        if not subs_data:
            self.logger.warning("Subscriptions file is empty or invalid")
            return {}
        
        results = {}
        total_episodes = 0
        
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
                total_episodes += 1
                
                # Initialize ActivityData if needed
                if activity not in results:
                    results[activity] = self._create_activity_data(activity)
                
                # Update with this episode
                self._update_activity_data(results[activity], season, episode)
        
        # Log summary
        if results:
            activity_summary = []
            for activity, data in results.items():
                episode_count = sum(data.episode_count.values())
                activity_summary.append(f"{activity.name.lower()} ({episode_count})")
            
            self.logger.info(f"Parsed {total_episodes} total episodes for activities: {', '.join(activity_summary)}")
            
            # Log detailed breakdown for each activity
            for activity, data in results.items():
                seasons_info = []
                for season in sorted(data.max_episode.keys()):
                    actual_count = data.episode_count.get(season, 0)
                    max_ep = data.max_episode.get(season, 0)
                    seasons_info.append(f"Season {season}: {actual_count} episodes (max E{max_ep})")
                
                self.logger.info(f"{activity.name} episodes: {'; '.join(seasons_info)}")
        else:
            self.logger.info("No episodes found in subscriptions")
        
        return results
    
    def find_subscription_class_ids(self) -> Set[str]:
        """Find all class IDs from the subscriptions YAML file.
        
        Returns:
            Set of class IDs found in subscriptions
        """
        if not self.subs_file.exists():
            self.logger.warning(f"Subscriptions file does not exist: {self.subs_file}")
            return set()
        
        self.logger.info(f"Scanning for subscription class IDs in: {self.subs_file}")
        class_ids = set()
        
        try:
            with open(self.subs_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find class IDs from URLs (more specific pattern)
            # Look for patterns like /classes/player/{class_id} or /player/{class_id}
            url_class_id_pattern = r'/(?:classes/)?player/([a-zA-Z0-9]+)'
            url_matches = re.findall(url_class_id_pattern, content)
            
            # Add URL-based class IDs
            for match in url_matches:
                if len(match) >= 6 and match.isalnum():
                    class_ids.add(match)
            
            # Fallback: Look for standalone alphanumeric strings that could be class IDs
            # But be more restrictive to avoid false positives
            if not class_ids:
                fallback_pattern = r'\b[a-z0-9]{6,12}\b'  # Lowercase only, reasonable length
                fallback_matches = re.findall(fallback_pattern, content)
                for match in fallback_matches:
                    if match.isalnum() and not match.isdigit():  # Exclude pure numbers
                        class_ids.add(match)
        
        except Exception as e:
            self.logger.error(f"Error scanning subscriptions file for class IDs: {e}")
            return set()
        
        self.logger.info(f"Found {len(class_ids)} subscription class IDs")
        return class_ids
    
    def _parse_episode_from_config(self, episode_data):
        """Parse episode information from a subscription config entry."""
        if not isinstance(episode_data, dict):
            return None
        
        # Look for URL in download field (ytdl-sub format)
        url = episode_data.get('download', '') or episode_data.get('url', '')
        if not url:
            return None
        
        # Check for overrides section which contains the episode info
        overrides = episode_data.get('overrides', {})
        if overrides:
            # Extract from overrides (direct format)
            season = overrides.get('season_number')
            episode = overrides.get('episode_number')
            tv_show_dir = overrides.get('tv_show_directory', '')
            
            if season and episode and tv_show_dir:
                # Extract activity from tv_show_directory path
                # Example: /media/peloton/Cycling/Hannah Frankson
                path_parts = tv_show_dir.split('/')
                if len(path_parts) >= 2:
                    activity_name = path_parts[-2].lower()  # Second to last is activity
                    
                    # Map to activity enum with special mappings for bootcamp variants
                    activity_map = {a.value.lower(): a for a in Activity}
                    special_mappings = {
                        "tread bootcamp": Activity.BOOTCAMP,
                        "row bootcamp": Activity.ROW_BOOTCAMP,
                        "bike bootcamp": Activity.BIKE_BOOTCAMP
                    }
                    
                    activity = activity_map.get(activity_name) or special_mappings.get(activity_name)
                    
                    if activity:
                        return activity, season, episode
        
        # Fallback: Parse activity and season from URL patterns
        # Example: /classes/cycling/20min/...
        url_parts = url.split('/')
        
        activity = None
        season = None
        
        # Try to find activity in URL
        for i, part in enumerate(url_parts):
            if part in ['cycling', 'strength', 'yoga', 'running', 'walking', 'rowing', 'meditation', 'stretching', 'cardio', 'bootcamp']:
                activity_name = part
                activity_map = {a.value.lower(): a for a in Activity}
                special_mappings = {
                    "bootcamp": Activity.BOOTCAMP  # Default bootcamp maps to tread bootcamp
                }
                activity = activity_map.get(activity_name) or special_mappings.get(activity_name)
                
                # Try to find duration (season) in next parts
                if i + 1 < len(url_parts):
                    duration_part = url_parts[i + 1]
                    # Extract minutes from strings like "20min", "30-min", etc.
                    duration_match = re.search(r'(\d+)', duration_part)
                    if duration_match:
                        season = int(duration_match.group(1))
                
                break
        
        # If we couldn't parse from URL, return None
        if not activity or not season:
            return None
        
        # For episode number, use 1 as default (will be updated by merger)
        episode = 1
        
        return activity, season, episode
    
    def find_subscription_class_ids_for_activity(self, activity) -> Set[str]:
        """Find all class IDs in subscriptions for a specific activity.
        
        Args:
            activity: The Activity enum to find class IDs for
            
        Returns:
            Set of class IDs found in subscriptions for this activity
        """
        if not self.subs_file.exists():
            self.logger.warning(f"Subscriptions file does not exist: {self.subs_file}")
            return set()
        
        self.logger.debug(f"Finding subscription class IDs for activity: {activity.name}")
        
        try:
            with open(self.subs_file, 'r', encoding='utf-8') as f:
                subs_data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing subscriptions YAML file {self.subs_file}: {e}")
            return set()
        
        if not subs_data:
            return set()
        
        class_ids = set()
        tv_shows = subs_data.get("Plex TV Show by Date", {})
        
        # Process each duration group looking for this activity
        for duration_key, duration_episodes in tv_shows.items():
            if not isinstance(duration_episodes, dict):
                continue
            
            # Check if this duration group matches our activity
            # Duration keys look like "= Cycling (20 min)", "= Strength (30 min)", etc.
            if activity.name.lower() in duration_key.lower():
                # Extract class IDs from all episodes in this duration group
                for episode_title, episode_data in duration_episodes.items():
                    if isinstance(episode_data, dict):
                        download_url = episode_data.get('download', '')
                        # Extract class ID from URL like "https://members.onepeloton.com/classes/player/abc123"
                        if '/classes/player/' in download_url:
                            class_id = download_url.split('/classes/player/')[-1].split('?')[0].split('#')[0]
                            if class_id:
                                class_ids.add(class_id)
                        # Also handle legacy format with classId parameter
                        elif 'classId=' in download_url:
                            class_id = download_url.split('classId=')[-1].split('&')[0]
                            if class_id:
                                class_ids.add(class_id)
        
        self.logger.debug(f"Found {len(class_ids)} subscription class IDs for {activity.name}")
        return class_ids
    
    def remove_existing_classes(self, existing_class_ids: Set[str]) -> tuple[bool, int]:
        """Remove existing class IDs from the subscriptions file.
        
        Args:
            existing_class_ids: Set of class IDs to remove
            
        Returns:
            Tuple of (True if changes were made, count of episodes removed)
        """
        if not self.subs_file.exists():
            self.logger.warning(f"Subscriptions file does not exist: {self.subs_file}")
            return False, 0
        
        if not existing_class_ids:
            self.logger.info("No existing class IDs to remove")
            return False, 0
        
        self.logger.info(f"Removing {len(existing_class_ids)} existing classes from subscriptions")
        
        try:
            # Read and parse the YAML file
            with open(self.subs_file, 'r', encoding='utf-8') as f:
                subs_data = yaml.safe_load(f)
            
            if not subs_data:
                self.logger.warning("Subscriptions file is empty or invalid")
                return False, 0
            
            changes_made = False
            removed_episodes = []
            
            # Look for the main TV show section
            tv_shows = subs_data.get("Plex TV Show by Date", {})
            if not tv_shows:
                self.logger.warning("No 'Plex TV Show by Date' section found in subscriptions")
                return False, 0
            
            # Process each duration group (e.g., "= Cycling (20 min)")
            # Create a list of duration keys to avoid modifying dict during iteration
            duration_keys_to_process = list(tv_shows.keys())
            duration_groups_to_remove = []
            
            for duration_key in duration_keys_to_process:
                duration_episodes = tv_shows[duration_key]
                if not isinstance(duration_episodes, dict):
                    continue
                
                # Find episodes to remove (iterate over a copy since we'll modify the dict)
                episodes_to_remove = []
                for episode_title, episode_data in duration_episodes.items():
                    if not isinstance(episode_data, dict):
                        continue
                    
                    # Check if this episode's URL contains any of the existing class IDs
                    download_url = episode_data.get('download', '')
                    for class_id in existing_class_ids:
                        if class_id in download_url:
                            episodes_to_remove.append(episode_title)
                            removed_episodes.append(f"{episode_title} (class ID: {class_id}) from {duration_key}")
                            break
                
                # Remove the episodes
                for episode_title in episodes_to_remove:
                    del duration_episodes[episode_title]
                    changes_made = True
                
                # If the duration group is now empty, mark it for removal
                if not duration_episodes:
                    duration_groups_to_remove.append(duration_key)
                    self.logger.info(f"Removed empty duration group: {duration_key}")
            
            # Remove empty duration groups after iteration is complete
            for duration_key in duration_groups_to_remove:
                del tv_shows[duration_key]
            
            # Write back the modified YAML if changes were made
            if changes_made:
                with open(self.subs_file, 'w', encoding='utf-8') as f:
                    yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True,
                             default_flow_style=False, indent=2, width=4096)
                
                self.logger.info(f"Removed {len(removed_episodes)} episodes from subscriptions:")
                for episode in removed_episodes:
                    self.logger.info(f"  - {episode}")
                
                return True, len(removed_episodes)
            else:
                self.logger.info("No matching episodes found to remove")
                return False, 0
                
        except Exception as e:
            self.logger.error(f"Error updating subscriptions file: {e}")
            return False, 0
