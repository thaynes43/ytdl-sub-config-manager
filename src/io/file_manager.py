"""File manager that combines filesystem and subscriptions parsing."""

from typing import Dict, Set
from pathlib import Path

from .episode_parser import EpisodeMerger
from .filesystem_parser import FilesystemEpisodeParser
from .subscriptions_parser import SubscriptionsEpisodeParser
from ..core.models import Activity, ActivityData
from ..core.logging import get_logger

logger = get_logger(__name__)


class FileManager:
    """Manages episode parsing from multiple sources and provides unified interface."""
    
    def __init__(self, media_dir: str, subs_file: str, validate_and_repair: bool = True):
        """Initialize the file manager.
        
        Args:
            media_dir: Root directory containing downloaded media files
            subs_file: Path to the subscriptions YAML file
            validate_and_repair: If True, validate and repair directory structure on init
        """
        self.media_dir = media_dir
        self.subs_file = subs_file
        
        # Initialize directory validator (lazy import to avoid circular imports)
        self.directory_validator = None
        if validate_and_repair:
            from .directory_validator import DirectoryValidator
            self.directory_validator = DirectoryValidator(media_dir)
        
        # Initialize parsers
        self.filesystem_parser = FilesystemEpisodeParser(media_dir)
        self.subscriptions_parser = SubscriptionsEpisodeParser(subs_file)
        self.episode_merger = EpisodeMerger()
        
        self.logger = get_logger(__name__)
        
        # Validate and repair directory structure if requested
        if validate_and_repair and self.directory_validator:
            self.logger.info("Validating and repairing directory structure")
            if not self.directory_validator.validate_and_repair():
                self.logger.error("Directory validation and repair failed!")
                raise RuntimeError("Directory structure validation failed")
    
    def get_merged_episode_data(self) -> Dict[Activity, ActivityData]:
        """Get merged episode data from all sources.
        
        Returns:
            Dictionary mapping Activity to ActivityData with max episode numbers
        """
        self.logger.info("Gathering episode data from all sources")
        
        # Parse from filesystem
        filesystem_data = self.filesystem_parser.parse_episodes()
        self.logger.info(f"Filesystem: {len(filesystem_data)} activities")
        
        # Parse from subscriptions
        subscriptions_data = self.subscriptions_parser.parse_episodes()
        self.logger.info(f"Subscriptions: {len(subscriptions_data)} activities")
        
        # Merge the data
        merged_data = self.episode_merger.merge_sources(filesystem_data, subscriptions_data)
        self.logger.info(f"Merged: {len(merged_data)} activities")
        
        return merged_data
    
    def get_next_episode_number(self, activity: Activity, season: int) -> int:
        """Get the next available episode number for an activity and season.
        
        Args:
            activity: The activity type
            season: The season (duration in minutes)
            
        Returns:
            The next available episode number
        """
        merged_data = self.get_merged_episode_data()
        return self.episode_merger.get_next_episode_number(merged_data, activity, season)
    
    def find_all_existing_class_ids(self) -> Set[str]:
        """Find all existing class IDs from both filesystem and subscriptions.
        
        Returns:
            Set of all class IDs that exist or are configured
        """
        self.logger.info("Finding all existing class IDs")
        
        # Get IDs from filesystem
        filesystem_ids = self.filesystem_parser.find_existing_class_ids()
        
        # Get IDs from subscriptions
        subscription_ids = self.subscriptions_parser.find_subscription_class_ids()
        
        # Combine both sets
        all_ids = filesystem_ids | subscription_ids
        
        self.logger.info(f"Total existing class IDs: {len(all_ids)} "
                        f"(filesystem: {len(filesystem_ids)}, subscriptions: {len(subscription_ids)})")
        
        return all_ids
    
    def cleanup_subscriptions(self) -> bool:
        """Remove already-downloaded classes from subscriptions.
        
        Returns:
            True if changes were made, False otherwise
        """
        self.logger.info("Cleaning up subscriptions file")
        
        # Get existing class IDs from filesystem
        existing_ids = self.filesystem_parser.find_existing_class_ids()
        
        # Remove them from subscriptions
        return self.subscriptions_parser.remove_existing_classes(existing_ids)
    
    def add_new_classes(self, classes: Dict[str, Dict[str, dict]]) -> bool:
        """Add new classes to the subscriptions file.
        
        Args:
            classes: Nested dictionary structure for merging into subscriptions.yaml
                    Format: {duration_key: {episode_title: episode_data}}
                    
        Returns:
            True if successful, False otherwise
        """
        if not classes:
            self.logger.info("No new classes to add")
            return True
        
        self.logger.info(f"Adding {sum(len(episodes) for episodes in classes.values())} new classes")
        
        try:
            import yaml
            
            # Load existing subscriptions
            subs_file_path = Path(self.subs_file)
            if subs_file_path.exists():
                with open(subs_file_path, 'r') as f:
                    subs_data = yaml.safe_load(f)
            else:
                # Create basic structure if file doesn't exist
                subs_data = {"Plex TV Show by Date": {}}
            
            # Ensure the main section exists
            if "Plex TV Show by Date" not in subs_data:
                subs_data["Plex TV Show by Date"] = {}
            
            # Merge in new classes
            for header, episodes in classes.items():
                if header not in subs_data["Plex TV Show by Date"]:
                    subs_data["Plex TV Show by Date"][header] = {}
                
                # Add each episode
                for ep_title, ep_data in episodes.items():
                    subs_data["Plex TV Show by Date"][header][ep_title] = ep_data
                    self.logger.debug(f"Added episode: {header} -> {ep_title}")
            
            # Write back to file
            with open(subs_file_path, 'w') as f:
                yaml.dump(subs_data, f, sort_keys=False, allow_unicode=True, 
                         default_flow_style=False, indent=2, width=4096)
            
            self.logger.info(f"Successfully updated {self.subs_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding new classes to subscriptions: {e}")
            return False
    
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
        from .directory_validator import DirectoryValidator
        validator = DirectoryValidator(self.media_dir, dry_run=dry_run)
        return validator.validate_and_repair()
