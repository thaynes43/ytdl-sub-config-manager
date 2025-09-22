"""Data models and enums for the ytdl-sub config manager."""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Set


class Activity(Enum):
    """Peloton activity types."""
    ALL = "all"
    STRENGTH = "strength"
    YOGA = "yoga"
    MEDITATION = "meditation"
    CARDIO = "cardio"
    STRETCHING = "stretching"
    CYCLING = "cycling"
    RUNNING = "running"
    WALKING = "walking"
    BOOTCAMP = "bootcamp"
    BIKE_BOOTCAMP = "bike_bootcamp"
    ROWING = "rowing"
    ROW_BOOTCAMP = "row_bootcamp"


@dataclass
class ActivityData:
    """Tracks maximum episode numbers per season for an activity."""
    
    activity: Activity
    max_episode: Dict[int, int]
    
    def __init__(self, activity: Activity):
        self.activity = activity
        self.max_episode = {}
    
    def update(self, season: int, episode: int) -> None:
        """Update the maximum episode for a given season."""
        if season not in self.max_episode or episode > self.max_episode[season]:
            self.max_episode[season] = episode
    
    def get_next_episode(self, season: int) -> int:
        """Get the next episode number for a season."""
        return self.max_episode.get(season, 0) + 1
    
    @staticmethod
    def merge_collections(map1: Dict[Activity, 'ActivityData'], 
                         map2: Dict[Activity, 'ActivityData']) -> Dict[Activity, 'ActivityData']:
        """Merge two dicts of ActivityData, keeping the largest episode per season."""
        merged = {}
        all_activities = set(map1.keys()) | set(map2.keys())
        
        for activity in all_activities:
            merged_data = ActivityData(activity)
            seasons = set()
            
            if activity in map1:
                seasons.update(map1[activity].max_episode.keys())
            if activity in map2:
                seasons.update(map2[activity].max_episode.keys())
            
            for season in seasons:
                ep1 = map1[activity].max_episode.get(season, 0) if activity in map1 else 0
                ep2 = map2[activity].max_episode.get(season, 0) if activity in map2 else 0
                merged_data.max_episode[season] = max(ep1, ep2)
            
            merged[activity] = merged_data
        
        return merged
    
    @staticmethod
    def parse_activities_from_env(env_var: str) -> List[Activity]:
        """Parse a comma-separated string of activities from environment."""
        if not env_var or not env_var.strip():
            # Default: all except ALL
            return [a for a in Activity if a != Activity.ALL]
        
        selected = []
        for val in env_var.split(","):
            val = val.strip()
            if not val:
                continue
            
            matched = None
            # Match by value (case-insensitive)
            for a in Activity:
                if a.value.lower() == val.lower():
                    matched = a
                    break
            
            # Match by name (case-insensitive)
            if not matched:
                try:
                    matched = Activity[val.strip().upper()]
                except KeyError:
                    pass
            
            if matched:
                selected.append(matched)
            else:
                raise ValueError(f"Invalid activity in PELOTON_ACTIVITY: '{val}'")
        
        return selected


@dataclass
class ClassMetadata:
    """Metadata for a Peloton class."""
    class_id: str
    title: str
    instructor: str
    activity: str
    duration_minutes: int
    player_url: str
    season_number: int
    episode_number: int
