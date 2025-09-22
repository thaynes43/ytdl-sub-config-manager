"""Media source strategy interfaces and base classes.

This module defines the strategy pattern for different media sources,
allowing each source to define its own directory structure, repair logic,
and ordering strategies.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

from ..core.models import Activity


@dataclass
class DirectoryPattern:
    """Defines the expected directory structure pattern for a media source."""
    # Pattern relative to media root, using placeholders
    # e.g., "{source}/{activity}/{instructor}/S{season}E{episode}"
    pattern: str
    
    # Number of directory levels expected
    expected_levels: int
    
    # Whether this pattern requires a source subdirectory
    has_source_subdir: bool


@dataclass
class RepairAction:
    """Represents a repair action to be taken on a directory."""
    action_type: str  # "move", "rename", "delete"
    source_path: Path
    target_path: Optional[Path] = None
    reason: str = ""


class DirectoryRepairStrategy(ABC):
    """Abstract base class for directory repair strategies."""
    
    @abstractmethod
    def can_repair(self, path: Path, expected_pattern: DirectoryPattern) -> bool:
        """Check if this strategy can repair the given path.
        
        Args:
            path: Path that doesn't match expected pattern
            expected_pattern: The expected directory pattern
            
        Returns:
            True if this strategy can handle the repair
        """
        pass
    
    @abstractmethod
    def generate_repair_actions(self, path: Path, expected_pattern: DirectoryPattern) -> List[RepairAction]:
        """Generate repair actions for the given path.
        
        Args:
            path: Path that needs repair
            expected_pattern: The expected directory pattern
            
        Returns:
            List of repair actions to execute
        """
        pass


class EpisodeOrderingStrategy(ABC):
    """Abstract base class for episode ordering strategies."""
    
    @abstractmethod
    def get_next_episode_number(self, activity: Activity, season: int, existing_episodes: Dict[int, int]) -> int:
        """Get the next episode number for a given activity and season.
        
        Args:
            activity: The activity type
            season: The season number
            existing_episodes: Dict mapping episode numbers to some identifier
            
        Returns:
            The next available episode number
        """
        pass


class SeasonOrderingStrategy(ABC):
    """Abstract base class for season ordering strategies."""
    
    @abstractmethod
    def determine_season(self, metadata: Dict[str, Any]) -> int:
        """Determine the season number based on content metadata.
        
        Args:
            metadata: Content metadata (duration, title, etc.)
            
        Returns:
            Season number
        """
        pass


class MediaSourceStrategy(ABC):
    """Abstract base class for media source strategies."""
    
    @abstractmethod
    def get_directory_pattern(self) -> DirectoryPattern:
        """Get the expected directory structure pattern."""
        pass
    
    @abstractmethod
    def get_repair_strategies(self) -> List[DirectoryRepairStrategy]:
        """Get the list of repair strategies for this source."""
        pass
    
    @abstractmethod
    def get_episode_ordering_strategy(self) -> EpisodeOrderingStrategy:
        """Get the episode ordering strategy."""
        pass
    
    @abstractmethod
    def get_season_ordering_strategy(self) -> SeasonOrderingStrategy:
        """Get the season ordering strategy."""
        pass
    
    @abstractmethod
    def parse_episode_info(self, path: Path) -> Optional[Tuple[Activity, str, int, int, str]]:
        """Parse episode information from a path.
        
        Args:
            path: Path to parse
            
        Returns:
            Tuple of (activity, instructor, season, episode, title) or None
        """
        pass


# Default implementations

class IncrementalEpisodeOrdering(EpisodeOrderingStrategy):
    """Simple incremental episode ordering (1, 2, 3, ...)."""
    
    def get_next_episode_number(self, activity: Activity, season: int, existing_episodes: Dict[int, int]) -> int:
        """Get next incremental episode number."""
        if not existing_episodes:
            return 1
        return max(existing_episodes.keys()) + 1


class DurationBasedSeasonOrdering(SeasonOrderingStrategy):
    """Season ordering based on content duration (common for workout content)."""
    
    def determine_season(self, metadata: Dict[str, Any]) -> int:
        """Determine season based on duration in minutes."""
        duration_minutes = metadata.get('duration_minutes', 0)
        
        # Round to nearest 5 minutes for season grouping
        return max(5, round(duration_minutes / 5) * 5)
