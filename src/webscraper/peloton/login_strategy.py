"""Peloton-specific login strategy."""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from ..session_manager import LoginStrategy


class PelotonLoginStrategy(LoginStrategy):
    """Login strategy for Peloton website."""
    
    def __init__(self, login_wait_time: float = 15.0):
        super().__init__()
        self.login_wait_time = login_wait_time
    
    def login(self, driver: webdriver.Chrome, username: str, password: str) -> bool:
        """
        Login to Peloton website.
        
        Args:
            driver: Active browser session
            username: Peloton username
            password: Peloton password
            
        Returns:
            True if login successful, False otherwise
        """
        try:
            self.logger.info("Navigating to Peloton login page")
            driver.get("https://members.onepeloton.com/login")
            time.sleep(10)  # Wait for page to load
            
            # Find and fill username field
            self.logger.debug("Entering username")
            username_field = driver.find_element(By.NAME, "usernameOrEmail")
            username_field.send_keys(username)
            
            # Find and fill password field
            self.logger.debug("Entering password")
            password_field = driver.find_element(By.NAME, "password")
            password_field.send_keys(password)
            
            # Submit login form
            self.logger.debug("Submitting login form")
            submit_button = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            submit_button.click()
            
            # Wait for login to complete
            self.logger.info(f"Waiting {self.login_wait_time}s for login to complete")
            time.sleep(self.login_wait_time)
            
            # Check if login was successful by looking for login-specific elements
            # If we're still on the login page, login failed
            current_url = driver.current_url
            if "login" in current_url.lower():
                self.logger.error("Login appears to have failed - still on login page")
                return False
            
            self.logger.info("Login completed successfully")
            return True
            
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"Login failed - element not found: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Login failed with unexpected error: {e}")
            return False
