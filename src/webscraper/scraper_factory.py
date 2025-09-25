"""Factory for creating web scrapers from configuration."""

from typing import Dict, Any
from ..io.strategy_loader import strategy_loader
from .scraper_manager import ScraperManager
from .session_manager import GenericSessionManager
from ..core.logging import get_logger

logger = get_logger(__name__)


class ScraperFactory:
    """Factory for creating web scrapers based on configuration."""
    
    @staticmethod
    def create_scraper(scraper_config: Dict[str, Any]) -> ScraperManager:
        """
        Create a scraper manager from configuration.
        
        Args:
            scraper_config: Configuration dictionary for the scraper
            
        Returns:
            Configured ScraperManager instance
        """
        try:
            # Load login strategy
            login_strategy_path = scraper_config.get('login_strategy')
            if not login_strategy_path:
                raise ValueError("login_strategy is required in scraper configuration")
            
            login_strategy = strategy_loader.instantiate_strategy(login_strategy_path)
            logger.debug(f"Loaded login strategy: {login_strategy_path}")
            
            # Create session manager with login strategy
            session_manager_path = scraper_config.get('session_manager')
            if not session_manager_path:
                raise ValueError("session_manager is required in scraper configuration")
            
            # Extract session configuration
            headless = scraper_config.get('headless', True)
            container_mode = scraper_config.get('container_mode', True)  # This will be overridden by ScrapingConfig
            
            # Create session manager (assuming GenericSessionManager for now)
            session_manager = GenericSessionManager(
                login_strategy=login_strategy,
                headless=headless,
                container_mode=container_mode
            )
            logger.debug(f"Created session manager: {session_manager_path}")
            
            # Load scraper strategy
            scraper_strategy_path = scraper_config.get('scraper_strategy')
            if not scraper_strategy_path:
                raise ValueError("scraper_strategy is required in scraper configuration")
            
            scraper_strategy = strategy_loader.instantiate_strategy(scraper_strategy_path)
            logger.debug(f"Loaded scraper strategy: {scraper_strategy_path}")
            
            # Create scraper manager
            scraper_manager = ScraperManager(
                session_manager=session_manager,
                scraper_strategy=scraper_strategy
            )
            
            logger.info("Successfully created scraper manager")
            return scraper_manager
            
        except Exception as e:
            logger.error(f"Failed to create scraper: {e}")
            raise
    
    @staticmethod
    def create_scrapers_from_config(scrapers_config: Dict[str, Dict[str, Any]]) -> Dict[str, ScraperManager]:
        """
        Create multiple scrapers from configuration.
        
        Args:
            scrapers_config: Dictionary mapping scraper names to their configurations
            
        Returns:
            Dictionary mapping scraper names to ScraperManager instances
        """
        scrapers = {}
        
        for scraper_name, scraper_config in scrapers_config.items():
            try:
                logger.info(f"Creating scraper: {scraper_name}")
                scrapers[scraper_name] = ScraperFactory.create_scraper(scraper_config)
            except Exception as e:
                logger.error(f"Failed to create scraper {scraper_name}: {e}")
                # Continue creating other scrapers
                continue
        
        return scrapers
