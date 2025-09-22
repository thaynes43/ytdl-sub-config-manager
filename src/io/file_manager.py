"""File manager that combines filesystem and subscriptions parsing using dependency injection."""

from typing import Dict, Set, List
from pathlib import Path

from .generic_directory_validator import GenericDirectoryValidator
from .generic_episode_manager import GenericEpisodeManager
from ..core.models import Activity, ActivityData
from ..core.logging import get_logger

logger = get_logger(__name__)


class FileManager:
    """Manages episode parsing from multiple sources and provides unified interface."""
    
    def __init__(self, media_dir: str, subs_file: str, validate_and_repair: bool = True, 
                 validation_strategies: List[str] = None, repair_strategies: List[str] = None, 
                 episode_parsers: List[str] = None):
        """Initialize the file manager.
        
        Args:
            media_dir: Root directory containing downloaded media files
            subs_file: Path to the subscriptions YAML file
            validate_and_repair: If True, validate and repair directory structure on init
            validation_strategies: List of validation strategy module paths (required if validate_and_repair=True)
            repair_strategies: List of repair strategy module paths (required if validate_and_repair=True)
            episode_parsers: List of episode parser module paths (required)
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
        
        self.logger = get_logger(__name__)
        
        # Validate and repair directory structure if requested
        if validate_and_repair and self.directory_validator:
            self.logger.info("Validating and repairing directory structure")
            if not self.directory_validator.validate_and_repair():
                self.logger.error("Directory validation and repair failed!")
                raise RuntimeError("Directory structure validation failed")
    
    def get_merged_episode_data(self) -> Dict[Activity, ActivityData]:
        """Get merged episode data from all configured parsers.
        
        Returns:
            Dictionary mapping Activity to ActivityData with merged episode information
        """
        return self.episode_manager.get_merged_episode_data()
    
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
    
    def cleanup_subscriptions(self) -> bool:
        """Remove already-downloaded classes from subscriptions.
        
        Returns:
            True if changes were made, False if no cleanup was needed
        """
        return self.episode_manager.cleanup_subscriptions()
    
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
        # Use the same strategies as the main validator
        validator = GenericDirectoryValidator(
            media_dir=self.media_dir,
            validation_strategies=self.validation_strategies,
            repair_strategies=self.repair_strategies,
            dry_run=dry_run
        )
        return validator.validate_and_repair()
