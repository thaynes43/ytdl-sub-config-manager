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
    
    def _scroll_dynamically_until_limit(self, driver: webdriver.Chrome, config, pause_time: float = 3.0) -> int:
        """
        Dynamically scroll until class limit is reached or max scrolls exceeded.
        
        Args:
            driver: Active browser session
            config: ScrapingConfig with dynamic scrolling settings
            pause_time: Time to pause between scrolls
            
        Returns:
            Number of scrolls performed
        """
        from selenium.webdriver.common.by import By
        
        scrolls_performed = 0
        classes_needed = config.max_classes - config.subscriptions_existing_classes
        
        self.logger.info(f"Dynamic scrolling: need {classes_needed} classes (limit: {config.max_classes}, existing: {config.subscriptions_existing_classes})")
        
        while scrolls_performed < config.max_scrolls:
            # Scroll to load more content first
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            scrolls_performed += 1
            self.logger.debug(f"Completed dynamic scroll {scrolls_performed}/{config.max_scrolls}")
            time.sleep(pause_time)
            
            # Check current class count on page after scrolling
            current_links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="classId="]')
            new_classes_found = 0
            
            # Count new classes (not in existing_class_ids)
            for link in current_links:
                try:
                    href = link.get_attribute("href")
                    if href:
                        class_id = self._extract_class_id(href)
                        if class_id and class_id not in config.existing_class_ids:
                            new_classes_found += 1
                except Exception:
                    continue
            
            self.logger.debug(f"After scroll {scrolls_performed}: found {new_classes_found} new classes on page")
            
            # Check if we have enough new classes
            if new_classes_found >= classes_needed:
                self.logger.info(f"Found enough classes ({new_classes_found} >= {classes_needed}) after {scrolls_performed} scrolls")
                break
        
        if scrolls_performed >= config.max_scrolls:
            self.logger.warning(f"Reached maximum scroll limit ({config.max_scrolls}) before finding enough classes")
        
        return scrolls_performed
    
    def _extract_class_id(self, url: str) -> str:
        """Extract class ID from Peloton URL - to be implemented by subclasses."""
        # This is a placeholder - actual implementation should be in PelotonScraperStrategy
        return ""
    
    def _wait_for_page_load(self, driver: webdriver.Chrome, wait_time: float = 10.0) -> None:
        """Helper method to wait for page to load."""
        import time
        self.logger.debug(f"Waiting {wait_time}s for page to load")
        time.sleep(wait_time)
