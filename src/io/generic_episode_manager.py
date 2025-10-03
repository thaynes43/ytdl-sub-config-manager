"""Generic episode manager that uses injected parsers."""

from typing import Dict, List, Set
from .strategy_loader import strategy_loader
from .episode_parser import EpisodeMerger
from ..core.models import Activity, ActivityData
from ..core.logging import get_logger


class GenericEpisodeManager:
    """Generic episode manager that uses injected episode parsers."""
    
    def __init__(self, episode_parser_strategies: List[str], media_dir: str, subs_file: str):
        """Initialize the generic episode manager.
        
        Args:
            episode_parser_strategies: List of episode parser module paths
            media_dir: Root directory containing downloaded media files
            subs_file: Path to subscriptions YAML file
        """
        self.media_dir = media_dir
        self.subs_file = subs_file
        self.logger = get_logger(__name__)
        
        # Load episode parsers
        self.episode_parsers = []
        for strategy_path in episode_parser_strategies:
            try:
                # Pass required parameters to the parser constructors
                if 'episodes_from_disk' in strategy_path.lower():
                    parser = strategy_loader.instantiate_strategy(strategy_path, {'media_dir': media_dir})
                elif 'episodes_from_subscriptions' in strategy_path.lower():
                    parser = strategy_loader.instantiate_strategy(strategy_path, {'subs_file': subs_file})
                else:
                    # Try without parameters first, then with common parameters
                    try:
                        parser = strategy_loader.instantiate_strategy(strategy_path)
                    except TypeError:
                        # If no-arg constructor fails, try with common parameters
                        parser = strategy_loader.instantiate_strategy(strategy_path, {
                            'media_dir': media_dir, 
                            'subs_file': subs_file
                        })
                
                self.episode_parsers.append(parser)
                self.logger.info(f"Loaded episode parser: {strategy_path}")
            except Exception as e:
                self.logger.error(f"Failed to load episode parser {strategy_path}: {e}")
        
        # Initialize episode merger
        self.episode_merger = EpisodeMerger()
    
    def get_merged_episode_data(self) -> Dict[Activity, ActivityData]:
        """Get merged episode data from all configured parsers.
        
        Returns:
            Dictionary mapping Activity to ActivityData with merged episode information
        """
        self.logger.info("Gathering episode data from all sources")
        
        # Collect data from all parsers
        all_data = []
        parser_names = []
        
        for parser in self.episode_parsers:
            try:
                if hasattr(parser, 'parse_episodes'):
                    data = parser.parse_episodes()
                    all_data.append(data)
                    parser_names.append(parser.__class__.__name__)
                    self.logger.info(f"{parser.__class__.__name__}: {len(data)} activities")
                else:
                    self.logger.warning(f"Parser {parser.__class__.__name__} does not have parse_episodes method")
            except Exception as e:
                self.logger.error(f"Parser {parser.__class__.__name__} failed: {e}")
                continue
        
        # Merge all data
        merged_data = self.episode_merger.merge_sources(*all_data)
        self.logger.info(f"Merged: {len(merged_data)} activities")
        
        return merged_data
    
    def get_disk_episode_data(self) -> Dict[Activity, ActivityData]:
        """Get episode data from disk only (not subscriptions).
        
        Returns:
            Dictionary mapping Activity to ActivityData with disk-only episode information
        """
        self.logger.info("Gathering episode data from disk only")
        
        disk_data = {}
        
        for parser in self.episode_parsers:
            try:
                # Only get data from disk parser
                if 'disk' in parser.__class__.__name__.lower() and hasattr(parser, 'parse_episodes'):
                    data = parser.parse_episodes()
                    disk_data.update(data)
                    self.logger.info(f"{parser.__class__.__name__}: {len(data)} activities")
                else:
                    self.logger.debug(f"Skipping parser {parser.__class__.__name__} (not disk parser)")
            except Exception as e:
                self.logger.error(f"Error getting disk episode data from {parser.__class__.__name__}: {e}")
        
        self.logger.info(f"Disk only: {len(disk_data)} activities")
        
        return disk_data
    
    def get_subscriptions_episode_data(self) -> Dict[Activity, ActivityData]:
        """Get episode data from subscriptions only (not disk).
        
        Returns:
            Dictionary mapping Activity to ActivityData with subscriptions-only episode information
        """
        self.logger.info("Gathering episode data from subscriptions only")
        
        subscriptions_data = {}
        
        for parser in self.episode_parsers:
            try:
                # Only get data from subscriptions parser
                if 'subscription' in parser.__class__.__name__.lower() and hasattr(parser, 'parse_episodes'):
                    data = parser.parse_episodes()
                    subscriptions_data.update(data)
                    self.logger.info(f"{parser.__class__.__name__}: {len(data)} activities from subscriptions")
            except Exception as e:
                self.logger.error(f"Subscriptions parser {parser.__class__.__name__} failed: {e}")
                continue
        
        self.logger.info(f"Subscriptions only: {len(subscriptions_data)} activities")
        return subscriptions_data
    
    def find_all_existing_class_ids(self) -> Set[str]:
        """Find all existing class IDs from all configured parsers.
        
        Returns:
            Set of all existing class IDs
        """
        self.logger.info("Finding all existing class IDs")
        all_class_ids = set()
        
        for parser in self.episode_parsers:
            try:
                if hasattr(parser, 'find_existing_class_ids'):
                    class_ids = parser.find_existing_class_ids()
                    all_class_ids.update(class_ids)
                    self.logger.debug(f"{parser.__class__.__name__}: {len(class_ids)} class IDs")
                elif hasattr(parser, 'find_subscription_class_ids'):
                    class_ids = parser.find_subscription_class_ids()
                    all_class_ids.update(class_ids)
                    self.logger.debug(f"{parser.__class__.__name__}: {len(class_ids)} class IDs")
                else:
                    self.logger.debug(f"Parser {parser.__class__.__name__} does not support class ID finding")
            except Exception as e:
                self.logger.error(f"Parser {parser.__class__.__name__} failed to find class IDs: {e}")
                continue
        
        # Count by parser type for logging
        filesystem_ids = set()
        subscription_ids = set()
        
        for parser in self.episode_parsers:
            try:
                if 'disk' in parser.__class__.__name__.lower():
                    if hasattr(parser, 'find_existing_class_ids'):
                        filesystem_ids.update(parser.find_existing_class_ids())
                elif 'subscription' in parser.__class__.__name__.lower():
                    if hasattr(parser, 'find_subscription_class_ids'):
                        subscription_ids.update(parser.find_subscription_class_ids())
            except Exception:
                continue
        
        self.logger.info(f"Total existing class IDs: {len(all_class_ids)} "
                        f"(filesystem: {len(filesystem_ids)}, subscriptions: {len(subscription_ids)})")
        
        return all_class_ids
    
    def cleanup_subscriptions(self) -> bool:
        """Clean up subscriptions by removing already-downloaded classes.
        
        Returns:
            True if changes were made, False if no cleanup was needed
        """
        self.logger.info("Cleaning up subscriptions file")
        
        # Find filesystem class IDs
        filesystem_ids = set()
        for parser in self.episode_parsers:
            if 'disk' in parser.__class__.__name__.lower():
                try:
                    if hasattr(parser, 'find_existing_class_ids'):
                        filesystem_ids.update(parser.find_existing_class_ids())
                except Exception as e:
                    self.logger.error(f"Failed to get filesystem class IDs: {e}")
        
        # Remove from subscriptions
        changes_made = False
        for parser in self.episode_parsers:
            if 'subscription' in parser.__class__.__name__.lower():
                try:
                    if hasattr(parser, 'remove_existing_classes'):
                        if parser.remove_existing_classes(filesystem_ids):
                            changes_made = True
                except Exception as e:
                    self.logger.error(f"Failed to clean up subscriptions: {e}")
        
        return changes_made
