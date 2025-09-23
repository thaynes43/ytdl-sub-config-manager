"""Tests for scraper factory."""

import pytest
from unittest.mock import patch, MagicMock

from src.webscraper.scraper_factory import ScraperFactory
from src.webscraper.scraper_manager import ScraperManager


class TestScraperFactory:
    """Test the ScraperFactory class."""

    @patch('src.webscraper.scraper_factory.strategy_loader')
    def test_create_scraper_success(self, mock_strategy_loader):
        """Test successful scraper creation."""
        # Setup mocks
        mock_login_strategy = MagicMock()
        mock_scraper_strategy = MagicMock()
        
        def mock_instantiate(path):
            if "login_strategy" in path:
                return mock_login_strategy
            elif "scraper_strategy" in path:
                return mock_scraper_strategy
            return MagicMock()
        
        mock_strategy_loader.instantiate_strategy.side_effect = mock_instantiate
        
        config = {
            'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
            'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
            'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy',
            'headless': True,
            'container_mode': False,
            'scroll_pause_time': 3.0,
            'login_wait_time': 15.0,
            'page_load_wait_time': 10.0
        }
        
        scraper = ScraperFactory.create_scraper(config)
        
        # Verify scraper manager was created
        assert isinstance(scraper, ScraperManager)
        assert scraper.scraper_strategy == mock_scraper_strategy
        
        # Verify strategy loader was called correctly
        expected_calls = [
            'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
            'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
        ]
        actual_calls = [call[0][0] for call in mock_strategy_loader.instantiate_strategy.call_args_list]
        for expected in expected_calls:
            assert expected in actual_calls

    def test_create_scraper_missing_login_strategy(self):
        """Test scraper creation with missing login_strategy."""
        config = {
            'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
            'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
        }
        
        with pytest.raises(ValueError, match="login_strategy is required"):
            ScraperFactory.create_scraper(config)

    def test_create_scraper_missing_session_manager(self):
        """Test scraper creation with missing session_manager."""
        config = {
            'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
            'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
        }
        
        with pytest.raises(ValueError, match="session_manager is required"):
            ScraperFactory.create_scraper(config)

    def test_create_scraper_missing_scraper_strategy(self):
        """Test scraper creation with missing scraper_strategy."""
        config = {
            'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
            'session_manager': 'src.webscraper.session_manager:GenericSessionManager'
        }
        
        with pytest.raises(ValueError, match="scraper_strategy is required"):
            ScraperFactory.create_scraper(config)

    @patch('src.webscraper.scraper_factory.strategy_loader')
    def test_create_scraper_strategy_loading_failure(self, mock_strategy_loader):
        """Test scraper creation when strategy loading fails."""
        mock_strategy_loader.instantiate_strategy.side_effect = ImportError("Module not found")
        
        config = {
            'login_strategy': 'invalid.module:InvalidClass',
            'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
            'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
        }
        
        with pytest.raises(ImportError):
            ScraperFactory.create_scraper(config)

    @patch('src.webscraper.scraper_factory.strategy_loader')
    def test_create_scraper_with_defaults(self, mock_strategy_loader):
        """Test scraper creation uses default values for missing optional config."""
        mock_login_strategy = MagicMock()
        mock_scraper_strategy = MagicMock()
        
        def mock_instantiate(path):
            if "login_strategy" in path:
                return mock_login_strategy
            elif "scraper_strategy" in path:
                return mock_scraper_strategy
            return MagicMock()
        
        mock_strategy_loader.instantiate_strategy.side_effect = mock_instantiate
        
        # Minimal config without optional parameters
        config = {
            'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
            'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
            'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
        }
        
        scraper = ScraperFactory.create_scraper(config)
        
        # Should still create scraper successfully with defaults
        assert isinstance(scraper, ScraperManager)
        
        # Verify session manager was created with default values
        # (headless=True, container_mode=True are the defaults)
        assert scraper.session_manager.headless is True
        assert scraper.session_manager.container_mode is True

    @patch('src.webscraper.scraper_factory.strategy_loader')
    def test_create_scrapers_from_config_success(self, mock_strategy_loader):
        """Test creating multiple scrapers from configuration."""
        mock_login_strategy = MagicMock()
        mock_scraper_strategy = MagicMock()
        
        def mock_instantiate(path):
            if "login_strategy" in path:
                return mock_login_strategy
            elif "scraper_strategy" in path:
                return mock_scraper_strategy
            return MagicMock()
        
        mock_strategy_loader.instantiate_strategy.side_effect = mock_instantiate
        
        scrapers_config = {
            'peloton.com': {
                'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
                'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
                'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
            },
            'example.com': {
                'login_strategy': 'src.webscraper.example.login_strategy:ExampleLoginStrategy',
                'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
                'scraper_strategy': 'src.webscraper.example.scraper_strategy:ExampleScraperStrategy'
            }
        }
        
        scrapers = ScraperFactory.create_scrapers_from_config(scrapers_config)
        
        assert len(scrapers) == 2
        assert 'peloton.com' in scrapers
        assert 'example.com' in scrapers
        assert isinstance(scrapers['peloton.com'], ScraperManager)
        assert isinstance(scrapers['example.com'], ScraperManager)

    @patch('src.webscraper.scraper_factory.strategy_loader')
    def test_create_scrapers_from_config_partial_failure(self, mock_strategy_loader):
        """Test creating scrapers when one fails."""
        mock_login_strategy = MagicMock()
        mock_scraper_strategy = MagicMock()
        
        def mock_instantiate(path):
            if "example" in path:
                raise ImportError("Example module not found")
            if "login_strategy" in path:
                return mock_login_strategy
            elif "scraper_strategy" in path:
                return mock_scraper_strategy
            return MagicMock()
        
        mock_strategy_loader.instantiate_strategy.side_effect = mock_instantiate
        
        scrapers_config = {
            'peloton.com': {
                'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
                'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
                'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
            },
            'example.com': {
                'login_strategy': 'src.webscraper.example.login_strategy:ExampleLoginStrategy',
                'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
                'scraper_strategy': 'src.webscraper.example.scraper_strategy:ExampleScraperStrategy'
            }
        }
        
        scrapers = ScraperFactory.create_scrapers_from_config(scrapers_config)
        
        # Should create the successful one and skip the failed one
        assert len(scrapers) == 1
        assert 'peloton.com' in scrapers
        assert 'example.com' not in scrapers
        assert isinstance(scrapers['peloton.com'], ScraperManager)

    def test_create_scrapers_from_config_empty(self):
        """Test creating scrapers from empty configuration."""
        scrapers_config = {}
        
        scrapers = ScraperFactory.create_scrapers_from_config(scrapers_config)
        
        assert scrapers == {}

    @patch('src.webscraper.scraper_factory.strategy_loader')
    def test_create_scraper_custom_session_config(self, mock_strategy_loader):
        """Test scraper creation with custom session configuration."""
        mock_login_strategy = MagicMock()
        mock_scraper_strategy = MagicMock()
        
        def mock_instantiate(path):
            if "login_strategy" in path:
                return mock_login_strategy
            elif "scraper_strategy" in path:
                return mock_scraper_strategy
            return MagicMock()
        
        mock_strategy_loader.instantiate_strategy.side_effect = mock_instantiate
        
        config = {
            'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
            'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
            'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy',
            'headless': False,
            'container_mode': True,
            'scroll_pause_time': 5.0,
            'login_wait_time': 30.0,
            'page_load_wait_time': 20.0
        }
        
        scraper = ScraperFactory.create_scraper(config)
        
        # Verify custom configuration was applied
        assert isinstance(scraper, ScraperManager)
        assert scraper.session_manager.headless is False
        assert scraper.session_manager.container_mode is True
