"""Tests for scraper strategy classes."""

import pytest
import time
from unittest.mock import patch, MagicMock

from src.webscraper.scraper_strategy import ScraperStrategy
from src.webscraper.models import ScrapingConfig, ScrapingResult, ScrapingStatus


class MockScraperStrategy(ScraperStrategy):
    """Mock scraper strategy for testing."""
    
    def __init__(self):
        super().__init__()
        self.scrape_calls = []
        self.url_calls = []
        self.metadata_calls = []
        self.duration_calls = []
    
    def scrape_activity(self, driver, config):
        self.scrape_calls.append((driver, config))
        return ScrapingResult(
            activity=config.activity,
            classes=[],
            total_found=0,
            total_skipped=0,
            total_errors=0,
            status=ScrapingStatus.COMPLETED
        )
    
    def get_activity_url(self, activity):
        self.url_calls.append(activity)
        return f"https://example.com/{activity}"
    
    def extract_class_metadata(self, element):
        self.metadata_calls.append(element)
        return {"title": "Test Class", "instructor": "Test Instructor", "activity": "Test"}
    
    def extract_duration_from_title(self, title):
        self.duration_calls.append(title)
        return 30


class TestScraperStrategy:
    """Test the abstract ScraperStrategy class."""

    def test_scraper_strategy_is_abstract(self):
        """Test that ScraperStrategy cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ScraperStrategy()

    def test_scraper_strategy_has_logger(self):
        """Test that ScraperStrategy subclasses have logger."""
        strategy = MockScraperStrategy()
        assert hasattr(strategy, 'logger')
        assert strategy.logger is not None

    @patch('src.webscraper.scraper_strategy.time.sleep')
    def test_scroll_to_load_content(self, mock_sleep):
        """Test _scroll_to_load_content helper method."""
        strategy = MockScraperStrategy()
        mock_driver = MagicMock()
        
        strategy._scroll_to_load_content(mock_driver, scrolls=3, pause_time=2.0)
        
        # Should call execute_script 3 times
        assert mock_driver.execute_script.call_count == 3
        expected_script = "window.scrollTo(0, document.body.scrollHeight);"
        for call in mock_driver.execute_script.call_args_list:
            assert call[0][0] == expected_script
        
        # Should sleep 3 times with 2.0 seconds each
        assert mock_sleep.call_count == 3
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 2.0

    @patch('src.webscraper.scraper_strategy.time.sleep')
    def test_scroll_to_load_content_default_pause(self, mock_sleep):
        """Test _scroll_to_load_content with default pause time."""
        strategy = MockScraperStrategy()
        mock_driver = MagicMock()
        
        strategy._scroll_to_load_content(mock_driver, scrolls=2)
        
        # Should use default pause time of 3.0 seconds
        assert mock_sleep.call_count == 2
        for call in mock_sleep.call_args_list:
            assert call[0][0] == 3.0

    @patch('src.webscraper.scraper_strategy.time.sleep')
    def test_wait_for_page_load(self, mock_sleep):
        """Test _wait_for_page_load helper method."""
        strategy = MockScraperStrategy()
        mock_driver = MagicMock()
        
        strategy._wait_for_page_load(mock_driver, wait_time=5.0)
        
        mock_sleep.assert_called_once_with(5.0)

    @patch('src.webscraper.scraper_strategy.time.sleep')
    def test_wait_for_page_load_default_time(self, mock_sleep):
        """Test _wait_for_page_load with default wait time."""
        strategy = MockScraperStrategy()
        mock_driver = MagicMock()
        
        strategy._wait_for_page_load(mock_driver)
        
        mock_sleep.assert_called_once_with(10.0)

    def test_abstract_methods_must_be_implemented(self):
        """Test that abstract methods must be implemented by subclasses."""
        strategy = MockScraperStrategy()
        mock_driver = MagicMock()
        config = ScrapingConfig(
            activity="test",
            max_classes=5,
            page_scrolls=2,
            existing_class_ids=set(),
            episode_numbering_data={}
        )
        
        # These should not raise NotImplementedError
        result = strategy.scrape_activity(mock_driver, config)
        assert isinstance(result, ScrapingResult)
        
        url = strategy.get_activity_url("test")
        assert url == "https://example.com/test"
        
        metadata = strategy.extract_class_metadata("test_element")
        assert metadata == {"title": "Test Class", "instructor": "Test Instructor", "activity": "Test"}
        
        duration = strategy.extract_duration_from_title("30 min Test Class")
        assert duration == 30

    def test_mock_strategy_tracks_calls(self):
        """Test that mock strategy tracks method calls for testing."""
        strategy = MockScraperStrategy()
        mock_driver = MagicMock()
        config = ScrapingConfig(
            activity="cycling",
            max_classes=10,
            page_scrolls=3,
            existing_class_ids={"existing-1"},
            episode_numbering_data={30: 5}
        )
        
        # Call methods
        strategy.scrape_activity(mock_driver, config)
        strategy.get_activity_url("yoga")
        strategy.extract_class_metadata("element1")
        strategy.extract_duration_from_title("45 min Power Class")
        
        # Verify calls were tracked
        assert len(strategy.scrape_calls) == 1
        assert strategy.scrape_calls[0] == (mock_driver, config)
        
        assert len(strategy.url_calls) == 1
        assert strategy.url_calls[0] == "yoga"
        
        assert len(strategy.metadata_calls) == 1
        assert strategy.metadata_calls[0] == "element1"
        
        assert len(strategy.duration_calls) == 1
        assert strategy.duration_calls[0] == "45 min Power Class"
