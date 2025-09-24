"""Peloton-specific scraping strategy."""

import re
import time
import unicodedata
from typing import List
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from ..scraper_strategy import ScraperStrategy
from ..models import ScrapedClass, ScrapingConfig, ScrapingResult, ScrapingStatus, normalize_text, sanitize_for_filesystem


class PelotonScraperStrategy(ScraperStrategy):
    """Peloton-specific web scraping strategy."""
    
    
    def get_activity_url(self, activity: str) -> str:
        """Get the URL for a Peloton activity's class listing."""
        base_url = "https://members.onepeloton.com/classes/{}"
        params = "?class_languages=%5B%22en-US%22%5D&sort=original_air_time&desc=true"
        return base_url.format(activity.lower()) + params
    
    def scrape_activity(self, driver: webdriver.Chrome, config: ScrapingConfig) -> ScrapingResult:
        """
        Scrape Peloton classes for a specific activity.
        
        Args:
            driver: Active browser session
            config: Scraping configuration
            
        Returns:
            ScrapingResult with scraped classes and metadata
        """
        activity_url = self.get_activity_url(config.activity)
        self.logger.info(f"Navigating to {config.activity} classes: {activity_url}")
        
        try:
            # Navigate to activity page
            driver.get(activity_url)
            self._wait_for_page_load(driver, config.page_load_wait_time)
            
            # Scroll to load more content
            self._scroll_to_load_content(driver, config.page_scrolls, config.scroll_pause_time)
            
            # Find all class links
            links = driver.find_elements(By.CSS_SELECTOR, 'a[href*="classId="]')
            self.logger.info(f"Found {len(links)} class links on page")
            
            scraped_classes = []
            skipped_count = 0
            error_count = 0
            
            for i, link in enumerate(links):
                if len(scraped_classes) >= config.max_classes:
                    self.logger.info(f"Reached max classes limit ({config.max_classes})")
                    break
                
                try:
                    # Extract class ID from URL
                    href = link.get_attribute("href")
                    class_id = self._extract_class_id(href)
                    
                    if not class_id:
                        self.logger.warning(f"Could not extract class ID from URL: {href}")
                        error_count += 1
                        continue
                    
                    # Skip if already exists
                    if class_id in config.existing_class_ids:
                        skipped_count += 1
                        continue
                    
                    # Extract metadata
                    metadata = self.extract_class_metadata(link)
                    if not metadata:
                        error_count += 1
                        continue
                    
                    # Create scraped class
                    duration = self.extract_duration_from_title(metadata['title'])
                    
                    # Update episode numbering
                    if duration not in config.episode_numbering_data:
                        config.episode_numbering_data[duration] = 0
                    config.episode_numbering_data[duration] += 1
                    
                    scraped_class = ScrapedClass(
                        class_id=class_id,
                        title=metadata['title'],
                        instructor=metadata['instructor'],
                        activity=metadata['activity'],
                        duration_minutes=duration,
                        player_url=f"https://members.onepeloton.com/classes/player/{class_id}",
                        season_number=duration,
                        episode_number=config.episode_numbering_data[duration],
                        status=ScrapingStatus.COMPLETED
                    )
                    
                    scraped_classes.append(scraped_class)
                    
                    if (i + 1) % 10 == 0:
                        self.logger.debug(f"Processed {i + 1}/{len(links)} links")
                    
                except Exception as e:
                    self.logger.warning(f"Error processing class link {i}: {e}")
                    error_count += 1
                    continue
            
            self.logger.info(f"Scraping completed: {len(scraped_classes)} classes, "
                           f"{skipped_count} skipped, {error_count} errors")
            
            return ScrapingResult(
                activity=config.activity,
                classes=scraped_classes,
                total_found=len(links),
                total_skipped=skipped_count,
                total_errors=error_count,
                status=ScrapingStatus.COMPLETED
            )
            
        except Exception as e:
            self.logger.error(f"Fatal error scraping {config.activity}: {e}")
            return ScrapingResult(
                activity=config.activity,
                classes=[],
                total_found=0,
                total_skipped=0,
                total_errors=1,
                status=ScrapingStatus.FAILED,
                error_message=str(e)
            )
    
    def extract_class_metadata(self, link_element) -> dict:
        """Extract metadata from a Peloton class link element."""
        try:
            # Extract title
            title_element = link_element.find_element(By.CSS_SELECTOR, '[data-test-id="videoCellTitle"]')
            title = normalize_text(title_element.text)
            
            # Extract instructor and activity
            subtitle_element = link_element.find_element(By.CSS_SELECTOR, '[data-test-id="videoCellSubtitle"]')
            subtitle_text = normalize_text(subtitle_element.text)
            
            # Parse "Instructor · Activity" format
            parts = subtitle_text.split('·')
            if len(parts) >= 2:
                instructor = normalize_text(parts[0].strip().title())
                activity = normalize_text(parts[1].strip().title())
            else:
                self.logger.warning(f"Unexpected subtitle format: {subtitle_text}")
                instructor = "Unknown"
                activity = "Unknown"
            
            return {
                'title': title,
                'instructor': instructor,
                'activity': activity
            }
            
        except NoSuchElementException as e:
            self.logger.warning(f"Could not extract metadata from class element: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error extracting metadata: {e}")
            return None
    
    def extract_duration_from_title(self, title: str) -> int:
        """Extract duration in minutes from a Peloton class title."""
        # Look for pattern like "45 min" at the beginning
        match = re.match(r"^\s*(\d+)\s*min", title, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        # Fallback: look for any number in the title
        fallback = re.search(r"\b(\d+)\b", title)
        if fallback:
            return int(fallback.group(1))
        
        # Default fallback
        self.logger.warning(f"Could not extract duration from title: {title}")
        return 0
    
    def _extract_class_id(self, url: str) -> str:
        """Extract class ID from Peloton URL."""
        try:
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            class_id = query_params.get("classId", [""])[0]
            return class_id
        except Exception as e:
            self.logger.warning(f"Error extracting class ID from URL {url}: {e}")
            return ""
