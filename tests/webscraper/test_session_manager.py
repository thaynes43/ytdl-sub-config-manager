"""Tests for session manager classes."""

import pytest
from unittest.mock import patch, MagicMock, call
import tempfile
import time

from src.webscraper.session_manager import (
    SessionManager, GenericSessionManager, LoginStrategy
)


class MockLoginStrategy(LoginStrategy):
    """Mock login strategy for testing."""
    
    def __init__(self, should_succeed=True):
        super().__init__()
        self.should_succeed = should_succeed
        self.login_calls = []
    
    def login(self, driver, username, password):
        self.login_calls.append((driver, username, password))
        return self.should_succeed


class TestSessionManager:
    """Test the abstract SessionManager class."""

    def test_session_manager_is_abstract(self):
        """Test that SessionManager cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SessionManager()

    @patch('src.webscraper.session_manager.webdriver.Chrome')
    @patch('src.webscraper.session_manager.Service')
    @patch('src.webscraper.session_manager.tempfile.mkdtemp')
    def test_create_session_default_options(self, mock_mkdtemp, mock_service, mock_chrome):
        """Test create_session with default options."""
        # Setup mocks
        mock_mkdtemp.return_value = "/tmp/test-profile"
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Create a concrete implementation for testing
        class TestSessionManager(SessionManager):
            def login(self, username, password):
                return True
        
        session_manager = TestSessionManager(headless=True, container_mode=False)
        result = session_manager.create_session()
        
        assert result == mock_driver
        assert session_manager.driver == mock_driver
        mock_mkdtemp.assert_called_once()
        mock_chrome.assert_called_once()

    @patch('src.webscraper.session_manager.webdriver.Chrome')
    @patch('src.webscraper.session_manager.Service')
    @patch('src.webscraper.session_manager.tempfile.mkdtemp')
    def test_create_session_container_mode(self, mock_mkdtemp, mock_service, mock_chrome):
        """Test create_session with container mode enabled."""
        mock_mkdtemp.return_value = "/tmp/test-profile"
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        mock_service_instance = MagicMock()
        mock_service.return_value = mock_service_instance
        
        class TestSessionManager(SessionManager):
            def login(self, username, password):
                return True
        
        session_manager = TestSessionManager(headless=True, container_mode=True)
        result = session_manager.create_session()
        
        assert result == mock_driver
        mock_service.assert_called_once_with("/usr/bin/chromedriver")
        mock_chrome.assert_called_once()
        # Verify that Chrome was called with the service and options
        call_args = mock_chrome.call_args
        assert call_args.kwargs['service'] == mock_service_instance
        assert 'options' in call_args.kwargs

    @patch('src.webscraper.session_manager.webdriver.Chrome')
    def test_create_session_failure(self, mock_chrome):
        """Test create_session when Chrome fails to start."""
        mock_chrome.side_effect = Exception("Chrome failed to start")
        
        class TestSessionManager(SessionManager):
            def login(self, username, password):
                return True
        
        session_manager = TestSessionManager()
        
        with pytest.raises(Exception, match="Chrome failed to start"):
            session_manager.create_session()

    def test_close_session_with_driver(self):
        """Test close_session when driver exists."""
        class TestSessionManager(SessionManager):
            def login(self, username, password):
                return True
        
        session_manager = TestSessionManager()
        mock_driver = MagicMock()
        session_manager.driver = mock_driver
        
        session_manager.close_session()
        
        mock_driver.quit.assert_called_once()
        assert session_manager.driver is None

    def test_close_session_without_driver(self):
        """Test close_session when no driver exists."""
        class TestSessionManager(SessionManager):
            def login(self, username, password):
                return True
        
        session_manager = TestSessionManager()
        session_manager.driver = None
        
        # Should not raise an exception
        session_manager.close_session()

    def test_close_session_driver_quit_fails(self):
        """Test close_session when driver.quit() fails."""
        class TestSessionManager(SessionManager):
            def login(self, username, password):
                return True
        
        session_manager = TestSessionManager()
        mock_driver = MagicMock()
        mock_driver.quit.side_effect = Exception("Quit failed")
        session_manager.driver = mock_driver
        
        # Should not raise an exception, but should still set driver to None
        session_manager.close_session()
        assert session_manager.driver is None


class TestGenericSessionManager:
    """Test the GenericSessionManager class."""

    def test_generic_session_manager_creation(self):
        """Test GenericSessionManager creation."""
        login_strategy = MockLoginStrategy()
        session_manager = GenericSessionManager(
            login_strategy=login_strategy,
            headless=True,
            container_mode=False
        )
        
        assert session_manager.login_strategy == login_strategy
        assert session_manager.headless is True
        assert session_manager.container_mode is False

    def test_login_success(self):
        """Test successful login."""
        login_strategy = MockLoginStrategy(should_succeed=True)
        session_manager = GenericSessionManager(login_strategy=login_strategy)
        
        mock_driver = MagicMock()
        session_manager.driver = mock_driver
        
        result = session_manager.login("test_user", "test_pass")
        
        assert result is True
        assert len(login_strategy.login_calls) == 1
        assert login_strategy.login_calls[0] == (mock_driver, "test_user", "test_pass")

    def test_login_failure(self):
        """Test failed login."""
        login_strategy = MockLoginStrategy(should_succeed=False)
        session_manager = GenericSessionManager(login_strategy=login_strategy)
        
        mock_driver = MagicMock()
        session_manager.driver = mock_driver
        
        result = session_manager.login("test_user", "test_pass")
        
        assert result is False
        assert len(login_strategy.login_calls) == 1

    def test_login_without_driver(self):
        """Test login when no driver is available."""
        login_strategy = MockLoginStrategy()
        session_manager = GenericSessionManager(login_strategy=login_strategy)
        
        # No driver set
        session_manager.driver = None
        
        with pytest.raises(RuntimeError, match="No active browser session"):
            session_manager.login("test_user", "test_pass")


class TestLoginStrategy:
    """Test the abstract LoginStrategy class."""

    def test_login_strategy_is_abstract(self):
        """Test that LoginStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LoginStrategy()

    def test_login_strategy_has_logger(self):
        """Test that LoginStrategy subclasses have logger."""
        class TestLoginStrategy(LoginStrategy):
            def login(self, driver, username, password):
                return True
        
        strategy = TestLoginStrategy()
        assert hasattr(strategy, 'logger')
        assert strategy.logger is not None
