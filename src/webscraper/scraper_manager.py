"""Generic web scraper manager with dependency injection."""

from typing import Dict, List, Optional, Set
from ..core.logging import get_logger
from .models import ScrapingConfig, ScrapingResult, ScrapingStatus
from .session_manager import SessionManager
from .scraper_strategy import ScraperStrategy


class ScraperManager:
    """Generic web scraper manager that coordinates session and scraping strategies."""
    
    def __init__(self, session_manager: SessionManager, scraper_strategy: ScraperStrategy):
        """
        Initialize the scraper manager.
        
        Args:
            session_manager: Session management strategy
            scraper_strategy: Website-specific scraping strategy
        """
        self.session_manager = session_manager
        self.scraper_strategy = scraper_strategy
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def scrape_activities(self, username: str, password: str, activities: List[str], 
                         configs: Dict[str, ScrapingConfig]) -> Dict[str, ScrapingResult]:
        """
        Scrape multiple activities in a single session.
        
        Args:
            username: Login username
            password: Login password
            activities: List of activity names to scrape
            configs: Configuration for each activity
            
        Returns:
            Dictionary mapping activity names to scraping results
        """
        results = {}
        
        try:
            # Update session manager settings based on first config (assuming all configs have same settings)
            if configs:
                first_config = next(iter(configs.values()))
                self.session_manager.headless = first_config.headless
                self.session_manager.container_mode = first_config.container_mode
            
            # Create session and login
            self.logger.info("Creating browser session")
            driver = self.session_manager.create_session()
            
            self.logger.info("Logging in")
            if not self.session_manager.login(username, password):
                raise RuntimeError("Login failed")
            
            # Scrape each activity
            for activity in activities:
                self.logger.info(f"Starting scrape for activity: {activity}")
                
                if activity not in configs:
                    self.logger.error(f"No configuration found for activity: {activity}")
                    results[activity] = ScrapingResult(
                        activity=activity,
                        classes=[],
                        total_found=0,
                        total_skipped=0,
                        total_errors=1,
                        status=ScrapingStatus.FAILED,
                        error_message=f"No configuration found for activity: {activity}"
                    )
                    continue
                
                try:
                    result = self.scraper_strategy.scrape_activity(driver, configs[activity])
                    results[activity] = result
                    
                    self.logger.info(f"Completed scrape for {activity}: "
                                   f"{len(result.classes)} classes, "
                                   f"{result.total_skipped} skipped, "
                                   f"{result.total_errors} errors")
                    
                except Exception as e:
                    self.logger.error(f"Error scraping activity {activity}: {e}")
                    results[activity] = ScrapingResult(
                        activity=activity,
                        classes=[],
                        total_found=0,
                        total_skipped=0,
                        total_errors=1,
                        status=ScrapingStatus.FAILED,
                        error_message=str(e)
                    )
        
        except Exception as e:
            self.logger.error(f"Fatal error during scraping session: {e}")
            # Create failed results for all activities
            for activity in activities:
                if activity not in results:
                    results[activity] = ScrapingResult(
                        activity=activity,
                        classes=[],
                        total_found=0,
                        total_skipped=0,
                        total_errors=1,
                        status=ScrapingStatus.FAILED,
                        error_message=f"Session error: {str(e)}"
                    )
        
        finally:
            # Always close the session
            self.logger.info("Closing browser session")
            self.session_manager.close_session()
        
        return results
    
    def scrape_single_activity(self, username: str, password: str, 
                              activity: str, config: ScrapingConfig) -> ScrapingResult:
        """
        Scrape a single activity.
        
        Args:
            username: Login username
            password: Login password
            activity: Activity name to scrape
            config: Scraping configuration
            
        Returns:
            ScrapingResult for the activity
        """
        results = self.scrape_activities(username, password, [activity], {activity: config})
        return results[activity]
