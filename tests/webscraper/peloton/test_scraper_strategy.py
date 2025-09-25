"""Tests for Peloton scraper strategy."""

import pytest
from unittest.mock import patch, MagicMock
from selenium.common.exceptions import NoSuchElementException

from src.webscraper.peloton.scraper_strategy import PelotonScraperStrategy
from src.webscraper.models import ScrapingConfig, ScrapingStatus, ScrapedClass


class TestPelotonScraperStrategy:
    """Test the PelotonScraperStrategy class."""

    def test_peloton_scraper_strategy_creation(self):
        """Test PelotonScraperStrategy creation."""
        strategy = PelotonScraperStrategy()
        assert hasattr(strategy, 'logger')

    def test_get_activity_url(self):
        """Test get_activity_url method."""
        strategy = PelotonScraperStrategy()
        
        url = strategy.get_activity_url("cycling")
        expected = "https://members.onepeloton.com/classes/cycling?class_languages=%5B%22en-US%22%5D&sort=original_air_time&desc=true"
        assert url == expected
        
        url = strategy.get_activity_url("YOGA")
        expected = "https://members.onepeloton.com/classes/yoga?class_languages=%5B%22en-US%22%5D&sort=original_air_time&desc=true"
        assert url == expected

    def test_extract_duration_from_title_standard_format(self):
        """Test extracting duration from standard title format."""
        strategy = PelotonScraperStrategy()
        
        assert strategy.extract_duration_from_title("30 min Power Ride") == 30
        assert strategy.extract_duration_from_title("45 min Yoga Flow") == 45
        assert strategy.extract_duration_from_title("  20 min   HIIT Cardio") == 20
        assert strategy.extract_duration_from_title("5 MIN Cool Down") == 5

    def test_extract_duration_from_title_fallback(self):
        """Test extracting duration with fallback pattern."""
        strategy = PelotonScraperStrategy()
        
        # When standard pattern fails, should find any number
        assert strategy.extract_duration_from_title("Power Ride 30") == 30
        assert strategy.extract_duration_from_title("Class with 45 minutes") == 45
        assert strategy.extract_duration_from_title("Quick 10 session") == 10

    def test_extract_duration_from_title_no_match(self):
        """Test extracting duration when no pattern matches."""
        strategy = PelotonScraperStrategy()
        
        # Should return 0 when no duration found
        assert strategy.extract_duration_from_title("Power Ride") == 0
        assert strategy.extract_duration_from_title("Yoga Flow Class") == 0
        assert strategy.extract_duration_from_title("") == 0

    def test_extract_class_id_success(self):
        """Test successful class ID extraction from URL."""
        strategy = PelotonScraperStrategy()
        
        url = "https://members.onepeloton.com/classes/cycling?classId=abc123def456"
        class_id = strategy._extract_class_id(url)
        assert class_id == "abc123def456"
        
        # Test with additional parameters
        url = "https://members.onepeloton.com/classes/yoga?classId=xyz789&other=param"
        class_id = strategy._extract_class_id(url)
        assert class_id == "xyz789"

    def test_extract_class_id_no_class_id(self):
        """Test class ID extraction when classId parameter is missing."""
        strategy = PelotonScraperStrategy()
        
        url = "https://members.onepeloton.com/classes/cycling?other=param"
        class_id = strategy._extract_class_id(url)
        assert class_id == ""

    def test_extract_class_id_invalid_url(self):
        """Test class ID extraction with invalid URL."""
        strategy = PelotonScraperStrategy()
        
        class_id = strategy._extract_class_id("not-a-valid-url")
        assert class_id == ""

    def test_extract_class_metadata_success(self):
        """Test successful metadata extraction."""
        strategy = PelotonScraperStrategy()
        
        # Mock elements
        mock_link = MagicMock()
        mock_title_element = MagicMock()
        mock_title_element.text = "30 min Power Ride"
        mock_subtitle_element = MagicMock()
        mock_subtitle_element.text = "Emma Lovewell · Cycling"
        
        def mock_find_element(by, value):
            if value == '[data-test-id="videoCellTitle"]':
                return mock_title_element
            elif value == '[data-test-id="videoCellSubtitle"]':
                return mock_subtitle_element
            return MagicMock()
        
        mock_link.find_element.side_effect = mock_find_element
        
        metadata = strategy.extract_class_metadata(mock_link)
        
        expected = {
            'title': '30 min Power Ride',
            'instructor': 'Emma Lovewell',
            'activity': 'Cycling'
        }
        assert metadata == expected

    def test_extract_class_metadata_title_not_found(self):
        """Test metadata extraction when title element is not found."""
        strategy = PelotonScraperStrategy()
        
        mock_link = MagicMock()
        mock_link.find_element.side_effect = NoSuchElementException("Title not found")
        
        metadata = strategy.extract_class_metadata(mock_link)
        assert metadata is None

    def test_extract_class_metadata_subtitle_not_found(self):
        """Test metadata extraction when subtitle element is not found."""
        strategy = PelotonScraperStrategy()
        
        mock_link = MagicMock()
        mock_title_element = MagicMock()
        mock_title_element.text = "30 min Power Ride"
        
        def mock_find_element(by, value):
            if value == '[data-test-id="videoCellTitle"]':
                return mock_title_element
            elif value == '[data-test-id="videoCellSubtitle"]':
                raise NoSuchElementException("Subtitle not found")
            return MagicMock()
        
        mock_link.find_element.side_effect = mock_find_element
        
        metadata = strategy.extract_class_metadata(mock_link)
        assert metadata is None

    def test_extract_class_metadata_unexpected_subtitle_format(self):
        """Test metadata extraction with unexpected subtitle format."""
        strategy = PelotonScraperStrategy()
        
        mock_link = MagicMock()
        mock_title_element = MagicMock()
        mock_title_element.text = "30 min Power Ride"
        mock_subtitle_element = MagicMock()
        mock_subtitle_element.text = "Just Instructor Name"  # No separator
        
        def mock_find_element(by, value):
            if value == '[data-test-id="videoCellTitle"]':
                return mock_title_element
            elif value == '[data-test-id="videoCellSubtitle"]':
                return mock_subtitle_element
            return MagicMock()
        
        mock_link.find_element.side_effect = mock_find_element
        
        metadata = strategy.extract_class_metadata(mock_link)
        
        expected = {
            'title': '30 min Power Ride',
            'instructor': 'Unknown',
            'activity': 'Unknown'
        }
        assert metadata == expected

    def test_extract_class_metadata_multiple_separators(self):
        """Test metadata extraction with multiple separators in subtitle."""
        strategy = PelotonScraperStrategy()
        
        mock_link = MagicMock()
        mock_title_element = MagicMock()
        mock_title_element.text = "30 min Power Ride"
        mock_subtitle_element = MagicMock()
        mock_subtitle_element.text = "Emma Lovewell · Cycling · Extra Info"
        
        def mock_find_element(by, value):
            if value == '[data-test-id="videoCellTitle"]':
                return mock_title_element
            elif value == '[data-test-id="videoCellSubtitle"]':
                return mock_subtitle_element
            return MagicMock()
        
        mock_link.find_element.side_effect = mock_find_element
        
        metadata = strategy.extract_class_metadata(mock_link)
        
        # Should take first two parts
        expected = {
            'title': '30 min Power Ride',
            'instructor': 'Emma Lovewell',
            'activity': 'Cycling'
        }
        assert metadata == expected

    @patch('src.webscraper.peloton.scraper_strategy.time.sleep')
    def test_scrape_activity_success(self, mock_sleep):
        """Test successful activity scraping."""
        strategy = PelotonScraperStrategy()
        
        # Mock driver and elements
        mock_driver = MagicMock()
        mock_links = []
        
        # Create mock links
        for i in range(3):
            mock_link = MagicMock()
            mock_link.get_attribute.return_value = f"https://example.com?classId=class-{i}"
            
            # Mock title element
            mock_title = MagicMock()
            mock_title.text = f"30 min Class {i}"
            
            # Mock subtitle element
            mock_subtitle = MagicMock()
            mock_subtitle.text = f"Instructor {i} · Cycling"
            
            def make_find_element(title_elem, subtitle_elem):
                def mock_find_element(by, value):
                    if value == '[data-test-id="videoCellTitle"]':
                        return title_elem
                    elif value == '[data-test-id="videoCellSubtitle"]':
                        return subtitle_elem
                    return MagicMock()
                return mock_find_element
            
            mock_link.find_element.side_effect = make_find_element(mock_title, mock_subtitle)
            mock_links.append(mock_link)
        
        mock_driver.find_elements.return_value = mock_links
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=10,
            page_scrolls=2,
            existing_class_ids=set(),
            episode_numbering_data={30: 0},
            page_load_wait_time=1.0,
            scroll_pause_time=0.5
        )
        
        result = strategy.scrape_activity(mock_driver, config)
        
        # Verify navigation and scrolling
        expected_url = "https://members.onepeloton.com/classes/cycling?class_languages=%5B%22en-US%22%5D&sort=original_air_time&desc=true"
        mock_driver.get.assert_called_once_with(expected_url)
        assert mock_driver.execute_script.call_count == 2  # 2 scrolls
        
        # Verify result
        assert result.activity == "cycling"
        assert result.status == ScrapingStatus.COMPLETED
        assert len(result.classes) == 3
        assert result.total_found == 3
        assert result.total_skipped == 0
        assert result.total_errors == 0
        
        # Verify scraped classes
        for i, scraped_class in enumerate(result.classes):
            assert scraped_class.class_id == f"class-{i}"
            assert scraped_class.title == f"30 min Class {i}"
            assert scraped_class.instructor == f"Instructor {i}"
            assert scraped_class.activity == "cycling"  # Should use config.activity, not metadata
            assert scraped_class.duration_minutes == 30
            assert scraped_class.season_number == 30
            assert scraped_class.episode_number == i + 1
            assert scraped_class.status == ScrapingStatus.COMPLETED

    @patch('src.webscraper.peloton.scraper_strategy.time.sleep')
    def test_scrape_activity_with_existing_classes(self, mock_sleep):
        """Test scraping activity with existing classes to skip."""
        strategy = PelotonScraperStrategy()
        
        mock_driver = MagicMock()
        mock_links = []
        
        # Create 3 mock links, but class-1 already exists
        for i in range(3):
            mock_link = MagicMock()
            mock_link.get_attribute.return_value = f"https://example.com?classId=class-{i}"
            
            # Mock title element
            mock_title = MagicMock()
            mock_title.text = f"30 min Class {i}"
            
            # Mock subtitle element
            mock_subtitle = MagicMock()
            mock_subtitle.text = f"Instructor {i} · Cycling"
            
            def make_find_element(title_elem, subtitle_elem):
                def mock_find_element(by, value):
                    if value == '[data-test-id="videoCellTitle"]':
                        return title_elem
                    elif value == '[data-test-id="videoCellSubtitle"]':
                        return subtitle_elem
                    return MagicMock()
                return mock_find_element
            
            mock_link.find_element.side_effect = make_find_element(mock_title, mock_subtitle)
            mock_links.append(mock_link)
        
        mock_driver.find_elements.return_value = mock_links
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=10,
            page_scrolls=1,
            existing_class_ids={"class-1"},  # class-1 already exists
            episode_numbering_data={30: 0},
            page_load_wait_time=0.1,
            scroll_pause_time=0.1
        )
        
        result = strategy.scrape_activity(mock_driver, config)
        
        assert result.total_found == 3
        assert result.total_skipped == 1  # class-1 was skipped
        assert len(result.classes) == 2  # Only class-0 and class-2 processed

    @patch('src.webscraper.peloton.scraper_strategy.time.sleep')
    def test_scrape_activity_max_classes_limit(self, mock_sleep):
        """Test scraping activity with max classes limit."""
        strategy = PelotonScraperStrategy()
        
        mock_driver = MagicMock()
        mock_links = []
        
        # Create 5 mock links
        for i in range(5):
            mock_link = MagicMock()
            mock_link.get_attribute.return_value = f"https://example.com?classId=class-{i}"
            
            mock_title = MagicMock()
            mock_title.text = f"30 min Class {i}"
            mock_subtitle = MagicMock()
            mock_subtitle.text = f"Instructor {i} · Cycling"
            
            def make_find_element(title_elem, subtitle_elem):
                def mock_find_element(by, value):
                    if value == '[data-test-id="videoCellTitle"]':
                        return title_elem
                    elif value == '[data-test-id="videoCellSubtitle"]':
                        return subtitle_elem
                    return MagicMock()
                return mock_find_element
            
            mock_link.find_element.side_effect = make_find_element(mock_title, mock_subtitle)
            mock_links.append(mock_link)
        
        mock_driver.find_elements.return_value = mock_links
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=3,  # Limit to 3 classes
            page_scrolls=1,
            existing_class_ids=set(),
            episode_numbering_data={30: 0},
            page_load_wait_time=0.1,
            scroll_pause_time=0.1
        )
        
        result = strategy.scrape_activity(mock_driver, config)
        
        assert result.total_found == 5
        assert len(result.classes) == 3  # Limited to max_classes

    @patch('src.webscraper.peloton.scraper_strategy.time.sleep')
    def test_scrape_activity_fatal_error(self, mock_sleep):
        """Test scraping activity with fatal error."""
        strategy = PelotonScraperStrategy()
        
        mock_driver = MagicMock()
        mock_driver.get.side_effect = Exception("Network error")
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=10,
            page_scrolls=1,
            existing_class_ids=set(),
            episode_numbering_data={}
        )
        
        result = strategy.scrape_activity(mock_driver, config)
        
        assert result.activity == "cycling"
        assert result.status == ScrapingStatus.FAILED
        assert result.error_message == "Network error"
        assert len(result.classes) == 0

    @patch('src.webscraper.peloton.scraper_strategy.time.sleep')
    def test_scrape_activity_metadata_extraction_errors(self, mock_sleep):
        """Test scraping activity with metadata extraction errors."""
        strategy = PelotonScraperStrategy()
        
        mock_driver = MagicMock()
        mock_links = []
        
        # Create links with various error conditions
        for i in range(3):
            mock_link = MagicMock()
            if i == 0:
                # Valid link
                mock_link.get_attribute.return_value = "https://example.com?classId=class-0"
                mock_title = MagicMock()
                mock_title.text = "30 min Class"
                mock_subtitle = MagicMock()
                mock_subtitle.text = "Instructor · Cycling"
                
                def mock_find_element(by, value):
                    if value == '[data-test-id="videoCellTitle"]':
                        return mock_title
                    elif value == '[data-test-id="videoCellSubtitle"]':
                        return mock_subtitle
                    return MagicMock()
                
                mock_link.find_element.side_effect = mock_find_element
            elif i == 1:
                # No class ID
                mock_link.get_attribute.return_value = "https://example.com?other=param"
            else:
                # Metadata extraction fails
                mock_link.get_attribute.return_value = "https://example.com?classId=class-2"
                mock_link.find_element.side_effect = Exception("Element error")
            
            mock_links.append(mock_link)
        
        mock_driver.find_elements.return_value = mock_links
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=10,
            page_scrolls=1,
            existing_class_ids=set(),
            episode_numbering_data={30: 0},
            page_load_wait_time=0.1,
            scroll_pause_time=0.1
        )
        
        result = strategy.scrape_activity(mock_driver, config)
        
        assert result.total_found == 3
        assert result.total_errors == 2  # Links 1 and 2 had errors
        assert len(result.classes) == 1  # Only link 0 succeeded
