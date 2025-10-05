"""File manager that combines filesystem and subscriptions parsing using dependency injection."""

from typing import Dict, Set, List, Optional
from pathlib import Path

from .generic_directory_validator import GenericDirectoryValidator
from .generic_episode_manager import GenericEpisodeManager
from .subscription_history_manager import SubscriptionHistoryManager
from ..core.models import Activity, ActivityData
from ..core.logging import get_logger
from ..webscraper.models import sanitize_for_filesystem

logger = get_logger(__name__)


class FileManager:
    """Manages episode parsing from multiple sources and provides unified interface."""
    
    def __init__(self, media_dir: str, subs_file: str, validate_and_repair: bool = True, 
                 validation_strategies: Optional[List[str]] = None, repair_strategies: Optional[List[str]] = None, 
                 episode_parsers: Optional[List[str]] = None, subscription_timeout_days: int = 15, metrics=None):
        """Initialize the file manager.
        
        Args:
            media_dir: Root directory containing downloaded media files
            subs_file: Path to the subscriptions YAML file
            validate_and_repair: If True, validate and repair directory structure on init
            validation_strategies: List of validation strategy module paths (required if validate_and_repair=True)
            repair_strategies: List of repair strategy module paths (required if validate_and_repair=True)
            episode_parsers: List of episode parser module paths (required)
            subscription_timeout_days: Number of days after which subscriptions are considered stale
            metrics: Optional metrics object to track statistics
        """
        self.media_dir = media_dir
        self.subs_file = subs_file
        
        # Store strategies for later use
        self.validation_strategies = validation_strategies or []
        self.repair_strategies = repair_strategies or []
        self.episode_parsers = episode_parsers or []
        
        # Validate that required strategies are provided
        if validate_and_repair and (not validation_strategies or not repair_strategies):
            raise ValueError("validation_strategies and repair_strategies are required when validate_and_repair=True")
        if not episode_parsers:
            raise ValueError("episode_parsers are required")
        
        # Initialize directory validator
        self.directory_validator = None
        if validate_and_repair:
            self.directory_validator = GenericDirectoryValidator(
                media_dir=media_dir,
                validation_strategies=self.validation_strategies,
                repair_strategies=self.repair_strategies
            )
        
        # Initialize episode manager
        self.episode_manager = GenericEpisodeManager(
            episode_parser_strategies=self.episode_parsers,
            media_dir=media_dir,
            subs_file=subs_file
        )
        
        # Initialize subscription history manager
        self.subscription_history_manager = SubscriptionHistoryManager(
            subs_file_path=subs_file,
            timeout_days=subscription_timeout_days
        )
        
        self.logger = get_logger(__name__)
        
        # Validate and repair directory structure if requested
        if validate_and_repair and self.directory_validator:
            self.logger.info("Validating and repairing directory structure")
            repair_metrics = metrics.directory_repair if metrics else None
            if not self.directory_validator.validate_and_repair(repair_metrics):
                self.logger.error("Directory validation and repair failed!")
                raise RuntimeError("Directory structure validation failed")
    
    def get_merged_episode_data(self) -> Dict[Activity, ActivityData]:
        """Get merged episode data from all configured parsers.
        
        Returns:
            Dictionary mapping Activity to ActivityData with merged episode information
        """
        return self.episode_manager.get_merged_episode_data()
    
    def get_disk_episode_data(self) -> Dict[Activity, ActivityData]:
        """Get episode data from disk only (not subscriptions).
        
        Returns:
            Dictionary mapping Activity to ActivityData with disk-only episode information
        """
        return self.episode_manager.get_disk_episode_data()
    
    def get_subscriptions_episode_data(self) -> Dict[Activity, ActivityData]:
        """Get episode data from subscriptions only (not disk).
        
        Returns:
            Dictionary mapping Activity to ActivityData with subscriptions-only episode information
        """
        return self.episode_manager.get_subscriptions_episode_data()
    
    def get_next_episode_number(self, activity: Activity, season: int) -> int:
        """Get the next available episode number for an activity and season.
        
        Args:
            activity: The activity type
            season: The season (duration in minutes)
            
        Returns:
            The next available episode number
        """
        merged_data = self.get_merged_episode_data()
        
        # Get next episode number directly from merged data
        if activity not in merged_data:
            return 1
        
        activity_data = merged_data[activity]
        current_max = activity_data.max_episode.get(season, 0)
        return current_max + 1
    
    def find_all_existing_class_ids(self) -> Set[str]:
        """Find all existing class IDs from all configured parsers.
        
        Returns:
            Set of all existing class IDs
        """
        return self.episode_manager.find_all_existing_class_ids()
    
    def cleanup_subscriptions(self) -> tuple[bool, int]:
        """Remove already-downloaded classes and stale subscriptions from subscriptions.
        
        Returns:
            Tuple of (True if changes were made, count of episodes removed)
        """
        changes_made = False
        total_removed = 0
        
        # First, clean up already-downloaded classes
        episode_changes, episode_removed = self.episode_manager.cleanup_subscriptions()
        if episode_changes:
            changes_made = True
            total_removed += episode_removed
        
        # Then, clean up stale subscriptions
        stale_ids = self.subscription_history_manager.get_stale_subscription_ids()
        if stale_ids:
            self.logger.info(f"Removing {len(stale_ids)} stale subscriptions (older than {self.subscription_history_manager.timeout_days} days)")
            
            # Remove stale subscriptions from the subscriptions file
            stale_removed = 0
            for parser in self.episode_manager.episode_parsers:
                if 'subscription' in parser.__class__.__name__.lower():
                    try:
                        if hasattr(parser, 'remove_existing_classes'):
                            parser_changed, parser_removed = parser.remove_existing_classes(stale_ids)
                            if parser_changed:
                                changes_made = True
                                stale_removed += parser_removed
                    except Exception as e:
                        self.logger.error(f"Failed to remove stale subscriptions: {e}")
            
            # Remove stale IDs from history file
            if self.subscription_history_manager.remove_subscription_ids(stale_ids):
                self.logger.info("Removed stale subscription IDs from history file")
            
            total_removed += stale_removed
        
        return changes_made, total_removed
    
    def track_new_subscriptions(self, subscription_urls: List[str]) -> bool:
        """Track new subscription URLs in the history file.
        
        Args:
            subscription_urls: List of subscription URLs to track
            
        Returns:
            True if successful, False otherwise
        """
        if not subscription_urls:
            return True
        
        # Extract subscription IDs from URLs
        subscription_ids = self.subscription_history_manager.extract_subscription_ids_from_urls(subscription_urls)
        
        if subscription_ids:
            self.logger.info(f"Tracking {len(subscription_ids)} new subscription IDs in history")
            return self.subscription_history_manager.add_subscription_ids(subscription_ids)
        
        return True
    
    def update_subscription_directories(self, target_media_dir: str) -> bool:
        """Update existing subscription directories to match the configured media directory.
        
        Args:
            target_media_dir: The target media directory from configuration
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import yaml
            
            # Load existing subscriptions
            subs_file_path = Path(self.subs_file)
            if not subs_file_path.exists():
                self.logger.info("No subscriptions file found to update")
                return True
            
            with open(subs_file_path, 'r', encoding='utf-8') as f:
                subs_data = yaml.safe_load(f)
            
            if not subs_data or "Plex TV Show by Date" not in subs_data:
                self.logger.info("No subscription data found to update")
                return True
            
            # Track changes
            updated_count = 0
            target_media_path = target_media_dir.rstrip('/\\')  # Remove trailing separators
            
            # Process each duration section
            for duration_key, episodes in subs_data["Plex TV Show by Date"].items():
                if not isinstance(episodes, dict):
                    continue
                    
                # Process each episode
                for episode_title, episode_data in episodes.items():
                    if not isinstance(episode_data, dict) or "overrides" not in episode_data:
                        continue
                    
                    overrides = episode_data["overrides"]
                    if "tv_show_directory" not in overrides:
                        continue
                    
                    current_dir = overrides["tv_show_directory"]
                    
                    # Extract the relative path (activity/instructor) from current directory
                    # Always use the last two path components (activity/instructor)
                    path_parts = current_dir.replace('\\', '/').split('/')
                    
                    # Filter out empty parts
                    path_parts = [part for part in path_parts if part]
                    
                    if len(path_parts) >= 2:
                        # Use the last two components: activity and instructor
                        relative_path = f"{path_parts[-2]}/{path_parts[-1]}"
                    else:
                        relative_path = None
                    
                    if relative_path:
                        # Construct new directory path
                        new_dir = f"{target_media_path}/{relative_path}"
                        
                        if new_dir != current_dir:
                            overrides["tv_show_directory"] = new_dir
                            updated_count += 1
                            self.logger.debug(f"Updated directory: {current_dir} -> {new_dir}")
            
            if updated_count > 0:
                # Write back to file
                with open(subs_file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True, 
                             default_flow_style=False, indent=2, width=4096)
                
                self.logger.info(f"Updated {updated_count} subscription directories to use {target_media_dir}")
            else:
                self.logger.info("All subscription directories already match the configured media directory")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating subscription directories: {e}")
            return False

    def add_new_subscriptions(self, subscriptions: Dict[str, Dict[str, dict]]) -> bool:
        """Add new subscriptions to the subscriptions file.
        
        Args:
            subscriptions: Nested dictionary structure for merging into subscriptions.yaml
                    Format: {duration_key: {episode_title: episode_data}}
                    
        Returns:
            True if successful, False otherwise
        """
        if not subscriptions:
            self.logger.info("No new subscriptions to add")
            return True
        
        self.logger.info(f"Adding {sum(len(episodes) for episodes in subscriptions.values())} new subscriptions")
        
        try:
            import yaml
            
            # Load existing subscriptions
            subs_file_path = Path(self.subs_file)
            if subs_file_path.exists():
                with open(subs_file_path, 'r', encoding='utf-8') as f:
                    subs_data = yaml.safe_load(f)
            else:
                # Create basic structure if file doesn't exist
                subs_data = {"Plex TV Show by Date": {}}
            
            # Ensure the main section exists
            if "Plex TV Show by Date" not in subs_data:
                subs_data["Plex TV Show by Date"] = {}
            
            # Update the preset to use the configured media directory
            self._update_preset_media_directory(subs_data)
            
            # Merge in new subscriptions
            for header, episodes in subscriptions.items():
                if header not in subs_data["Plex TV Show by Date"]:
                    subs_data["Plex TV Show by Date"][header] = {}
                
                # Add each episode, checking for name conflicts with different class IDs
                for ep_title, ep_data in episodes.items():
                    # Extract class ID from download URL for logging
                    download_url = ep_data.get("download", "")
                    new_class_id = download_url.split('/')[-1] if '/' in download_url else 'UNKNOWN'
                    
                    # Check if episode title already exists with different class ID
                    final_ep_title = ep_title
                    if ep_title in subs_data["Plex TV Show by Date"][header]:
                        existing_episode = subs_data["Plex TV Show by Date"][header][ep_title]
                        existing_url = existing_episode.get("download", "")
                        existing_class_id = existing_url.split('/')[-1] if '/' in existing_url else 'UNKNOWN'
                        
                        if existing_class_id != new_class_id:
                            # Same name, different class ID - append class ID to new episode
                            final_ep_title = f"{ep_title} {new_class_id[:7]}"
                            self.logger.info(f"Deconflicted episode name: '{ep_title}' -> '{final_ep_title}' (class ID conflict: existing {existing_class_id[:7]} vs new {new_class_id[:7]})")
                    
                    subs_data["Plex TV Show by Date"][header][final_ep_title] = ep_data
                    self.logger.debug(f"Added episode: {header} -> {final_ep_title} (class ID: {new_class_id})")
            
            # Write back to file
            with open(subs_file_path, 'w', encoding='utf-8') as f:
                yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True, 
                         default_flow_style=False, indent=2, width=4096)
            
            self.logger.info(f"Successfully updated {self.subs_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding new subscriptions to subscriptions: {e}")
            return False
    
    def _update_preset_media_directory(self, subs_data: dict) -> None:
        """Update the __preset__ section to use the configured media directory.
        
        Args:
            subs_data: The subscriptions data dictionary to update
        """
        # Ensure preset section exists
        if "__preset__" not in subs_data:
            subs_data["__preset__"] = {}
        
        if "overrides" not in subs_data["__preset__"]:
            subs_data["__preset__"]["overrides"] = {}
        
        # Update tv_show_directory to use configured media_dir instead of hardcoded /media/peloton
        current_preset_dir = subs_data["__preset__"]["overrides"].get("tv_show_directory", "/media/peloton")
        configured_media_dir = self.media_dir.rstrip('/\\')
        
        if current_preset_dir != configured_media_dir:
            subs_data["__preset__"]["overrides"]["tv_show_directory"] = configured_media_dir
            self.logger.debug(f"Updated preset tv_show_directory: {current_preset_dir} -> {configured_media_dir}")
        
        # Ensure other preset defaults are maintained
        if "only_recent_date_range" not in subs_data["__preset__"]["overrides"]:
            subs_data["__preset__"]["overrides"]["only_recent_date_range"] = "24months"
        
        if "only_recent_max_files" not in subs_data["__preset__"]["overrides"]:
            subs_data["__preset__"]["overrides"]["only_recent_max_files"] = 300
        
        # Ensure output_options exist with proper structure
        if "output_options" not in subs_data["__preset__"]:
            subs_data["__preset__"]["output_options"] = {
                "output_directory": "{tv_show_directory}",
                "file_name": "S{season_number}E{episode_number} - {upload_date} - {title}/S{season_number}E{episode_number} - {upload_date} - {title}.{ext}",
                "thumbnail_name": "S{season_number}E{episode_number} - {upload_date} - {title}/S{season_number}E{episode_number} - {upload_date} - {title}-thumb.jpg",
                "info_json_name": "S{season_number}E{episode_number} - {upload_date} - {title}/S{season_number}E{episode_number} - {upload_date} - {title}.info.json"
            }
    
    def validate_and_resolve_subscription_conflicts(self) -> bool:
        """Validate subscription file against filesystem and resolve conflicts.
        
        This method checks if any subscriptions would create file paths that conflict
        with existing files on disk. If conflicts are found, episode titles are 
        modified by appending a short hash from the download URL.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import yaml
            import re
            from pathlib import Path
            from ..webscraper.models import extract_class_id_from_url, get_short_hash
            
            # Load existing subscriptions
            subs_file_path = Path(self.subs_file)
            if not subs_file_path.exists():
                self.logger.info("No subscriptions file found to validate")
                return True
            
            with open(subs_file_path, 'r', encoding='utf-8') as f:
                subs_data = yaml.safe_load(f)
            
            if not subs_data or "Plex TV Show by Date" not in subs_data:
                self.logger.info("No subscription data found to validate")
                return True
            
            # Get file naming configuration from subscriptions.yaml
            file_name_template = None
            if "__preset__" in subs_data and "output_options" in subs_data["__preset__"]:
                file_name_template = subs_data["__preset__"]["output_options"].get("file_name", "")
            
            # Default template if not found
            if not file_name_template:
                file_name_template = "S{season_number}E{episode_number} - {upload_date} - {title}/S{season_number}E{episode_number} - {upload_date} - {title}.{ext}"
            
            # Get existing file paths from the filesystem
            existing_file_paths = set()
            media_path = Path(self.media_dir)
            
            if media_path.exists():
                # Walk through all directories and files to find existing content
                import os
                for root, dirs, files in os.walk(media_path):
                    # Check both episode directories and actual files
                    for dir_name in dirs:
                        # Look for episode directory pattern: S{season}E{episode} - {date} - {title}
                        if re.match(r'S\d+E\d+\s*-\s*.+', dir_name):
                            existing_file_paths.add(str(Path(root) / dir_name))
                    
                    # Also check for actual episode files
                    for file_name in files:
                        if re.match(r'S\d+E\d+\s*-\s*.+\.(mp4|mkv|avi|mov)', file_name):
                            existing_file_paths.add(str(Path(root) / file_name))
            
            # Track changes
            titles_sanitized = 0
            conflicts_resolved = 0
            
            # Process each subscription to check for potential conflicts
            for _duration_key, episodes in subs_data["Plex TV Show by Date"].items():
                if not isinstance(episodes, dict):
                    continue
                
                # Track episode titles that need to be updated
                episodes_to_update = {}
                
                for episode_title, episode_data in episodes.items():
                    if not isinstance(episode_data, dict) or "overrides" not in episode_data:
                        continue
                    
                    overrides = episode_data["overrides"]
                    if not all(key in overrides for key in ["tv_show_directory", "season_number", "episode_number"]):
                        continue
                    
                    # Apply filesystem sanitization to subscription title to ensure consistency
                    sanitized_episode_title = sanitize_for_filesystem(episode_title)
                    title_was_sanitized = sanitized_episode_title != episode_title
                    
                    # Construct the expected file paths based on ytdl-sub configuration
                    tv_show_dir = overrides["tv_show_directory"]
                    season = overrides["season_number"]
                    episode = overrides["episode_number"]
                    
                    # Build expected paths based on the file_name template
                    # Template: S{season_number}E{episode_number} - {upload_date} - {title}/S{season_number}E{episode_number} - {upload_date} - {title}.{ext}
                    # Note: Peloton uses no leading zeros (e.g., S20E1 not S20E001)
                    episode_dir_pattern = f"S{season}E{episode} - "  # Directory part
                    episode_file_pattern = f"S{season}E{episode} - "  # File part
                    
                    # Construct expected full paths
                    expected_episode_dir_prefix = f"{tv_show_dir}/S{season}E{episode} - "
                    expected_episode_file_prefix = expected_episode_dir_prefix  # Files are inside the episode directory
                    
                    # Check if any existing path would conflict
                    potential_conflict = False
                    conflicting_path = None
                    
                    for existing_path in existing_file_paths:
                        # Check if this existing path is in the same tv_show_directory
                        if tv_show_dir in existing_path:
                            # Check if it matches the same season/episode pattern
                            if episode_dir_pattern in existing_path or episode_file_pattern in existing_path:
                                # Extract the title part from the existing path
                                existing_path_obj = Path(existing_path)
                                
                                # Try to extract title from directory name or file name
                                if existing_path_obj.is_dir() or existing_path_obj.suffix == "":
                                    # It's a directory - extract from directory name
                                    existing_title_match = re.search(r'S\d+E\d+\s*-\s*\d{4}-\d{2}-\d{2}\s*-\s*(.+)', existing_path_obj.name)
                                else:
                                    # It's a file - extract from file name (remove extension)
                                    file_name_without_ext = existing_path_obj.stem
                                    existing_title_match = re.search(r'S\d+E\d+\s*-\s*\d{4}-\d{2}-\d{2}\s*-\s*(.+)', file_name_without_ext)
                                
                                if existing_title_match:
                                    existing_title = existing_title_match.group(1)
                                    # Check if titles are similar (could cause conflicts)
                                    if self._titles_would_conflict(sanitized_episode_title, existing_title):
                                        potential_conflict = True
                                        conflicting_path = existing_path
                                        break
                    
                    # Apply filesystem sanitization or conflict resolution (or both)
                    needs_update = title_was_sanitized or potential_conflict
                    
                    if needs_update:
                        # Start with sanitized title
                        new_episode_title = sanitized_episode_title
                        
                        # Add hash suffix if there was a conflict
                        if potential_conflict:
                            # Extract class ID from download URL and create short hash
                            download_url = episode_data.get("download", "")
                            class_id = extract_class_id_from_url(download_url)
                            
                            if class_id:
                                # Use first 7 characters of class ID as suffix
                                short_hash = class_id[:7]
                            else:
                                # Fallback: use hash of the URL
                                short_hash = get_short_hash(download_url, 7)
                            
                            new_episode_title = f"{new_episode_title} {short_hash}"
                        
                        episodes_to_update[episode_title] = new_episode_title
                        
                        if title_was_sanitized and potential_conflict:
                            self.logger.info(f"Sanitized and resolved conflict: '{episode_title}' -> '{new_episode_title}' (conflicts with {conflicting_path})")
                            titles_sanitized += 1
                            conflicts_resolved += 1
                        elif title_was_sanitized:
                            self.logger.info(f"Sanitized title: '{episode_title}' -> '{new_episode_title}'")
                            titles_sanitized += 1
                        else:
                            self.logger.info(f"Resolved conflict: '{episode_title}' -> '{new_episode_title}' (conflicts with {conflicting_path})")
                            conflicts_resolved += 1
                
                # Apply updates to episode titles
                for old_title, new_title in episodes_to_update.items():
                    episodes[new_title] = episodes.pop(old_title)
            
            total_changes = titles_sanitized + conflicts_resolved
            if total_changes > 0:
                # Write back to file
                with open(subs_file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True, 
                             default_flow_style=False, indent=2, width=4096)
                
                # Log detailed summary
                if titles_sanitized > 0 and conflicts_resolved > 0:
                    self.logger.info(f"Updated {total_changes} subscription titles: {titles_sanitized} sanitized, {conflicts_resolved} conflicts resolved")
                elif titles_sanitized > 0:
                    self.logger.info(f"Sanitized {titles_sanitized} subscription titles for filesystem safety")
                elif conflicts_resolved > 0:
                    self.logger.info(f"Resolved {conflicts_resolved} subscription path conflicts")
            else:
                self.logger.info("No subscription titles needed sanitization or conflict resolution")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating subscription conflicts: {e}")
            return False
    
    def _titles_would_conflict(self, subscription_title: str, existing_title: str) -> bool:
        """Check if a subscription title would conflict with an existing file title.
        
        Args:
            subscription_title: Title from subscription (e.g., "20 min Ride with Hannah Corbin")
            existing_title: Title from existing file (e.g., "20 min Pop Ride with Hannah Corbin")
            
        Returns:
            True if titles would likely create conflicting paths
        """
        # Normalize both titles for comparison
        sub_normalized = sanitize_for_filesystem(subscription_title.lower())
        existing_normalized = sanitize_for_filesystem(existing_title.lower())
        
        # Extract key components for comparison
        # Remove common words and focus on instructor and activity type
        common_words = {"min", "with", "and", "the", "a", "an", "by", "for", "in", "on", "at"}
        
        def extract_key_words(title):
            words = title.split()
            return [word for word in words if word not in common_words and len(word) > 2]
        
        sub_key_words = set(extract_key_words(sub_normalized))
        existing_key_words = set(extract_key_words(existing_normalized))
        
        # Check for significant overlap that could cause conflicts
        if not sub_key_words or not existing_key_words:
            return False
        
        # Calculate similarity based on shared key words
        shared_words = sub_key_words.intersection(existing_key_words)
        similarity = len(shared_words) / max(len(sub_key_words), len(existing_key_words))
        
        # Consider it a conflict if similarity is high (>60%)
        return similarity > 0.6
    
    def validate_directories(self) -> bool:
        """Validate that required directories and files exist or can be created.
        
        Returns:
            True if validation passes, False otherwise
        """
        issues = []
        
        # Check media directory
        media_path = Path(self.media_dir)
        if not media_path.exists():
            self.logger.warning(f"Media directory does not exist: {media_path}")
            # This might be OK if it's the first run
        elif not media_path.is_dir():
            issues.append(f"Media path is not a directory: {media_path}")
        
        # Check subscriptions file directory
        subs_path = Path(self.subs_file)
        subs_dir = subs_path.parent
        if not subs_dir.exists():
            try:
                subs_dir.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created subscriptions directory: {subs_dir}")
            except Exception as e:
                issues.append(f"Cannot create subscriptions directory {subs_dir}: {e}")
        
        # Check if subscriptions file is readable/writable
        if subs_path.exists():
            if not subs_path.is_file():
                issues.append(f"Subscriptions path is not a file: {subs_path}")
            else:
                try:
                    # Test read access
                    with open(subs_path, 'r') as f:
                        f.read(1)
                    # Test write access
                    with open(subs_path, 'a') as f:
                        pass
                except Exception as e:
                    issues.append(f"Cannot access subscriptions file {subs_path}: {e}")
        
        if issues:
            for issue in issues:
                self.logger.error(issue)
            return False
        
        self.logger.info("Directory validation passed")
        return True
    
    def repair_directory_structure(self, dry_run: bool = False) -> bool:
        """Manually trigger directory structure validation and repair.
        
        Args:
            dry_run: If True, only report issues without making changes
            
        Returns:
            True if validation passed or repairs were successful, False otherwise
        """
        self.logger.info(f"Manual directory repair requested (dry_run={dry_run})")
        
        # Create a new validator instance with the specified dry_run setting
        # Use the same strategies as the main validator
        validator = GenericDirectoryValidator(
            media_dir=self.media_dir,
            validation_strategies=self.validation_strategies,
            repair_strategies=self.repair_strategies,
            dry_run=dry_run
        )
        return validator.validate_and_repair()
