"""Tests for dynamic scrolling functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from selenium.webdriver.common.by import By

from src.webscraper.scraper_strategy import ScraperStrategy
from src.webscraper.models import ScrapingConfig, ScrapingResult, ScrapingStatus


class MockScraperStrategy(ScraperStrategy):
    """Mock implementation of ScraperStrategy for testing."""
    
    def scrape_activity(self, driver, config):
        return ScrapingResult(
            activity=config.activity,
            classes=[],
            total_found=0,
            total_skipped=0,
            total_errors=0,
            status=ScrapingStatus.COMPLETED
        )
    
    def get_activity_url(self, activity):
        return f"https://example.com/{activity}"
    
    def extract_class_metadata(self, element):
        return {'title': 'Test Class', 'instructor': 'Test Instructor', 'activity': 'cycling'}
    
    def extract_duration_from_title(self, title):
        return 30
    
    def _extract_class_id(self, url):
        """Extract class ID from URL for testing."""
        if "classId=" in url:
            return url.split("classId=")[1].split("&")[0]
        return ""


class TestDynamicScrolling:
    """Test dynamic scrolling functionality."""
    
    def test_scroll_dynamically_until_limit_finds_enough_classes(self):
        """Test that dynamic scrolling stops when enough classes are found."""
        strategy = MockScraperStrategy()
        driver = Mock()
        
        # Mock config with dynamic scrolling enabled
        config = ScrapingConfig(
            activity="cycling",
            max_classes=5,
            page_scrolls=10,
            existing_class_ids=set(),
            episode_numbering_data={},
            subscriptions_existing_classes=0,
            dynamic_scrolling=True,
            max_scrolls=20
        )
        
        # Mock links that represent new classes
        mock_links = []
        for i in range(10):  # More than needed
            link = Mock()
            link.get_attribute.return_value = f"https://example.com/class?classId=class{i}"
            mock_links.append(link)
        
        driver.find_elements.return_value = mock_links
        
        with patch('time.sleep'):
            scrolls_performed = strategy._scroll_dynamically_until_limit(driver, config, 1.0)
        
        # Should stop after first scroll since we found enough classes
        assert scrolls_performed == 1
        assert driver.execute_script.call_count == 1
    
    def test_scroll_dynamically_until_limit_hits_max_scrolls(self):
        """Test that dynamic scrolling stops at max scrolls limit."""
        strategy = MockScraperStrategy()
        driver = Mock()
        
        # Mock config with dynamic scrolling enabled
        config = ScrapingConfig(
            activity="cycling",
            max_classes=5,
            page_scrolls=10,
            existing_class_ids=set(),
            episode_numbering_data={},
            subscriptions_existing_classes=0,
            dynamic_scrolling=True,
            max_scrolls=3  # Low limit for testing
        )
        
        # Mock links that represent fewer classes than needed
        mock_links = []
        for i in range(2):  # Less than needed
            link = Mock()
            link.get_attribute.return_value = f"https://example.com/class?classId=class{i}"
            mock_links.append(link)
        
        driver.find_elements.return_value = mock_links
        
        with patch('time.sleep'):
            scrolls_performed = strategy._scroll_dynamically_until_limit(driver, config, 1.0)
        
        # Should stop at max scrolls limit
        assert scrolls_performed == 3
        assert driver.execute_script.call_count == 3
    
    def test_scroll_dynamically_until_limit_with_existing_classes(self):
        """Test that dynamic scrolling accounts for existing classes in subscriptions."""
        strategy = MockScraperStrategy()
        driver = Mock()
        
        # Mock config with existing classes in subscriptions
        config = ScrapingConfig(
            activity="cycling",
            max_classes=10,
            page_scrolls=10,
            existing_class_ids=set(),
            episode_numbering_data={},
            subscriptions_existing_classes=7,  # Already have 7 classes
            dynamic_scrolling=True,
            max_scrolls=20
        )
        
        # Mock links that represent new classes
        mock_links = []
        for i in range(5):  # Exactly what we need (10 - 7 = 3, but we'll find 5)
            link = Mock()
            link.get_attribute.return_value = f"https://example.com/class?classId=class{i}"
            mock_links.append(link)
        
        driver.find_elements.return_value = mock_links
        
        with patch('time.sleep'):
            scrolls_performed = strategy._scroll_dynamically_until_limit(driver, config, 1.0)
        
        # Should stop after first scroll since we found enough new classes
        assert scrolls_performed == 1
        assert driver.execute_script.call_count == 1
    
    def test_scroll_dynamically_until_limit_filters_existing_class_ids(self):
        """Test that dynamic scrolling filters out existing class IDs."""
        strategy = MockScraperStrategy()
        driver = Mock()
        
        # Mock config with some existing class IDs
        config = ScrapingConfig(
            activity="cycling",
            max_classes=5,
            page_scrolls=10,
            existing_class_ids={"existing1", "existing2"},
            episode_numbering_data={},
            subscriptions_existing_classes=0,
            dynamic_scrolling=True,
            max_scrolls=20
        )
        
        # Mock links with mix of new and existing classes
        mock_links = []
        # Add existing classes (should be filtered out)
        for i in range(2):
            link = Mock()
            link.get_attribute.return_value = f"https://example.com/class?classId=existing{i+1}"
            mock_links.append(link)
        
        # Add new classes
        for i in range(5):  # Exactly what we need
            link = Mock()
            link.get_attribute.return_value = f"https://example.com/class?classId=new{i}"
            mock_links.append(link)
        
        driver.find_elements.return_value = mock_links
        
        with patch('time.sleep'):
            scrolls_performed = strategy._scroll_dynamically_until_limit(driver, config, 1.0)
        
        # Should stop after first scroll since we found enough new classes (5)
        assert scrolls_performed == 1
        assert driver.execute_script.call_count == 1
    
    def test_scroll_dynamically_until_limit_handles_invalid_links(self):
        """Test that dynamic scrolling handles invalid links gracefully."""
        strategy = MockScraperStrategy()
        driver = Mock()
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=3,
            page_scrolls=10,
            existing_class_ids=set(),
            episode_numbering_data={},
            subscriptions_existing_classes=0,
            dynamic_scrolling=True,
            max_scrolls=20
        )
        
        # Mock links with mix of valid and invalid
        mock_links = []
        
        # Valid links
        for i in range(3):
            link = Mock()
            link.get_attribute.return_value = f"https://example.com/class?classId=class{i}"
            mock_links.append(link)
        
        # Invalid links (no href or invalid href)
        invalid_link1 = Mock()
        invalid_link1.get_attribute.return_value = None
        mock_links.append(invalid_link1)
        
        invalid_link2 = Mock()
        invalid_link2.get_attribute.return_value = "https://example.com/class?noClassId=123"
        mock_links.append(invalid_link2)
        
        driver.find_elements.return_value = mock_links
        
        with patch('time.sleep'):
            scrolls_performed = strategy._scroll_dynamically_until_limit(driver, config, 1.0)
        
        # Should stop after first scroll since we found enough valid classes (3)
        assert scrolls_performed == 1
        assert driver.execute_script.call_count == 1
    
    def test_scroll_dynamically_until_limit_handles_exceptions(self):
        """Test that dynamic scrolling handles exceptions gracefully."""
        strategy = MockScraperStrategy()
        driver = Mock()
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=3,
            page_scrolls=10,
            existing_class_ids=set(),
            episode_numbering_data={},
            subscriptions_existing_classes=0,
            dynamic_scrolling=True,
            max_scrolls=20
        )
        
        # Mock links that raise exceptions
        mock_links = []
        for i in range(5):
            link = Mock()
            if i < 3:
                # Valid links
                link.get_attribute.return_value = f"https://example.com/class?classId=class{i}"
            else:
                # Links that raise exceptions
                link.get_attribute.side_effect = Exception("Test exception")
            mock_links.append(link)
        
        driver.find_elements.return_value = mock_links
        
        with patch('time.sleep'):
            scrolls_performed = strategy._scroll_dynamically_until_limit(driver, config, 1.0)
        
        # Should stop after first scroll since we found enough valid classes (3)
        assert scrolls_performed == 1
        assert driver.execute_script.call_count == 1


class TestPelotonScraperStrategyDynamicScrolling:
    """Test Peloton scraper strategy with dynamic scrolling."""
    
    def test_peloton_scraper_uses_dynamic_scrolling_when_enabled(self):
        """Test that Peloton scraper uses dynamic scrolling when enabled."""
        from src.webscraper.peloton.scraper_strategy import PelotonScraperStrategy
        
        strategy = PelotonScraperStrategy()
        driver = Mock()
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=5,
            page_scrolls=10,
            existing_class_ids=set(),
            episode_numbering_data={},
            subscriptions_existing_classes=0,
            dynamic_scrolling=True,
            max_scrolls=20
        )
        
        # Mock the page load and dynamic scrolling
        with patch.object(strategy, '_wait_for_page_load'), \
             patch.object(strategy, '_scroll_dynamically_until_limit', return_value=5) as mock_dynamic_scroll, \
             patch.object(strategy, '_scroll_to_load_content') as mock_static_scroll:
            
            # Mock driver.find_elements to return empty list to avoid processing
            driver.find_elements.return_value = []
            
            result = strategy.scrape_activity(driver, config)
        
        # Should use dynamic scrolling, not static scrolling
        mock_dynamic_scroll.assert_called_once_with(driver, config, config.scroll_pause_time)
        mock_static_scroll.assert_not_called()
        
        assert result.status == ScrapingStatus.COMPLETED
    
    def test_peloton_scraper_uses_static_scrolling_when_dynamic_disabled(self):
        """Test that Peloton scraper uses static scrolling when dynamic scrolling is disabled."""
        from src.webscraper.peloton.scraper_strategy import PelotonScraperStrategy
        
        strategy = PelotonScraperStrategy()
        driver = Mock()
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=5,
            page_scrolls=10,
            existing_class_ids=set(),
            episode_numbering_data={},
            subscriptions_existing_classes=0,
            dynamic_scrolling=False,  # Disabled
            max_scrolls=20
        )
        
        # Mock the page load and static scrolling
        with patch.object(strategy, '_wait_for_page_load'), \
             patch.object(strategy, '_scroll_dynamically_until_limit') as mock_dynamic_scroll, \
             patch.object(strategy, '_scroll_to_load_content') as mock_static_scroll:
            
            # Mock driver.find_elements to return empty list to avoid processing
            driver.find_elements.return_value = []
            
            result = strategy.scrape_activity(driver, config)
        
        # Should use static scrolling, not dynamic scrolling
        mock_static_scroll.assert_called_once_with(driver, config.page_scrolls, config.scroll_pause_time)
        mock_dynamic_scroll.assert_not_called()
        
        assert result.status == ScrapingStatus.COMPLETED


class TestScrapingConfigDynamicScrolling:
    """Test ScrapingConfig with dynamic scrolling options."""
    
    def test_scraping_config_defaults(self):
        """Test that ScrapingConfig has correct defaults for dynamic scrolling."""
        config = ScrapingConfig(
            activity="cycling",
            max_classes=5,
            page_scrolls=10,
            existing_class_ids=set(),
            episode_numbering_data={}
        )
        
        assert config.dynamic_scrolling is False
        assert config.max_scrolls == 50
    
    def test_scraping_config_custom_values(self):
        """Test that ScrapingConfig accepts custom dynamic scrolling values."""
        config = ScrapingConfig(
            activity="cycling",
            max_classes=5,
            page_scrolls=10,
            existing_class_ids=set(),
            episode_numbering_data={},
            dynamic_scrolling=True,
            max_scrolls=100
        )
        
        assert config.dynamic_scrolling is True
        assert config.max_scrolls == 100
