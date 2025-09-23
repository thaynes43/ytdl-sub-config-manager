"""Data models for web scraping framework."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class ScrapingStatus(Enum):
    """Status of a scraping operation."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScrapedClass:
    """Represents a single scraped class/episode."""
    class_id: str
    title: str
    instructor: str
    activity: str
    duration_minutes: int
    player_url: str
    season_number: int
    episode_number: int
    status: ScrapingStatus = ScrapingStatus.PENDING
    
    def to_subscription_entry(self) -> Dict[str, Any]:
        """Convert to ytdl-sub subscription format."""
        episode_title = f"{self.title} with {self.instructor}".replace("/", "-")
        
        return {
            "download": self.player_url,
            "overrides": {
                "tv_show_directory": f"/media/peloton/{self.activity.title()}/{self.instructor}",
                "season_number": self.season_number,
                "episode_number": self.episode_number
            }
        }


@dataclass
class ScrapingResult:
    """Results from a scraping operation."""
    activity: str
    classes: List[ScrapedClass]
    total_found: int
    total_skipped: int
    total_errors: int
    status: ScrapingStatus
    error_message: Optional[str] = None
    
    def get_subscription_data(self) -> Dict[str, Dict[str, Any]]:
        """Convert scraped classes to subscription YAML format."""
        result_dict = {}
        dupe_dict = {}
        
        for scraped_class in self.classes:
            if scraped_class.status != ScrapingStatus.COMPLETED:
                continue
                
            # Create duration key (e.g., "= Cycling (30 min)")
            duration_key = f"= {scraped_class.activity.title()} ({scraped_class.duration_minutes} min)"
            
            # Create episode title
            episode_title = f"{scraped_class.title} with {scraped_class.instructor}".replace("/", "-")
            
            # Handle duplicates
            if duration_key not in result_dict:
                result_dict[duration_key] = {}
                
            if episode_title in result_dict[duration_key]:
                if episode_title not in dupe_dict:
                    dupe_dict[episode_title] = 1
                updated_title = f"{episode_title} ({dupe_dict[episode_title]})"
                dupe_dict[episode_title] += 1
                episode_title = updated_title
            
            # Add to result
            result_dict[duration_key][episode_title] = scraped_class.to_subscription_entry()
        
        return result_dict


@dataclass
class ScrapingConfig:
    """Configuration for a scraping operation."""
    activity: str
    max_classes: int
    page_scrolls: int
    existing_class_ids: set
    episode_numbering_data: Dict[int, int]  # season -> max_episode
    headless: bool = True
    container_mode: bool = True
    scroll_pause_time: float = 3.0
    login_wait_time: float = 15.0
    page_load_wait_time: float = 10.0
