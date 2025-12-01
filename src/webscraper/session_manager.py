"""Generic session management for web scraping."""

import tempfile
import time
from abc import ABC, abstractmethod
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from ..core.logging import get_logger


class SessionManager(ABC):
    """Abstract base class for web session management."""
    
    def __init__(self, headless: bool = True, container_mode: bool = True):
        self.headless = headless
        self.container_mode = container_mode
        self.driver: Optional[webdriver.Chrome] = None
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    def create_session(self) -> webdriver.Chrome:
        """Create and configure a new browser session."""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Container/pod options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # Enable performance logging to capture network requests
        chrome_options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        if self.container_mode:
            chrome_options.binary_location = "/usr/bin/chromium"
        
        # Create temporary profile directory
        tmp_profile = tempfile.mkdtemp()
        self.logger.debug(f"Using Chrome user-data-dir: {tmp_profile}")
        chrome_options.add_argument(f'--user-data-dir={tmp_profile}')
        
        self.logger.debug(f"Chrome options: {chrome_options.arguments}")
        
        # Create service and driver
        service = None
        if self.container_mode:
            service = Service("/usr/bin/chromedriver")
        
        try:
            if self.container_mode:
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            
            self.logger.info("Browser session created successfully")
            return self.driver
            
        except Exception as e:
            self.logger.error(f"Failed to create browser session: {e}")
            raise
    
    @abstractmethod
    def login(self, username: str, password: str) -> bool:
        """Login to the website. Must be implemented by subclasses."""
        pass
    
    def close_session(self) -> None:
        """Close the browser session."""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Browser session closed")
            except Exception as e:
                self.logger.warning(f"Error closing browser session: {e}")
            finally:
                self.driver = None


class GenericSessionManager(SessionManager):
    """Generic session manager with configurable login logic."""
    
    def __init__(self, login_strategy, headless: bool = True, container_mode: bool = True):
        super().__init__(headless, container_mode)
        self.login_strategy = login_strategy
    
    def login(self, username: str, password: str) -> bool:
        """Login using the injected login strategy."""
        if not self.driver:
            raise RuntimeError("No active browser session. Call create_session() first.")
        
        return self.login_strategy.login(self.driver, username, password)


class LoginStrategy(ABC):
    """Abstract base class for login strategies."""
    
    def __init__(self):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    def login(self, driver: webdriver.Chrome, username: str, password: str) -> bool:
        """Perform login. Returns True if successful."""
        pass
