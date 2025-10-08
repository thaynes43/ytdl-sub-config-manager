"""Tests for activity name matching fix in find_subscription_class_ids_for_activity.

This tests the regression fix where activity names with underscores (like bike_bootcamp)
were not matching duration keys with spaces (like "= Bike Bootcamp (45 min)").
"""

import tempfile
import yaml
from pathlib import Path

import pytest

from src.core.models import Activity
from src.io.peloton.episodes_from_subscriptions import EpisodesFromSubscriptions


class TestActivityNameMatchingFix:
    """Test that activity names with underscores match duration keys with spaces."""
    
    @pytest.fixture
    def temp_subs_file(self):
        """Create a temporary subscriptions file with bootcamp variants."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            subs_data = {
                "Plex TV Show by Date": {
                    "= Bike Bootcamp (30 min)": {
                        "30 min Full Body Bootcamp with Callie": {
                            "download": "https://members.onepeloton.com/classes/player/class123",
                            "overrides": {
                                "tv_show_directory": "/media/peloton/Bike Bootcamp/Callie",
                                "season_number": 30,
                                "episode_number": 1
                            }
                        },
                        "30 min Total Body Bootcamp with Robin": {
                            "download": "https://members.onepeloton.com/classes/player/class456",
                            "overrides": {
                                "tv_show_directory": "/media/peloton/Bike Bootcamp/Robin",
                                "season_number": 30,
                                "episode_number": 2
                            }
                        }
                    },
                    "= Bike Bootcamp (45 min)": {
                        "45 min Full Body Bootcamp with Jess": {
                            "download": "https://members.onepeloton.com/classes/player/class789",
                            "overrides": {
                                "tv_show_directory": "/media/peloton/Bike Bootcamp/Jess",
                                "season_number": 45,
                                "episode_number": 1
                            }
                        }
                    },
                    "= Row Bootcamp (30 min)": {
                        "30 min Full Body Row with Adrian": {
                            "download": "https://members.onepeloton.com/classes/player/class999",
                            "overrides": {
                                "tv_show_directory": "/media/peloton/Row Bootcamp/Adrian",
                                "season_number": 30,
                                "episode_number": 1
                            }
                        }
                    },
                    "= Tread Bootcamp (30 min)": {
                        "30 min Full Body with Marcel": {
                            "download": "https://members.onepeloton.com/classes/player/class111",
                            "overrides": {
                                "tv_show_directory": "/media/peloton/Tread Bootcamp/Marcel",
                                "season_number": 30,
                                "episode_number": 1
                            }
                        }
                    },
                    "= Cycling (20 min)": {
                        "20 min Ride with Leanne": {
                            "download": "https://members.onepeloton.com/classes/player/class222",
                            "overrides": {
                                "tv_show_directory": "/media/peloton/Cycling/Leanne",
                                "season_number": 20,
                                "episode_number": 1
                            }
                        },
                        "20 min Ride with Denis": {
                            "download": "https://members.onepeloton.com/classes/player/class333",
                            "overrides": {
                                "tv_show_directory": "/media/peloton/Cycling/Denis",
                                "season_number": 20,
                                "episode_number": 2
                            }
                        }
                    }
                }
            }
            yaml.dump(subs_data, f)
            path = Path(f.name)
        
        yield path
        path.unlink()
    
    def test_bike_bootcamp_matching(self, temp_subs_file):
        """Test that BIKE_BOOTCAMP activity matches 'Bike Bootcamp' duration keys."""
        parser = EpisodesFromSubscriptions(temp_subs_file)
        
        class_ids = parser.find_subscription_class_ids_for_activity(Activity.BIKE_BOOTCAMP)
        
        # Should find all 3 bike bootcamp classes (2 from 30min, 1 from 45min)
        assert len(class_ids) == 3
        assert "class123" in class_ids
        assert "class456" in class_ids
        assert "class789" in class_ids
        
        # Should NOT include other bootcamp types
        assert "class999" not in class_ids  # row bootcamp
        assert "class111" not in class_ids  # tread bootcamp
    
    def test_row_bootcamp_matching(self, temp_subs_file):
        """Test that ROW_BOOTCAMP activity matches 'Row Bootcamp' duration keys."""
        parser = EpisodesFromSubscriptions(temp_subs_file)
        
        class_ids = parser.find_subscription_class_ids_for_activity(Activity.ROW_BOOTCAMP)
        
        # Should find only the row bootcamp class
        assert len(class_ids) == 1
        assert "class999" in class_ids
        
        # Should NOT include other bootcamp types
        assert "class123" not in class_ids  # bike bootcamp
        assert "class111" not in class_ids  # tread bootcamp
    
    def test_bootcamp_matching(self, temp_subs_file):
        """Test that BOOTCAMP activity matches 'Tread Bootcamp' duration keys."""
        parser = EpisodesFromSubscriptions(temp_subs_file)
        
        class_ids = parser.find_subscription_class_ids_for_activity(Activity.BOOTCAMP)
        
        # Should find only the tread bootcamp class
        assert len(class_ids) == 1
        assert "class111" in class_ids
        
        # Should NOT include other bootcamp types
        assert "class123" not in class_ids  # bike bootcamp
        assert "class999" not in class_ids  # row bootcamp
    
    def test_cycling_matching(self, temp_subs_file):
        """Test that CYCLING activity matches 'Cycling' duration keys."""
        parser = EpisodesFromSubscriptions(temp_subs_file)
        
        class_ids = parser.find_subscription_class_ids_for_activity(Activity.CYCLING)
        
        # Should find both cycling classes
        assert len(class_ids) == 2
        assert "class222" in class_ids
        assert "class333" in class_ids
        
        # Should NOT include bootcamp classes
        assert "class123" not in class_ids
    
    def test_activity_folder_name_mapping(self, temp_subs_file):
        """Test the _get_activity_folder_name helper method."""
        parser = EpisodesFromSubscriptions(temp_subs_file)
        
        # Test bootcamp variants
        assert parser._get_activity_folder_name("bike_bootcamp") == "Bike Bootcamp"
        assert parser._get_activity_folder_name("row_bootcamp") == "Row Bootcamp"
        assert parser._get_activity_folder_name("bootcamp") == "Tread Bootcamp"
        
        # Test regular activities
        assert parser._get_activity_folder_name("cycling") == "Cycling"
        assert parser._get_activity_folder_name("yoga") == "Yoga"
        assert parser._get_activity_folder_name("strength") == "Strength"
        
        # Test case insensitivity
        assert parser._get_activity_folder_name("BIKE_BOOTCAMP") == "Bike Bootcamp"
        assert parser._get_activity_folder_name("CYCLING") == "Cycling"
    
    def test_regression_bike_bootcamp_not_counted_as_bootcamp(self, temp_subs_file):
        """Regression test: bike_bootcamp subscriptions should not be counted as bootcamp.
        
        This was the original bug - when counting bootcamp subscriptions, it was also
        counting bike_bootcamp and row_bootcamp subscriptions because it used substring matching.
        """
        parser = EpisodesFromSubscriptions(temp_subs_file)
        
        bootcamp_ids = parser.find_subscription_class_ids_for_activity(Activity.BOOTCAMP)
        bike_bootcamp_ids = parser.find_subscription_class_ids_for_activity(Activity.BIKE_BOOTCAMP)
        
        # These should be completely separate sets with no overlap
        assert len(bootcamp_ids) == 1
        assert len(bike_bootcamp_ids) == 3
        assert bootcamp_ids.isdisjoint(bike_bootcamp_ids)
    
    def test_empty_file(self):
        """Test handling of empty subscriptions file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({}, f)
            path = Path(f.name)
        
        try:
            parser = EpisodesFromSubscriptions(path)
            class_ids = parser.find_subscription_class_ids_for_activity(Activity.BIKE_BOOTCAMP)
            assert len(class_ids) == 0
        finally:
            path.unlink()
    
    def test_nonexistent_file(self):
        """Test handling of nonexistent subscriptions file."""
        parser = EpisodesFromSubscriptions(Path("/nonexistent/file.yaml"))
        class_ids = parser.find_subscription_class_ids_for_activity(Activity.BIKE_BOOTCAMP)
        assert len(class_ids) == 0
    
    def test_legacy_url_format(self, temp_subs_file):
        """Test that legacy URL format with classId parameter is also handled."""
        # Add a subscription with legacy URL format
        with open(temp_subs_file, 'r') as f:
            subs_data = yaml.safe_load(f)
        
        subs_data["Plex TV Show by Date"]["= Bike Bootcamp (30 min)"]["30 min Legacy Format"] = {
            "download": "https://members.onepeloton.com/classes?classId=legacy123&other=param",
            "overrides": {
                "tv_show_directory": "/media/peloton/Bike Bootcamp/Test",
                "season_number": 30,
                "episode_number": 3
            }
        }
        
        with open(temp_subs_file, 'w') as f:
            yaml.dump(subs_data, f)
        
        parser = EpisodesFromSubscriptions(temp_subs_file)
        class_ids = parser.find_subscription_class_ids_for_activity(Activity.BIKE_BOOTCAMP)
        
        # Should find the legacy format class ID
        assert "legacy123" in class_ids
        # Should still find the original 3 classes plus this new one
        assert len(class_ids) == 4
