"""Test for the class limit bug - ensuring total classes don't exceed limit per activity."""

from unittest.mock import Mock, MagicMock, patch
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from src.webscraper.peloton.scraper_strategy import PelotonScraperStrategy
from src.webscraper.models import ScrapingConfig, ScrapingStatus


class TestClassLimitBug:
    """Test that the class limit properly counts total classes, not just new ones."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.scraper = PelotonScraperStrategy()
        
        # Mock logger
        self.scraper.logger = MagicMock()
        self.scraper.logger.info = MagicMock()  # type: ignore
        
        # Mock selenium methods
        self.scraper._wait_for_page_load = Mock()
        self.scraper._scroll_to_load_content = Mock()
    
    def create_mock_link_element(self, class_id: str, title: str, instructor: str, activity: str) -> Mock:
        """Create a mock link element for testing."""
        from selenium.webdriver.common.by import By
        
        link = Mock(spec=WebElement)
        link.get_attribute.return_value = f"https://members.onepeloton.com/classes?classId={class_id}"
        
        # Mock title element
        title_elem = Mock()
        title_elem.text = title
        
        # Mock subtitle element
        subtitle_elem = Mock()
        subtitle_elem.text = f"{instructor} · {activity}"
        
        # Set up find_element to return the appropriate element based on selector
        def find_element_side_effect(by, selector, **kwargs):
            if by == By.CSS_SELECTOR and selector == '[data-test-id="videoCellTitle"]':
                return title_elem
            elif by == By.CSS_SELECTOR and selector == '[data-test-id="videoCellSubtitle"]':
                return subtitle_elem
            else:
                return Mock()
        
        link.find_element.side_effect = find_element_side_effect
        
        return link
    
    def test_class_limit_should_count_total_not_new_classes(self):
        """
        Test that class limit properly considers:
        1. Classes already on disk
        2. Classes already in subscriptions (in-flight)
        3. New classes being added
        
        Total should not exceed the limit per activity.
        """
        # Setup: We have a limit of 5 classes per activity
        # - 2 classes already on disk (not counted in limit)
        # - 2 classes already in subscriptions (counted in limit)
        # - Should add 3 new classes (5 limit - 2 in subscriptions = 3 new)
        
        existing_class_ids = {"existing1", "existing2"}  # 2 classes on disk
        
        config = ScrapingConfig(
            activity="cycling",
            max_classes=5,  # Total limit per activity in subscriptions.yaml
            page_scrolls=1,
            existing_class_ids=existing_class_ids,
            episode_numbering_data={20: 2, 30: 2},  # Episode numbering from merged data (disk + subscriptions)
            subscriptions_existing_classes=2,  # Only 2 classes in subscriptions (not counting disk)
            headless=True,
            container_mode=False,
            scroll_pause_time=1.0,
            login_wait_time=5.0,
            page_load_wait_time=5.0
        )
        
        # Create mock driver
        driver = Mock()
        driver.get = Mock()
        driver.find_elements.return_value = [
            # 7 potential classes on the page
            self.create_mock_link_element("existing1", "20 min Ride", "Instructor1", "Cycling"),  # Already exists - skip
            self.create_mock_link_element("existing2", "20 min Ride", "Instructor2", "Cycling"),  # Already exists - skip
            self.create_mock_link_element("new1", "20 min Ride", "Instructor3", "Cycling"),      # Should be added
            self.create_mock_link_element("new2", "20 min Ride", "Instructor4", "Cycling"),      # Should be added
            self.create_mock_link_element("new3", "20 min Ride", "Instructor5", "Cycling"),      # Should be added
            self.create_mock_link_element("new4", "20 min Ride", "Instructor6", "Cycling"),      # Should be added
            self.create_mock_link_element("new5", "20 min Ride", "Instructor7", "Cycling"),      # Should be skipped (would exceed limit)
        ]
        
        # The current implementation has the bug - it only counts new classes, not total
        # This test will fail until we fix the bug
        result = self.scraper.scrape_activity(driver, config)
        
        # Verify the result - FIXED: it now properly considers subscriptions limit only
        assert result.status == ScrapingStatus.COMPLETED
        # With the fixed implementation, it should add 3 classes (5 limit - 2 in subscriptions = 3 new)
        assert len(result.classes) == 3, f"Expected 3 new classes with fixed implementation, got {len(result.classes)}"
        assert result.classes[0].class_id == "new1"
        assert result.classes[1].class_id == "new2"
        assert result.classes[2].class_id == "new3"
        
        # Verify that we stopped at the right point due to subscriptions limit
        # Fixed behavior: stops when subscriptions would exceed limit (2 in subscriptions + 3 new = 5, which is at limit)
        self.scraper.logger.info.assert_any_call("Reached max classes limit (5) - total would be 6 (existing in subscriptions: 2, new: 4)")  # type: ignore
    
    def test_class_limit_with_no_existing_classes(self):
        """Test class limit when no classes exist yet."""
        config = ScrapingConfig(
            activity="cycling",
            max_classes=3,  # Total limit per activity
            page_scrolls=1,
            existing_class_ids=set(),  # No existing classes
            episode_numbering_data={},
            subscriptions_existing_classes=0,  # No existing classes
            headless=True,
            container_mode=False,
            scroll_pause_time=1.0,
            login_wait_time=5.0,
            page_load_wait_time=5.0
        )
        
        driver = Mock()
        driver.get = Mock()
        driver.find_elements.return_value = [
            # 5 potential classes on the page
            self.create_mock_link_element("new1", "20 min Ride", "Instructor1", "Cycling"),
            self.create_mock_link_element("new2", "20 min Ride", "Instructor2", "Cycling"),
            self.create_mock_link_element("new3", "20 min Ride", "Instructor3", "Cycling"),
            self.create_mock_link_element("new4", "20 min Ride", "Instructor4", "Cycling"),
            self.create_mock_link_element("new5", "20 min Ride", "Instructor5", "Cycling"),
        ]
        
        # With no existing classes, should add exactly 3 classes (the limit)
        result = self.scraper.scrape_activity(driver, config)
        
        # Should add exactly 3 classes (the limit)
        assert result.status == ScrapingStatus.COMPLETED
        assert len(result.classes) == 3, f"Expected 3 new classes, got {len(result.classes)}"
        assert result.classes[0].class_id == "new1"
        assert result.classes[1].class_id == "new2"
        assert result.classes[2].class_id == "new3"
        
        self.scraper.logger.info.assert_any_call("Reached max classes limit (3) - total would be 4 (existing in subscriptions: 0, new: 4)")  # type: ignore
    
    def test_class_limit_with_many_existing_classes(self):
        """Test that no new classes are added when already at limit."""
        config = ScrapingConfig(
            activity="cycling",
            max_classes=2,  # Small limit
            page_scrolls=1,
            existing_class_ids={"existing1"},  # 1 class on disk (not counted)
            episode_numbering_data={20: 1},  # Episode numbering
            subscriptions_existing_classes=2,  # Already at the subscriptions limit
            headless=True,
            container_mode=False,
            scroll_pause_time=1.0,
            login_wait_time=5.0,
            page_load_wait_time=5.0
        )
        
        driver = Mock()
        driver.get = Mock()
        driver.find_elements.return_value = [
            self.create_mock_link_element("new1", "20 min Ride", "Instructor1", "Cycling"),
            self.create_mock_link_element("new2", "20 min Ride", "Instructor2", "Cycling"),
        ]
        
        # Should add 0 classes because we're already at limit (2 existing = 2 limit)
        result = self.scraper.scrape_activity(driver, config)
        
        # Should add 0 classes because we're already at limit
        assert result.status == ScrapingStatus.COMPLETED
        assert len(result.classes) == 0, f"Expected 0 new classes, got {len(result.classes)}"
        
        # Should log that we're at limit
        self.scraper.logger.info.assert_any_call("Reached max classes limit (2) - total would be 3 (existing in subscriptions: 2, new: 1)")  # type: ignore
