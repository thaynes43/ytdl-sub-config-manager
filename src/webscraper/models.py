"""Data models for web scraping framework."""

import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


def normalize_text(text: str) -> str:
    """Normalize text to handle encoding issues and special characters.
    
    Args:
        text: Raw text that may contain encoding issues
        
    Returns:
        Normalized text safe for YAML output
    """
    if not text:
        return text
    
    # First normalize unicode to composed form (NFC)
    text = unicodedata.normalize('NFC', text)
    
    # Replace any remaining problematic characters
    # Handle common encoding issues
    replacements = {
        '\ufffd': '',  # Unicode replacement character
        '\u00e1': 'á',  # Ensure proper á character
        '\u00e9': 'é',  # Ensure proper é character
        '\u00ed': 'í',  # Ensure proper í character
        '\u00f1': 'ñ',  # Ensure proper ñ character
        '\u00f3': 'ó',  # Ensure proper ó character
        '\u00fa': 'ú',  # Ensure proper ú character
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Strip whitespace and return
    return text.strip()


def sanitize_for_filesystem(text: str) -> str:
    """Sanitize text for safe use in filesystem paths.
    
    Args:
        text: Raw text that may contain filesystem-unsafe characters
        
    Returns:
        Text safe for use in file and directory names
    """
    if not text:
        return text
    
    # First normalize the text for encoding issues
    text = normalize_text(text)
    
    # Replace filesystem-unsafe characters
    # These characters can cause issues on various filesystems
    replacements = {
        '/': '-',      # Forward slash (directory separator)
        '\\': '-',     # Backslash (Windows directory separator)
        ':': '-',      # Colon (Windows drive separator, general issues)
        ';': '-',      # Semicolon (command separator)
        '*': '-',      # Asterisk (wildcard)
        '?': '-',      # Question mark (wildcard)
        '"': "'",      # Double quote (shell quoting issues)
        '<': '-',      # Less than (redirection)
        '>': '-',      # Greater than (redirection)
        '|': '-',      # Pipe (command separator)
        '\0': '',      # Null character
        '\t': ' ',     # Tab to space
        '\n': ' ',     # Newline to space
        '\r': ' ',     # Carriage return to space
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Remove any remaining control characters (0-31, 127)
    text = ''.join(char for char in text if ord(char) > 31 and ord(char) != 127)
    
    # Collapse multiple spaces and strip
    import re
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Remove leading/trailing dots and spaces (Windows issues)
    text = text.strip('. ')
    
    return text


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
    
    def to_subscription_entry(self, media_dir: str = "/media/peloton") -> Dict[str, Any]:
        """Convert to ytdl-sub subscription format."""
        # Normalize all text fields to ensure proper encoding
        normalized_title = normalize_text(self.title)
        normalized_instructor = normalize_text(self.instructor)
        normalized_activity = normalize_text(self.activity)
        
        # Sanitize for filesystem safety (episode titles and directory paths)
        safe_title = sanitize_for_filesystem(normalized_title)
        safe_instructor = sanitize_for_filesystem(normalized_instructor)
        safe_activity = sanitize_for_filesystem(normalized_activity)
        
        episode_title = f"{safe_title} with {safe_instructor}"
        
        # Use configured media directory, ensuring proper path format
        media_path = media_dir.rstrip('/\\')  # Remove trailing separators
        tv_show_directory = f"{media_path}/{safe_activity.title()}/{safe_instructor}"
        
        return {
            "download": self.player_url,
            "overrides": {
                "tv_show_directory": tv_show_directory,
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
    
    def get_subscription_data(self, media_dir: str = "/media/peloton") -> Dict[str, Dict[str, Any]]:
        """Convert scraped classes to subscription YAML format."""
        result_dict = {}
        dupe_dict = {}
        
        for scraped_class in self.classes:
            if scraped_class.status != ScrapingStatus.COMPLETED:
                continue
                
            # Create duration key (e.g., "= Cycling (30 min)")
            normalized_activity = normalize_text(scraped_class.activity)
            safe_activity = sanitize_for_filesystem(normalized_activity)
            duration_key = f"= {safe_activity.title()} ({scraped_class.duration_minutes} min)"
            
            # Create episode title with filesystem-safe text
            normalized_title = normalize_text(scraped_class.title)
            normalized_instructor = normalize_text(scraped_class.instructor)
            safe_title = sanitize_for_filesystem(normalized_title)
            safe_instructor = sanitize_for_filesystem(normalized_instructor)
            episode_title = f"{safe_title} with {safe_instructor}"
            
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
            result_dict[duration_key][episode_title] = scraped_class.to_subscription_entry(media_dir)
        
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
