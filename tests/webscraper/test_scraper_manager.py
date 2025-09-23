"""Tests for scraper manager."""

import pytest
from unittest.mock import MagicMock, patch

from src.webscraper.scraper_manager import ScraperManager
from src.webscraper.models import ScrapingConfig, ScrapingResult, ScrapingStatus
from src.webscraper.session_manager import SessionManager
from src.webscraper.scraper_strategy import ScraperStrategy


class MockSessionManager(SessionManager):
    """Mock session manager for testing."""
    
    def __init__(self, login_success=True):
        super().__init__()
        self.login_success = login_success
        self.create_calls = []
        self.login_calls = []
        self.close_calls = []
        self.mock_driver = MagicMock()
    
    def create_session(self):
        self.create_calls.append(True)
        self.driver = self.mock_driver
        return self.mock_driver
    
    def login(self, username, password):
        self.login_calls.append((username, password))
        return self.login_success
    
    def close_session(self):
        self.close_calls.append(True)
        self.driver = None


class MockScraperStrategy(ScraperStrategy):
    """Mock scraper strategy for testing."""
    
    def __init__(self, should_fail=False, fail_activity=None):
        super().__init__()
        self.should_fail = should_fail
        self.fail_activity = fail_activity
        self.scrape_calls = []
    
    def scrape_activity(self, driver, config):
        self.scrape_calls.append((driver, config))
        
        if self.should_fail or (self.fail_activity and config.activity == self.fail_activity):
            raise Exception(f"Scraping failed for {config.activity}")
        
        return ScrapingResult(
            activity=config.activity,
            classes=[],
            total_found=5,
            total_skipped=2,
            total_errors=0,
            status=ScrapingStatus.COMPLETED
        )
    
    def get_activity_url(self, activity):
        return f"https://example.com/{activity}"
    
    def extract_class_metadata(self, element):
        return {"title": "Test", "instructor": "Test", "activity": "Test"}
    
    def extract_duration_from_title(self, title):
        return 30


class TestScraperManager:
    """Test the ScraperManager class."""

    def test_scraper_manager_creation(self):
        """Test ScraperManager creation."""
        session_manager = MockSessionManager()
        scraper_strategy = MockScraperStrategy()
        
        manager = ScraperManager(session_manager, scraper_strategy)
        
        assert manager.session_manager == session_manager
        assert manager.scraper_strategy == scraper_strategy
        assert hasattr(manager, 'logger')

    def test_scrape_single_activity_success(self):
        """Test successful scraping of single activity."""
        session_manager = MockSessionManager(login_success=True)
        scraper_strategy = MockScraperStrategy()
        manager = ScraperManager(session_manager, scraper_strategy)
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=10,
            page_scrolls=3,
            existing_class_ids=set(),
            episode_numbering_data={}
        )
        
        result = manager.scrape_single_activity("test_user", "test_pass", "cycling", config)
        
        # Verify session management
        assert len(session_manager.create_calls) == 1
        assert len(session_manager.login_calls) == 1
        assert session_manager.login_calls[0] == ("test_user", "test_pass")
        assert len(session_manager.close_calls) == 1
        
        # Verify scraping
        assert len(scraper_strategy.scrape_calls) == 1
        assert scraper_strategy.scrape_calls[0][1] == config
        
        # Verify result
        assert result.activity == "cycling"
        assert result.status == ScrapingStatus.COMPLETED
        assert result.total_found == 5
        assert result.total_skipped == 2

    def test_scrape_single_activity_login_failure(self):
        """Test scraping with login failure."""
        session_manager = MockSessionManager(login_success=False)
        scraper_strategy = MockScraperStrategy()
        manager = ScraperManager(session_manager, scraper_strategy)
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=10,
            page_scrolls=3,
            existing_class_ids=set(),
            episode_numbering_data={}
        )
        
        result = manager.scrape_single_activity("test_user", "wrong_pass", "cycling", config)
        
        # Should still create and close session
        assert len(session_manager.create_calls) == 1
        assert len(session_manager.close_calls) == 1
        
        # Should not attempt scraping
        assert len(scraper_strategy.scrape_calls) == 0
        
        # Should return failed result
        assert result.activity == "cycling"
        assert result.status == ScrapingStatus.FAILED
        assert "Session error" in result.error_message

    def test_scrape_single_activity_scraping_failure(self):
        """Test scraping with scraping strategy failure."""
        session_manager = MockSessionManager(login_success=True)
        scraper_strategy = MockScraperStrategy(should_fail=True)
        manager = ScraperManager(session_manager, scraper_strategy)
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=10,
            page_scrolls=3,
            existing_class_ids=set(),
            episode_numbering_data={}
        )
        
        result = manager.scrape_single_activity("test_user", "test_pass", "cycling", config)
        
        # Session should be managed properly
        assert len(session_manager.create_calls) == 1
        assert len(session_manager.login_calls) == 1
        assert len(session_manager.close_calls) == 1
        
        # Scraping should be attempted
        assert len(scraper_strategy.scrape_calls) == 1
        
        # Should return failed result
        assert result.activity == "cycling"
        assert result.status == ScrapingStatus.FAILED
        assert "Scraping failed for cycling" in result.error_message

    def test_scrape_multiple_activities_success(self):
        """Test successful scraping of multiple activities."""
        session_manager = MockSessionManager(login_success=True)
        scraper_strategy = MockScraperStrategy()
        manager = ScraperManager(session_manager, scraper_strategy)
        
        configs = {
            "cycling": ScrapingConfig(
                activity="cycling",
                max_classes=10,
                page_scrolls=3,
                existing_class_ids=set(),
                episode_numbering_data={}
            ),
            "yoga": ScrapingConfig(
                activity="yoga",
                max_classes=5,
                page_scrolls=2,
                existing_class_ids=set(),
                episode_numbering_data={}
            )
        }
        
        results = manager.scrape_activities("test_user", "test_pass", ["cycling", "yoga"], configs)
        
        # Verify session management (should be called once for all activities)
        assert len(session_manager.create_calls) == 1
        assert len(session_manager.login_calls) == 1
        assert len(session_manager.close_calls) == 1
        
        # Verify scraping (should be called once per activity)
        assert len(scraper_strategy.scrape_calls) == 2
        
        # Verify results
        assert len(results) == 2
        assert "cycling" in results
        assert "yoga" in results
        assert results["cycling"].status == ScrapingStatus.COMPLETED
        assert results["yoga"].status == ScrapingStatus.COMPLETED

    def test_scrape_multiple_activities_partial_failure(self):
        """Test scraping multiple activities with one failing."""
        session_manager = MockSessionManager(login_success=True)
        scraper_strategy = MockScraperStrategy(fail_activity="yoga")
        manager = ScraperManager(session_manager, scraper_strategy)
        
        configs = {
            "cycling": ScrapingConfig(
                activity="cycling",
                max_classes=10,
                page_scrolls=3,
                existing_class_ids=set(),
                episode_numbering_data={}
            ),
            "yoga": ScrapingConfig(
                activity="yoga",
                max_classes=5,
                page_scrolls=2,
                existing_class_ids=set(),
                episode_numbering_data={}
            )
        }
        
        results = manager.scrape_activities("test_user", "test_pass", ["cycling", "yoga"], configs)
        
        # Should still attempt both
        assert len(scraper_strategy.scrape_calls) == 2
        
        # Verify results
        assert len(results) == 2
        assert results["cycling"].status == ScrapingStatus.COMPLETED
        assert results["yoga"].status == ScrapingStatus.FAILED
        assert "Scraping failed for yoga" in results["yoga"].error_message

    def test_scrape_activities_missing_config(self):
        """Test scraping activities with missing configuration."""
        session_manager = MockSessionManager(login_success=True)
        scraper_strategy = MockScraperStrategy()
        manager = ScraperManager(session_manager, scraper_strategy)
        
        configs = {
            "cycling": ScrapingConfig(
                activity="cycling",
                max_classes=10,
                page_scrolls=3,
                existing_class_ids=set(),
                episode_numbering_data={}
            )
            # Missing "yoga" config
        }
        
        results = manager.scrape_activities("test_user", "test_pass", ["cycling", "yoga"], configs)
        
        # Should still process cycling
        assert len(scraper_strategy.scrape_calls) == 1
        
        # Verify results
        assert len(results) == 2
        assert results["cycling"].status == ScrapingStatus.COMPLETED
        assert results["yoga"].status == ScrapingStatus.FAILED
        assert "No configuration found" in results["yoga"].error_message

    def test_scrape_activities_session_creation_failure(self):
        """Test scraping when session creation fails."""
        session_manager = MockSessionManager()
        session_manager.create_session = MagicMock(side_effect=Exception("Session creation failed"))
        scraper_strategy = MockScraperStrategy()
        manager = ScraperManager(session_manager, scraper_strategy)
        
        configs = {
            "cycling": ScrapingConfig(
                activity="cycling",
                max_classes=10,
                page_scrolls=3,
                existing_class_ids=set(),
                episode_numbering_data={}
            )
        }
        
        results = manager.scrape_activities("test_user", "test_pass", ["cycling"], configs)
        
        # Should not attempt scraping
        assert len(scraper_strategy.scrape_calls) == 0
        
        # Should return failed result
        assert results["cycling"].status == ScrapingStatus.FAILED
        assert "Session error" in results["cycling"].error_message
