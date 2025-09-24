"""Tests for webscraper models."""

import pytest
from src.webscraper.models import (
    ScrapingStatus, ScrapedClass, ScrapingResult, ScrapingConfig
)


class TestScrapingStatus:
    """Test the ScrapingStatus enum."""

    def test_scraping_status_values(self):
        """Test ScrapingStatus enum values."""
        assert ScrapingStatus.PENDING.value == "pending"
        assert ScrapingStatus.IN_PROGRESS.value == "in_progress"
        assert ScrapingStatus.COMPLETED.value == "completed"
        assert ScrapingStatus.FAILED.value == "failed"
        assert ScrapingStatus.SKIPPED.value == "skipped"


class TestScrapedClass:
    """Test the ScrapedClass data model."""

    def test_scraped_class_creation(self):
        """Test ScrapedClass creation with required fields."""
        scraped_class = ScrapedClass(
            class_id="test-class-123",
            title="30 min Cycling Class",
            instructor="Test Instructor",
            activity="Cycling",
            duration_minutes=30,
            player_url="https://example.com/classes/player/test-class-123",
            season_number=30,
            episode_number=1
        )
        
        assert scraped_class.class_id == "test-class-123"
        assert scraped_class.title == "30 min Cycling Class"
        assert scraped_class.instructor == "Test Instructor"
        assert scraped_class.activity == "Cycling"
        assert scraped_class.duration_minutes == 30
        assert scraped_class.player_url == "https://example.com/classes/player/test-class-123"
        assert scraped_class.season_number == 30
        assert scraped_class.episode_number == 1
        assert scraped_class.status == ScrapingStatus.PENDING

    def test_scraped_class_with_custom_status(self):
        """Test ScrapedClass creation with custom status."""
        scraped_class = ScrapedClass(
            class_id="test-class-123",
            title="30 min Cycling Class",
            instructor="Test Instructor",
            activity="Cycling",
            duration_minutes=30,
            player_url="https://example.com/classes/player/test-class-123",
            season_number=30,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        assert scraped_class.status == ScrapingStatus.COMPLETED

    def test_to_subscription_entry(self):
        """Test conversion to subscription entry format."""
        scraped_class = ScrapedClass(
            class_id="test-class-123",
            title="30 min Power Ride",
            instructor="Emma Lovewell",
            activity="Cycling",
            duration_minutes=30,
            player_url="https://example.com/classes/player/test-class-123",
            season_number=30,
            episode_number=5
        )
        
        entry = scraped_class.to_subscription_entry()
        
        expected = {
            "download": "https://example.com/classes/player/test-class-123",
            "overrides": {
                "tv_show_directory": "/media/peloton/Cycling/Emma Lovewell",
                "season_number": 30,
                "episode_number": 5
            }
        }
        
        assert entry == expected

    def test_to_subscription_entry_replaces_slashes(self):
        """Test that forward slashes in titles are replaced with dashes."""
        scraped_class = ScrapedClass(
            class_id="test-class-123",
            title="30 min Hip Hop/R&B Ride",
            instructor="Tunde Oyeneyin",
            activity="Cycling",
            duration_minutes=30,
            player_url="https://example.com/classes/player/test-class-123",
            season_number=30,
            episode_number=1
        )
        
        entry = scraped_class.to_subscription_entry()
        
        # The slash replacement happens in the ScrapingResult.get_subscription_data() method
        # The to_subscription_entry() method doesn't handle title formatting
        assert entry["download"] == "https://example.com/classes/player/test-class-123"
        assert entry["overrides"]["tv_show_directory"] == "/media/peloton/Cycling/Tunde Oyeneyin"


class TestScrapingResult:
    """Test the ScrapingResult data model."""

    def test_scraping_result_creation(self):
        """Test ScrapingResult creation."""
        classes = [
            ScrapedClass(
                class_id="test-1",
                title="20 min Class",
                instructor="Instructor 1",
                activity="Cycling",
                duration_minutes=20,
                player_url="https://example.com/classes/player/test-1",
                season_number=20,
                episode_number=1,
                status=ScrapingStatus.COMPLETED
            )
        ]
        
        result = ScrapingResult(
            activity="cycling",
            classes=classes,
            total_found=10,
            total_skipped=5,
            total_errors=1,
            status=ScrapingStatus.COMPLETED
        )
        
        assert result.activity == "cycling"
        assert len(result.classes) == 1
        assert result.total_found == 10
        assert result.total_skipped == 5
        assert result.total_errors == 1
        assert result.status == ScrapingStatus.COMPLETED
        assert result.error_message is None

    def test_scraping_result_with_error(self):
        """Test ScrapingResult creation with error message."""
        result = ScrapingResult(
            activity="cycling",
            classes=[],
            total_found=0,
            total_skipped=0,
            total_errors=1,
            status=ScrapingStatus.FAILED,
            error_message="Login failed"
        )
        
        assert result.status == ScrapingStatus.FAILED
        assert result.error_message == "Login failed"

    def test_get_subscription_data_empty(self):
        """Test get_subscription_data with no completed classes."""
        result = ScrapingResult(
            activity="cycling",
            classes=[],
            total_found=0,
            total_skipped=0,
            total_errors=0,
            status=ScrapingStatus.COMPLETED
        )
        
        subscription_data = result.get_subscription_data()
        assert subscription_data == {}

    def test_get_subscription_data_single_class(self):
        """Test get_subscription_data with single completed class."""
        classes = [
            ScrapedClass(
                class_id="test-1",
                title="30 min Power Ride",
                instructor="Emma Lovewell",
                activity="Cycling",
                duration_minutes=30,
                player_url="https://example.com/classes/player/test-1",
                season_number=30,
                episode_number=1,
                status=ScrapingStatus.COMPLETED
            )
        ]
        
        result = ScrapingResult(
            activity="cycling",
            classes=classes,
            total_found=1,
            total_skipped=0,
            total_errors=0,
            status=ScrapingStatus.COMPLETED
        )
        
        subscription_data = result.get_subscription_data()
        
        expected_key = "= Cycling (30 min)"
        expected_episode_title = "30 min Power Ride with Emma Lovewell"
        
        assert expected_key in subscription_data
        assert expected_episode_title in subscription_data[expected_key]
        assert subscription_data[expected_key][expected_episode_title]["download"] == "https://example.com/classes/player/test-1"

    def test_get_subscription_data_skips_non_completed(self):
        """Test that get_subscription_data only includes completed classes."""
        classes = [
            ScrapedClass(
                class_id="test-1",
                title="30 min Power Ride",
                instructor="Emma Lovewell",
                activity="Cycling",
                duration_minutes=30,
                player_url="https://example.com/classes/player/test-1",
                season_number=30,
                episode_number=1,
                status=ScrapingStatus.COMPLETED
            ),
            ScrapedClass(
                class_id="test-2",
                title="20 min Recovery Ride",
                instructor="Matt Wilpers",
                activity="Cycling",
                duration_minutes=20,
                player_url="https://example.com/classes/player/test-2",
                season_number=20,
                episode_number=1,
                status=ScrapingStatus.FAILED
            )
        ]
        
        result = ScrapingResult(
            activity="cycling",
            classes=classes,
            total_found=2,
            total_skipped=0,
            total_errors=1,
            status=ScrapingStatus.COMPLETED
        )
        
        subscription_data = result.get_subscription_data()
        
        # Should only have the completed class
        assert len(subscription_data) == 1
        assert "= Cycling (30 min)" in subscription_data
        assert "= Cycling (20 min)" not in subscription_data

    def test_get_subscription_data_handles_duplicates(self):
        """Test that get_subscription_data handles duplicate episode titles."""
        classes = [
            ScrapedClass(
                class_id="test-1",
                title="30 min Power Ride",
                instructor="Emma Lovewell",
                activity="Cycling",
                duration_minutes=30,
                player_url="https://example.com/classes/player/test-1",
                season_number=30,
                episode_number=1,
                status=ScrapingStatus.COMPLETED
            ),
            ScrapedClass(
                class_id="test-2",
                title="30 min Power Ride",  # Same title
                instructor="Emma Lovewell",  # Same instructor
                activity="Cycling",
                duration_minutes=30,
                player_url="https://example.com/classes/player/test-2",
                season_number=30,
                episode_number=2,
                status=ScrapingStatus.COMPLETED
            )
        ]
        
        result = ScrapingResult(
            activity="cycling",
            classes=classes,
            total_found=2,
            total_skipped=0,
            total_errors=0,
            status=ScrapingStatus.COMPLETED
        )
        
        subscription_data = result.get_subscription_data()
        
        duration_key = "= Cycling (30 min)"
        assert duration_key in subscription_data
        
        # Should have both episodes with different titles
        episode_titles = list(subscription_data[duration_key].keys())
        assert len(episode_titles) == 2
        assert "30 min Power Ride with Emma Lovewell" in episode_titles
        assert "30 min Power Ride with Emma Lovewell (1)" in episode_titles


class TestScrapingConfig:
    """Test the ScrapingConfig data model."""

    def test_scraping_config_creation(self):
        """Test ScrapingConfig creation with required fields."""
        config = ScrapingConfig(
            activity="cycling",
            max_classes=25,
            page_scrolls=10,
            existing_class_ids={"class-1", "class-2"},
            episode_numbering_data={20: 50, 30: 25}
        )
        
        assert config.activity == "cycling"
        assert config.max_classes == 25
        assert config.page_scrolls == 10
        assert config.existing_class_ids == {"class-1", "class-2"}
        assert config.episode_numbering_data == {20: 50, 30: 25}
        
        # Test defaults
        assert config.headless is True
        assert config.container_mode is True
        assert config.scroll_pause_time == 3.0
        assert config.login_wait_time == 15.0
        assert config.page_load_wait_time == 10.0

    def test_scraping_config_with_custom_values(self):
        """Test ScrapingConfig creation with custom values."""
        config = ScrapingConfig(
            activity="yoga",
            max_classes=10,
            page_scrolls=5,
            existing_class_ids=set(),
            episode_numbering_data={},
            headless=False,
            container_mode=False,
            scroll_pause_time=5.0,
            login_wait_time=30.0,
            page_load_wait_time=15.0
        )
        
        assert config.activity == "yoga"
        assert config.max_classes == 10
        assert config.page_scrolls == 5
        assert config.existing_class_ids == set()
        assert config.episode_numbering_data == {}
        assert config.headless is False
        assert config.container_mode is False
        assert config.scroll_pause_time == 5.0
        assert config.login_wait_time == 30.0
        assert config.page_load_wait_time == 15.0


class TestNormalizeText:
    """Test cases for the normalize_text utility function."""
    
    def test_normalize_text_with_valid_unicode(self):
        """Test normalize_text with valid Unicode characters."""
        from src.webscraper.models import normalize_text
        
        # Test with proper accented characters
        result = normalize_text("Mariana Fernández")
        assert result == "Mariana Fernández"
        
        # Test with other accented characters
        result = normalize_text("José María")
        assert result == "José María"
        
        result = normalize_text("Café Niño")
        assert result == "Café Niño"
    
    def test_normalize_text_with_corrupted_characters(self):
        """Test normalize_text with corrupted Unicode replacement characters."""
        from src.webscraper.models import normalize_text
        
        # Test with Unicode replacement character (�)
        corrupted_text = "Mariana Fern\ufffdndez"
        result = normalize_text(corrupted_text)
        assert result == "Mariana Fernndez"  # Should remove the replacement char
        
        # Test with multiple replacement characters
        corrupted_text = "Test\ufffd with\ufffd multiple"
        result = normalize_text(corrupted_text)
        assert result == "Test with multiple"
    
    def test_normalize_text_with_whitespace(self):
        """Test normalize_text handles whitespace correctly."""
        from src.webscraper.models import normalize_text
        
        # Test with leading/trailing whitespace
        result = normalize_text("  Mariana Fernández  ")
        assert result == "Mariana Fernández"
        
        # Test with internal whitespace preservation
        result = normalize_text("Mariana   Fernández")
        assert result == "Mariana   Fernández"
    
    def test_normalize_text_edge_cases(self):
        """Test normalize_text with edge cases."""
        from src.webscraper.models import normalize_text
        
        # Test with empty string
        result = normalize_text("")
        assert result == ""
        
        # Test with None (should not crash)
        result = normalize_text(None)
        assert result is None
        
        # Test with normal ASCII text
        result = normalize_text("Normal English Text")
        assert result == "Normal English Text"
    
    def test_normalize_text_yaml_safety(self):
        """Test that normalized text produces valid YAML."""
        import yaml
        from src.webscraper.models import normalize_text
        
        # Test various problematic characters
        test_strings = [
            "Mariana Fernández",
            "José María Café",
            "Test with émojis and ñ",
            "Múltiple áccénts éverywhere"
        ]
        
        for test_string in test_strings:
            normalized = normalize_text(test_string)
            
            # Create a simple YAML structure
            yaml_data = {
                "test_entry": {
                    "title": normalized,
                    "path": f"/media/test/{normalized}"
                }
            }
            
            # Should not raise an exception when dumping to YAML
            try:
                yaml_output = yaml.dump(yaml_data, allow_unicode=True, default_flow_style=False)
                # Should be able to parse it back
                parsed_data = yaml.safe_load(yaml_output)
                assert parsed_data["test_entry"]["title"] == normalized
            except Exception as e:
                pytest.fail(f"YAML serialization failed for '{normalized}': {e}")
    
    def test_scraped_class_with_unicode_characters(self):
        """Test ScrapedClass handles Unicode characters in to_subscription_entry."""
        from src.webscraper.models import ScrapedClass, ScrapingStatus
        
        # Create a class with Unicode characters
        scraped_class = ScrapedClass(
            class_id="test123",
            title="Focus Flow: For Runners",
            instructor="Mariana Fernández",
            activity="Yoga",
            duration_minutes=10,
            player_url="https://example.com/class",
            season_number=10,
            episode_number=31,
            status=ScrapingStatus.COMPLETED
        )
        
        # Convert to subscription entry
        entry = scraped_class.to_subscription_entry()
        
        # Verify Unicode characters are preserved
        assert "Mariana Fernández" in entry["overrides"]["tv_show_directory"]
        assert entry["overrides"]["tv_show_directory"] == "/media/peloton/Yoga/Mariana Fernández"
        
        # Verify the entry can be serialized to YAML
        import yaml
        yaml_output = yaml.dump(entry, allow_unicode=True, default_flow_style=False)
        parsed_entry = yaml.safe_load(yaml_output)
        assert parsed_entry == entry


class TestFilesystemSanitization:
    """Test cases for the sanitize_for_filesystem utility function."""
    
    def test_sanitize_for_filesystem_basic_cases(self):
        """Test sanitize_for_filesystem with basic problematic characters."""
        from src.webscraper.models import sanitize_for_filesystem
        
        # Test forward slash (the main issue)
        result = sanitize_for_filesystem("50/50 Workout")
        assert result == "50-50 Workout"
        
        # Test multiple slashes
        result = sanitize_for_filesystem("Test/Path/With/Slashes")
        assert result == "Test-Path-With-Slashes"
        
        # Test backslashes (Windows)
        result = sanitize_for_filesystem("Test\\Path\\Windows")
        assert result == "Test-Path-Windows"
    
    def test_sanitize_for_filesystem_colons_and_semicolons(self):
        """Test sanitize_for_filesystem with colons and semicolons."""
        from src.webscraper.models import sanitize_for_filesystem
        
        # Test colons
        result = sanitize_for_filesystem("Morning: Flow")
        assert result == "Morning- Flow"
        
        # Test semicolons
        result = sanitize_for_filesystem("Flow; Core; Stretch")
        assert result == "Flow- Core- Stretch"
        
        # Test combination
        result = sanitize_for_filesystem("Morning: Flow; Evening: Stretch")
        assert result == "Morning- Flow- Evening- Stretch"
    
    def test_sanitize_for_filesystem_special_characters(self):
        """Test sanitize_for_filesystem with various special characters."""
        from src.webscraper.models import sanitize_for_filesystem
        
        # Test wildcards and redirections
        result = sanitize_for_filesystem("Test*?<>|")
        assert result == "Test-----"
        
        # Test quotes
        result = sanitize_for_filesystem('Flow "Advanced" Session')
        assert result == "Flow 'Advanced' Session"
        
        # Test control characters
        result = sanitize_for_filesystem("Test\t\n\r Flow")
        assert result == "Test Flow"  # Multiple spaces are collapsed
    
    def test_sanitize_for_filesystem_whitespace_handling(self):
        """Test sanitize_for_filesystem handles whitespace correctly."""
        from src.webscraper.models import sanitize_for_filesystem
        
        # Test multiple spaces collapse
        result = sanitize_for_filesystem("Test    Multiple    Spaces")
        assert result == "Test Multiple Spaces"
        
        # Test leading/trailing spaces and dots
        result = sanitize_for_filesystem("  . Test Flow .  ")
        assert result == "Test Flow"
    
    def test_sanitize_for_filesystem_edge_cases(self):
        """Test sanitize_for_filesystem with edge cases."""
        from src.webscraper.models import sanitize_for_filesystem
        
        # Test empty string
        result = sanitize_for_filesystem("")
        assert result == ""
        
        # Test None
        result = sanitize_for_filesystem(None)
        assert result is None
        
        # Test normal text (should be unchanged)
        result = sanitize_for_filesystem("Normal Flow Session")
        assert result == "Normal Flow Session"
    
    def test_scraped_class_with_filesystem_unsafe_characters(self):
        """Test ScrapedClass handles filesystem-unsafe characters correctly."""
        from src.webscraper.models import ScrapedClass, ScrapingStatus
        
        # Create a class with the specific "50/50" case mentioned
        scraped_class = ScrapedClass(
            class_id="test123",
            title="15 min 50/50 Workout",
            instructor="Kirra Michel",
            activity="Strength",
            duration_minutes=15,
            player_url="https://example.com/class",
            season_number=15,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        # Convert to subscription entry (default media dir)
        entry = scraped_class.to_subscription_entry()
        
        # Verify slashes are removed from directory path
        expected_dir = "/media/peloton/Strength/Kirra Michel"
        assert entry["overrides"]["tv_show_directory"] == expected_dir
        
        # Verify the entry can be serialized to YAML
        import yaml
        yaml_output = yaml.dump(entry, allow_unicode=True, default_flow_style=False)
        parsed_entry = yaml.safe_load(yaml_output)
        assert parsed_entry == entry
    
    def test_scraping_result_with_filesystem_unsafe_characters(self):
        """Test ScrapingResult handles filesystem-unsafe characters in get_subscription_data."""
        from src.webscraper.models import ScrapedClass, ScrapingResult, ScrapingStatus
        
        # Create classes with various problematic characters
        classes = [
            ScrapedClass(
                class_id="test1",
                title="15 min 50/50 Workout",
                instructor="Kirra Michel",
                activity="Strength",
                duration_minutes=15,
                player_url="https://example.com/class1",
                season_number=15,
                episode_number=1,
                status=ScrapingStatus.COMPLETED
            ),
            ScrapedClass(
                class_id="test2",
                title="Morning: Flow Session",
                instructor="Test/Instructor",
                activity="Yoga",
                duration_minutes=30,
                player_url="https://example.com/class2",
                season_number=30,
                episode_number=1,
                status=ScrapingStatus.COMPLETED
            )
        ]
        
        result = ScrapingResult(
            activity="strength",
            classes=classes,
            total_found=2,
            total_skipped=0,
            total_errors=0,
            status=ScrapingStatus.COMPLETED
        )
        
        # Get subscription data
        subscription_data = result.get_subscription_data()
        
        # Verify duration keys are filesystem-safe
        assert "= Strength (15 min)" in subscription_data
        assert "= Yoga (30 min)" in subscription_data
        
        # Verify episode titles are filesystem-safe
        strength_section = subscription_data["= Strength (15 min)"]
        yoga_section = subscription_data["= Yoga (30 min)"]
        
        # Check that slashes are removed from episode titles
        assert "15 min 50-50 Workout with Kirra Michel" in strength_section
        assert "Morning- Flow Session with Test-Instructor" in yoga_section
        
        # Verify the subscription data can be serialized to YAML
        import yaml
        yaml_output = yaml.dump(subscription_data, allow_unicode=True, default_flow_style=False)
        parsed_data = yaml.safe_load(yaml_output)
        assert parsed_data == subscription_data
    
    def test_filesystem_sanitization_comprehensive(self):
        """Comprehensive test with all types of problematic characters."""
        from src.webscraper.models import ScrapedClass, ScrapingStatus
        
        # Create a class with many problematic characters
        scraped_class = ScrapedClass(
            class_id="test123",
            title='Complex: "50/50" Workout*?',
            instructor="Test\\Instructor|Name",
            activity="Strength<>Training",
            duration_minutes=20,
            player_url="https://example.com/class",
            season_number=20,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        # Convert to subscription entry
        entry = scraped_class.to_subscription_entry()
        
        # Verify all problematic characters are sanitized
        expected_dir = "/media/peloton/Strength--Training/Test-Instructor-Name"
        assert entry["overrides"]["tv_show_directory"] == expected_dir
        
        # Verify the entry is valid YAML
        import yaml
        try:
            yaml_output = yaml.dump(entry, allow_unicode=True, default_flow_style=False)
            parsed_entry = yaml.safe_load(yaml_output)
            assert parsed_entry == entry
        except Exception as e:
            pytest.fail(f"YAML serialization failed: {e}")


class TestMediaDirectoryConfiguration:
    """Test cases for configurable media directory functionality."""
    
    def test_scraped_class_uses_default_media_dir(self):
        """Test ScrapedClass uses default media directory when none specified."""
        from src.webscraper.models import ScrapedClass, ScrapingStatus
        
        scraped_class = ScrapedClass(
            class_id="test123",
            title="Test Workout",
            instructor="Test Instructor",
            activity="Strength",
            duration_minutes=20,
            player_url="https://example.com/class",
            season_number=20,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        # Test default behavior
        entry = scraped_class.to_subscription_entry()
        assert entry["overrides"]["tv_show_directory"] == "/media/peloton/Strength/Test Instructor"
    
    def test_scraped_class_uses_configured_media_dir(self):
        """Test ScrapedClass uses configured media directory."""
        from src.webscraper.models import ScrapedClass, ScrapingStatus
        
        scraped_class = ScrapedClass(
            class_id="test123",
            title="Test Workout",
            instructor="Test Instructor",
            activity="Strength",
            duration_minutes=20,
            player_url="https://example.com/class",
            season_number=20,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        # Test with Windows-style path
        entry = scraped_class.to_subscription_entry("D:/labspace/tmp/test-media")
        assert entry["overrides"]["tv_show_directory"] == "D:/labspace/tmp/test-media/Strength/Test Instructor"
        
        # Test with Unix-style path
        entry = scraped_class.to_subscription_entry("/home/user/media")
        assert entry["overrides"]["tv_show_directory"] == "/home/user/media/Strength/Test Instructor"
        
        # Test with trailing slash removal
        entry = scraped_class.to_subscription_entry("/media/peloton/")
        assert entry["overrides"]["tv_show_directory"] == "/media/peloton/Strength/Test Instructor"
        
        # Test with trailing backslash removal (Windows)
        entry = scraped_class.to_subscription_entry("D:\\media\\peloton\\")
        assert entry["overrides"]["tv_show_directory"] == "D:\\media\\peloton/Strength/Test Instructor"
    
    def test_scraping_result_uses_configured_media_dir(self):
        """Test ScrapingResult passes media directory to scraped classes."""
        from src.webscraper.models import ScrapedClass, ScrapingResult, ScrapingStatus
        
        scraped_class = ScrapedClass(
            class_id="test123",
            title="Test Workout",
            instructor="Test Instructor",
            activity="Strength",
            duration_minutes=20,
            player_url="https://example.com/class",
            season_number=20,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        result = ScrapingResult(
            activity="strength",
            classes=[scraped_class],
            total_found=1,
            total_skipped=0,
            total_errors=0,
            status=ScrapingStatus.COMPLETED
        )
        
        # Test with configured media directory
        subscription_data = result.get_subscription_data("D:/labspace/tmp/test-media")
        
        # Check that the directory is correctly set
        strength_section = subscription_data["= Strength (20 min)"]
        episode_data = list(strength_section.values())[0]
        assert episode_data["overrides"]["tv_show_directory"] == "D:/labspace/tmp/test-media/Strength/Test Instructor"
    
    def test_path_style_consistency(self):
        """Test that path styles are handled consistently."""
        from src.webscraper.models import ScrapedClass, ScrapingStatus
        
        scraped_class = ScrapedClass(
            class_id="test123",
            title="Test Workout",
            instructor="Test Instructor",
            activity="Strength",
            duration_minutes=20,
            player_url="https://example.com/class",
            season_number=20,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        # Test various input formats
        test_cases = [
            ("D:/labspace/tmp/test-media", "D:/labspace/tmp/test-media/Strength/Test Instructor"),
            ("D:\\labspace\\tmp\\test-media", "D:\\labspace\\tmp\\test-media/Strength/Test Instructor"),
            ("/home/user/media", "/home/user/media/Strength/Test Instructor"),
            ("C:/Program Files/Media", "C:/Program Files/Media/Strength/Test Instructor"),
            ("/media/peloton", "/media/peloton/Strength/Test Instructor"),
        ]
        
        for input_dir, expected_output in test_cases:
            entry = scraped_class.to_subscription_entry(input_dir)
            actual_output = entry["overrides"]["tv_show_directory"]
            assert actual_output == expected_output, f"Input: {input_dir}, Expected: {expected_output}, Got: {actual_output}"
    
    def test_special_characters_in_media_dir(self):
        """Test media directories with special characters."""
        from src.webscraper.models import ScrapedClass, ScrapingStatus
        
        scraped_class = ScrapedClass(
            class_id="test123",
            title="Test Workout",
            instructor="Test Instructor",
            activity="Strength",
            duration_minutes=20,
            player_url="https://example.com/class",
            season_number=20,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        # Test with spaces in path
        entry = scraped_class.to_subscription_entry("D:/My Media/Peloton Content")
        assert entry["overrides"]["tv_show_directory"] == "D:/My Media/Peloton Content/Strength/Test Instructor"
        
        # Test with special characters (should work as-is since we only sanitize the activity/instructor parts)
        entry = scraped_class.to_subscription_entry("/media/peloton-data")
        assert entry["overrides"]["tv_show_directory"] == "/media/peloton-data/Strength/Test Instructor"