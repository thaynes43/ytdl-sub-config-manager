"""Abstract scraper strategy interface."""

import time
from abc import ABC, abstractmethod
from typing import List
from selenium import webdriver

from .models import ScrapedClass, ScrapingConfig, ScrapingResult


class ScraperStrategy(ABC):
    """Abstract base class for website-specific scraping strategies."""
    
    def __init__(self):
        from ..core.logging import get_logger
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def scrape_activity(self, driver: webdriver.Chrome, config: ScrapingConfig) -> ScrapingResult:
        """
        Scrape classes for a specific activity.
        
        Args:
            driver: Active browser session
            config: Scraping configuration
            
        Returns:
            ScrapingResult with scraped classes and metadata
        """
        pass
    
    @abstractmethod
    def get_activity_url(self, activity: str) -> str:
        """Get the URL for a specific activity's class listing."""
        pass
    
    @abstractmethod
    def extract_class_metadata(self, element) -> dict:
        """Extract metadata from a class element on the page."""
        pass
    
    @abstractmethod
    def extract_duration_from_title(self, title: str) -> int:
        """Extract duration in minutes from a class title."""
        pass
    
    def _scroll_to_load_content(self, driver: webdriver.Chrome, scrolls: int, pause_time: float = 3.0) -> None:
        """Helper method to scroll page to load more content."""
        self.logger.info(f"Scrolling page {scrolls} times to load more content")
        
        for i in range(scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            self.logger.debug(f"Completed scroll {i + 1}/{scrolls}")
            time.sleep(pause_time)
    
    def _wait_for_page_load(self, driver: webdriver.Chrome, wait_time: float = 10.0) -> None:
        """Helper method to wait for page to load."""
        import time
        self.logger.debug(f"Waiting {wait_time}s for page to load")
        time.sleep(wait_time)
