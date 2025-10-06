"""Tests for the subscription parser URL format fix."""

import tempfile
import yaml
from pathlib import Path
import pytest
from src.io.peloton.episodes_from_subscriptions import EpisodesFromSubscriptions
from src.io.episode_parser import Activity


class TestSubscriptionParserUrlFormatFix:
    """Test that the subscription parser correctly handles /classes/player/ URL format."""
    
    def test_find_subscription_class_ids_for_activity_with_player_urls(self):
        """Test that the parser correctly extracts class IDs from /classes/player/ URLs."""
        # Create test data with the correct URL format
        test_data = {
            "Plex TV Show by Date": {
                "= Walking (30 min)": {
                    "30 min Hike with Kirsten Ferguson": {
                        "download": "https://members.onepeloton.com/classes/player/3b784236209b4d30aba4a9289b55dabd",
                        "overrides": {
                            "tv_show_directory": "D:/labspace/tmp/test-media/Walking/Kirsten Ferguson",
                            "season_number": 30,
                            "episode_number": 1
                        }
                    },
                    "30 min Walk + Run: Menopause with Susie Chan": {
                        "download": "https://members.onepeloton.com/classes/player/1972cfdfa19042c5af6750a10c99ca3a",
                        "overrides": {
                            "tv_show_directory": "D:/labspace/tmp/test-media/Walking/Susie Chan",
                            "season_number": 30,
                            "episode_number": 2
                        }
                    }
                },
                "= Cycling (20 min)": {
                    "20 min HIIT Ride with Emma Lovewell": {
                        "download": "https://members.onepeloton.com/classes/player/abc123def456ghi789",
                        "overrides": {
                            "tv_show_directory": "D:/labspace/tmp/test-media/Cycling/Emma Lovewell",
                            "season_number": 20,
                            "episode_number": 1
                        }
                    }
                }
            }
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            temp_file = f.name
        
        try:
            # Test the parser
            parser = EpisodesFromSubscriptions(temp_file)
            
            # Test Walking activity
            walking_class_ids = parser.find_subscription_class_ids_for_activity(Activity.WALKING)
            expected_walking_ids = {
                "3b784236209b4d30aba4a9289b55dabd",
                "1972cfdfa19042c5af6750a10c99ca3a"
            }
            assert walking_class_ids == expected_walking_ids
            
            # Test Cycling activity
            cycling_class_ids = parser.find_subscription_class_ids_for_activity(Activity.CYCLING)
            expected_cycling_ids = {
                "abc123def456ghi789"
            }
            assert cycling_class_ids == expected_cycling_ids
            
            # Test Strength activity (should be empty)
            strength_class_ids = parser.find_subscription_class_ids_for_activity(Activity.STRENGTH)
            assert strength_class_ids == set()
            
        finally:
            # Clean up
            Path(temp_file).unlink()
    
    def test_find_subscription_class_ids_for_activity_with_legacy_urls(self):
        """Test that the parser still works with legacy classId= parameter URLs."""
        # Create test data with legacy URL format
        test_data = {
            "Plex TV Show by Date": {
                "= Walking (30 min)": {
                    "30 min Hike with Kirsten Ferguson": {
                        "download": "https://members.onepeloton.com/classes?classId=3b784236209b4d30aba4a9289b55dabd",
                        "overrides": {
                            "tv_show_directory": "D:/labspace/tmp/test-media/Walking/Kirsten Ferguson",
                            "season_number": 30,
                            "episode_number": 1
                        }
                    }
                }
            }
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            temp_file = f.name
        
        try:
            # Test the parser
            parser = EpisodesFromSubscriptions(temp_file)
            
            # Test Walking activity
            walking_class_ids = parser.find_subscription_class_ids_for_activity(Activity.WALKING)
            expected_walking_ids = {
                "3b784236209b4d30aba4a9289b55dabd"
            }
            assert walking_class_ids == expected_walking_ids
            
        finally:
            # Clean up
            Path(temp_file).unlink()
    
    def test_find_subscription_class_ids_for_activity_with_mixed_urls(self):
        """Test that the parser handles both URL formats in the same file."""
        # Create test data with mixed URL formats
        test_data = {
            "Plex TV Show by Date": {
                "= Walking (30 min)": {
                    "30 min Hike with Kirsten Ferguson": {
                        "download": "https://members.onepeloton.com/classes/player/3b784236209b4d30aba4a9289b55dabd",
                        "overrides": {
                            "tv_show_directory": "D:/labspace/tmp/test-media/Walking/Kirsten Ferguson",
                            "season_number": 30,
                            "episode_number": 1
                        }
                    },
                    "30 min Walk + Run: Menopause with Susie Chan": {
                        "download": "https://members.onepeloton.com/classes?classId=1972cfdfa19042c5af6750a10c99ca3a",
                        "overrides": {
                            "tv_show_directory": "D:/labspace/tmp/test-media/Walking/Susie Chan",
                            "season_number": 30,
                            "episode_number": 2
                        }
                    }
                }
            }
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            temp_file = f.name
        
        try:
            # Test the parser
            parser = EpisodesFromSubscriptions(temp_file)
            
            # Test Walking activity
            walking_class_ids = parser.find_subscription_class_ids_for_activity(Activity.WALKING)
            expected_walking_ids = {
                "3b784236209b4d30aba4a9289b55dabd",
                "1972cfdfa19042c5af6750a10c99ca3a"
            }
            assert walking_class_ids == expected_walking_ids
            
        finally:
            # Clean up
            Path(temp_file).unlink()
    
    def test_find_subscription_class_ids_for_activity_with_url_parameters(self):
        """Test that the parser correctly handles URLs with query parameters and fragments."""
        # Create test data with URLs containing parameters
        test_data = {
            "Plex TV Show by Date": {
                "= Walking (30 min)": {
                    "30 min Hike with Kirsten Ferguson": {
                        "download": "https://members.onepeloton.com/classes/player/3b784236209b4d30aba4a9289b55dabd?param=value#fragment",
                        "overrides": {
                            "tv_show_directory": "D:/labspace/tmp/test-media/Walking/Kirsten Ferguson",
                            "season_number": 30,
                            "episode_number": 1
                        }
                    }
                }
            }
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            temp_file = f.name
        
        try:
            # Test the parser
            parser = EpisodesFromSubscriptions(temp_file)
            
            # Test Walking activity
            walking_class_ids = parser.find_subscription_class_ids_for_activity(Activity.WALKING)
            expected_walking_ids = {
                "3b784236209b4d30aba4a9289b55dabd"
            }
            assert walking_class_ids == expected_walking_ids
            
        finally:
            # Clean up
            Path(temp_file).unlink()
