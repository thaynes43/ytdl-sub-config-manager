"""Base classes and interfaces for episode number parsing."""

from abc import ABC, abstractmethod
from typing import Dict, Set
from ..core.models import Activity, ActivityData
from ..core.logging import get_logger

logger = get_logger(__name__)


class EpisodeParser(ABC):
    """Abstract base class for parsing episode numbers from different sources."""
    
    def __init__(self, source_name: str):
        """Initialize the parser with a source name for logging."""
        self.source_name = source_name
        self.logger = get_logger(f"{__name__}.{source_name}")
    
    @abstractmethod
    def parse_episodes(self) -> Dict[Activity, ActivityData]:
        """Parse episode numbers and return ActivityData mapping.
        
        Returns:
            Dictionary mapping Activity enum to ActivityData objects
            containing max episode numbers per season.
        """
        pass
    
    def _create_activity_data(self, activity: Activity) -> ActivityData:
        """Create a new ActivityData instance for the given activity."""
        return ActivityData(activity)
    
    def _update_activity_data(self, activity_data: ActivityData, season: int, episode: int) -> None:
        """Update ActivityData with a new season/episode combination."""
        activity_data.update(season, episode)


class EpisodeMerger:
    """Merges episode data from multiple sources."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def merge_sources(self, *sources: Dict[Activity, ActivityData]) -> Dict[Activity, ActivityData]:
        """Merge episode data from multiple sources.
        
        Args:
            *sources: Variable number of ActivityData dictionaries from different sources
            
        Returns:
            Merged dictionary with maximum episode numbers per season per activity
        """
        if not sources:
            self.logger.warning("No sources provided for merging")
            return {}
        
        if len(sources) == 1:
            self.logger.info("Only one source provided, returning as-is")
            return sources[0]
        
        # Start with the first source
        merged = dict(sources[0])
        
        # Merge each additional source
        for i, source in enumerate(sources[1:], 1):
            self.logger.debug(f"Merging source {i+1} of {len(sources)}")
            merged = ActivityData.merge_collections(merged, source)
        
        # Log the final results
        for activity, activity_data in merged.items():
            total_episodes = sum(activity_data.max_episode.values())
            seasons = list(activity_data.max_episode.keys())
            self.logger.info(f"{activity.name}: {total_episodes} episodes across seasons {seasons}")
        
        return merged
    
    def get_next_episode_number(self, merged_data: Dict[Activity, ActivityData], 
                              activity: Activity, season: int) -> int:
        """Get the next available episode number for a given activity and season.
        
        Args:
            merged_data: Merged episode data from all sources
            activity: The activity type
            season: The season (duration in minutes)
            
        Returns:
            The next available episode number (starts at 1)
        """
        if activity not in merged_data:
            self.logger.debug(f"No existing data for {activity.name}, starting at episode 1")
            return 1
        
        activity_data = merged_data[activity]
        current_max = activity_data.max_episode.get(season, 0)
        next_episode = current_max + 1
        
        self.logger.debug(f"{activity.name} S{season}: next episode is {next_episode}")
        return next_episode
