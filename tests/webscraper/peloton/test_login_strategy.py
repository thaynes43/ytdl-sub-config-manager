"""Tests for Peloton login strategy."""

import pytest
from unittest.mock import patch, MagicMock
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.webscraper.peloton.login_strategy import PelotonLoginStrategy


class TestPelotonLoginStrategy:
    """Test the PelotonLoginStrategy class."""

    def test_peloton_login_strategy_creation(self):
        """Test PelotonLoginStrategy creation."""
        strategy = PelotonLoginStrategy()
        assert strategy.login_wait_time == 15.0
        assert hasattr(strategy, 'logger')

    def test_peloton_login_strategy_custom_wait_time(self):
        """Test PelotonLoginStrategy creation with custom wait time."""
        strategy = PelotonLoginStrategy(login_wait_time=30.0)
        assert strategy.login_wait_time == 30.0

    @patch('src.webscraper.peloton.login_strategy.time.sleep')
    def test_login_success(self, mock_sleep):
        """Test successful login."""
        strategy = PelotonLoginStrategy(login_wait_time=5.0)
        
        # Mock driver and elements
        mock_driver = MagicMock()
        mock_username_field = MagicMock()
        mock_password_field = MagicMock()
        mock_submit_button = MagicMock()
        
        # Setup find_element calls
        def mock_find_element(by, value):
            if value == "usernameOrEmail":
                return mock_username_field
            elif value == "password":
                return mock_password_field
            elif value == 'button[type="submit"]':
                return mock_submit_button
            return MagicMock()
        
        mock_driver.find_element.side_effect = mock_find_element
        mock_driver.current_url = "https://members.onepeloton.com/home"  # Not login page
        
        result = strategy.login(mock_driver, "test_user", "test_pass")
        
        # Verify login process
        assert result is True
        mock_driver.get.assert_called_once_with("https://members.onepeloton.com/login")
        mock_username_field.send_keys.assert_called_once_with("test_user")
        mock_password_field.send_keys.assert_called_once_with("test_pass")
        mock_submit_button.click.assert_called_once()
        
        # Verify sleep calls (initial page load + login wait)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(10)  # Initial page load
        mock_sleep.assert_any_call(5.0)  # Custom login wait time

    @patch('src.webscraper.peloton.login_strategy.time.sleep')
    def test_login_still_on_login_page(self, mock_sleep):
        """Test login failure when still on login page after attempt."""
        strategy = PelotonLoginStrategy()
        
        mock_driver = MagicMock()
        mock_driver.find_element.return_value = MagicMock()
        mock_driver.current_url = "https://members.onepeloton.com/login"  # Still on login page
        
        result = strategy.login(mock_driver, "test_user", "wrong_pass")
        
        assert result is False

    @patch('src.webscraper.peloton.login_strategy.time.sleep')
    def test_login_username_element_not_found(self, mock_sleep):
        """Test login failure when username element is not found."""
        strategy = PelotonLoginStrategy()
        
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = NoSuchElementException("Username field not found")
        
        result = strategy.login(mock_driver, "test_user", "test_pass")
        
        assert result is False

    @patch('src.webscraper.peloton.login_strategy.time.sleep')
    def test_login_password_element_not_found(self, mock_sleep):
        """Test login failure when password element is not found."""
        strategy = PelotonLoginStrategy()
        
        mock_driver = MagicMock()
        
        def mock_find_element(by, value):
            if value == "usernameOrEmail":
                return MagicMock()  # Username field found
            elif value == "password":
                raise NoSuchElementException("Password field not found")
            return MagicMock()
        
        mock_driver.find_element.side_effect = mock_find_element
        
        result = strategy.login(mock_driver, "test_user", "test_pass")
        
        assert result is False

    @patch('src.webscraper.peloton.login_strategy.time.sleep')
    def test_login_submit_button_not_found(self, mock_sleep):
        """Test login failure when submit button is not found."""
        strategy = PelotonLoginStrategy()
        
        mock_driver = MagicMock()
        
        def mock_find_element(by, value):
            if value == "usernameOrEmail":
                return MagicMock()
            elif value == "password":
                return MagicMock()
            elif value == 'button[type="submit"]':
                raise NoSuchElementException("Submit button not found")
            return MagicMock()
        
        mock_driver.find_element.side_effect = mock_find_element
        
        result = strategy.login(mock_driver, "test_user", "test_pass")
        
        assert result is False

    @patch('src.webscraper.peloton.login_strategy.time.sleep')
    def test_login_timeout_exception(self, mock_sleep):
        """Test login failure with timeout exception."""
        strategy = PelotonLoginStrategy()
        
        mock_driver = MagicMock()
        mock_driver.find_element.side_effect = TimeoutException("Timeout waiting for element")
        
        result = strategy.login(mock_driver, "test_user", "test_pass")
        
        assert result is False

    @patch('src.webscraper.peloton.login_strategy.time.sleep')
    def test_login_unexpected_exception(self, mock_sleep):
        """Test login failure with unexpected exception."""
        strategy = PelotonLoginStrategy()
        
        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("Unexpected error")
        
        result = strategy.login(mock_driver, "test_user", "test_pass")
        
        assert result is False

    @patch('src.webscraper.peloton.login_strategy.time.sleep')
    def test_login_url_check_case_insensitive(self, mock_sleep):
        """Test that URL check for login failure is case insensitive."""
        strategy = PelotonLoginStrategy()
        
        mock_driver = MagicMock()
        mock_driver.find_element.return_value = MagicMock()
        mock_driver.current_url = "https://members.onepeloton.com/LOGIN"  # Uppercase LOGIN
        
        result = strategy.login(mock_driver, "test_user", "wrong_pass")
        
        assert result is False  # Should detect we're still on login page

    @patch('src.webscraper.peloton.login_strategy.time.sleep')
    def test_login_success_different_redirect_url(self, mock_sleep):
        """Test successful login with different redirect URL."""
        strategy = PelotonLoginStrategy()
        
        mock_driver = MagicMock()
        mock_driver.find_element.return_value = MagicMock()
        mock_driver.current_url = "https://members.onepeloton.com/classes"  # Redirected to classes
        
        result = strategy.login(mock_driver, "test_user", "test_pass")
        
        assert result is True  # Should detect successful login (not on login page)
