"""Tests for bootcamp folder naming in subscription entries."""

import pytest
from src.webscraper.models import ScrapedClass, ScrapingStatus


class TestBootcampFolderNaming:
    """Test that bootcamp activities get correct folder names in subscription entries."""
    
    def test_bootcamp_folder_name_mapping(self):
        """Test that bootcamp activities map to correct folder names."""
        # Test regular bootcamp -> Tread Bootcamp
        bootcamp_class = ScrapedClass(
            class_id="test123",
            title="30 min HIIT Bootcamp",
            instructor="Andy Speer",
            activity="bootcamp",
            duration_minutes=30,
            player_url="https://members.onepeloton.com/classes/player/test123",
            season_number=30,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        subscription_entry = bootcamp_class.to_subscription_entry("/media/peloton")
        tv_show_directory = subscription_entry["overrides"]["tv_show_directory"]
        
        assert tv_show_directory == "/media/peloton/Tread Bootcamp/Andy Speer"
    
    def test_bike_bootcamp_folder_name_mapping(self):
        """Test that bike_bootcamp maps to Bike Bootcamp folder."""
        bike_bootcamp_class = ScrapedClass(
            class_id="test456",
            title="45 min Bike Bootcamp",
            instructor="Emma Lovewell",
            activity="bike_bootcamp",
            duration_minutes=45,
            player_url="https://members.onepeloton.com/classes/player/test456",
            season_number=45,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        subscription_entry = bike_bootcamp_class.to_subscription_entry("/media/peloton")
        tv_show_directory = subscription_entry["overrides"]["tv_show_directory"]
        
        assert tv_show_directory == "/media/peloton/Bike Bootcamp/Emma Lovewell"
    
    def test_row_bootcamp_folder_name_mapping(self):
        """Test that row_bootcamp maps to Row Bootcamp folder."""
        row_bootcamp_class = ScrapedClass(
            class_id="test789",
            title="20 min Row Bootcamp",
            instructor="Josh Crosby",
            activity="row_bootcamp",
            duration_minutes=20,
            player_url="https://members.onepeloton.com/classes/player/test789",
            season_number=20,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        subscription_entry = row_bootcamp_class.to_subscription_entry("/media/peloton")
        tv_show_directory = subscription_entry["overrides"]["tv_show_directory"]
        
        assert tv_show_directory == "/media/peloton/Row Bootcamp/Josh Crosby"
    
    def test_regular_activity_folder_name_mapping(self):
        """Test that regular activities use title case."""
        cycling_class = ScrapedClass(
            class_id="test000",
            title="30 min Power Zone Ride",
            instructor="Matt Wilpers",
            activity="cycling",
            duration_minutes=30,
            player_url="https://members.onepeloton.com/classes/player/test000",
            season_number=30,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        subscription_entry = cycling_class.to_subscription_entry("/media/peloton")
        tv_show_directory = subscription_entry["overrides"]["tv_show_directory"]
        
        assert tv_show_directory == "/media/peloton/Cycling/Matt Wilpers"
    
    def test_duration_key_uses_correct_folder_name(self):
        """Test that duration keys in subscription data use correct folder names."""
        from src.webscraper.models import ScrapingResult
        
        bootcamp_class = ScrapedClass(
            class_id="test123",
            title="30 min HIIT Bootcamp",
            instructor="Andy Speer",
            activity="bootcamp",
            duration_minutes=30,
            player_url="https://members.onepeloton.com/classes/player/test123",
            season_number=30,
            episode_number=1,
            status=ScrapingStatus.COMPLETED
        )
        
        result = ScrapingResult(
            activity="bootcamp",
            classes=[bootcamp_class],
            total_found=1,
            total_skipped=0,
            total_errors=0,
            status=ScrapingStatus.COMPLETED
        )
        
        subscription_data = result.get_subscription_data("/media/peloton")
        
        # Should have a duration key with "Tread Bootcamp" not "Bootcamp"
        expected_duration_key = "= Tread Bootcamp (30 min)"
        assert expected_duration_key in subscription_data
        
        # Verify the entry structure
        episode_entry = subscription_data[expected_duration_key]["30 min HIIT Bootcamp with Andy Speer"]
        assert episode_entry["overrides"]["tv_show_directory"] == "/media/peloton/Tread Bootcamp/Andy Speer"
