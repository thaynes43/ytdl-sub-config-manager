"""Tests for core models."""

import pytest

from ytdl_sub_config_manager.core.models import Activity, ActivityData


class TestActivity:
    """Test Activity enum."""
    
    def test_activity_values(self):
        """Test that Activity enum has expected values."""
        assert Activity.CYCLING.value == "cycling"
        assert Activity.YOGA.value == "yoga"
        assert Activity.STRENGTH.value == "strength"
        assert Activity.MEDITATION.value == "meditation"
        assert Activity.CARDIO.value == "cardio"
        assert Activity.STRETCHING.value == "stretching"
        assert Activity.RUNNING.value == "running"
        assert Activity.WALKING.value == "walking"
        assert Activity.BOOTCAMP.value == "bootcamp"
        assert Activity.BIKE_BOOTCAMP.value == "bike_bootcamp"
        assert Activity.ROWING.value == "rowing"
        assert Activity.ROW_BOOTCAMP.value == "row_bootcamp"
    
    def test_activity_enum_completeness(self):
        """Test that we have all expected activities."""
        expected_activities = {
            "all", "cycling", "yoga", "strength", "meditation", "cardio", 
            "stretching", "running", "walking", "bootcamp", 
            "bike_bootcamp", "rowing", "row_bootcamp"
        }
        actual_activities = {activity.value for activity in Activity}
        assert actual_activities == expected_activities


class TestActivityData:
    """Test ActivityData class."""
    
    def test_init(self):
        """Test ActivityData initialization."""
        activity_data = ActivityData(Activity.CYCLING)
        assert activity_data.activity == Activity.CYCLING
        assert activity_data.max_episode == {}
    
    def test_update(self):
        """Test updating episode data."""
        activity_data = ActivityData(Activity.CYCLING)
        
        # Add first episode
        activity_data.update(20, 1)
        assert activity_data.max_episode[20] == 1
        
        # Add higher episode in same season
        activity_data.update(20, 3)
        assert activity_data.max_episode[20] == 3
        
        # Add lower episode (should not update)
        activity_data.update(20, 2)
        assert activity_data.max_episode[20] == 3
        
        # Add episode in different season
        activity_data.update(30, 5)
        assert activity_data.max_episode[30] == 5
        assert activity_data.max_episode[20] == 3  # Should not affect other season
    
    def test_merge_collections(self):
        """Test merging ActivityData collections."""
        # Create first collection
        map1 = {
            Activity.CYCLING: ActivityData(Activity.CYCLING),
            Activity.YOGA: ActivityData(Activity.YOGA),
        }
        map1[Activity.CYCLING].update(20, 5)
        map1[Activity.CYCLING].update(30, 3)
        map1[Activity.YOGA].update(30, 10)
        
        # Create second collection
        map2 = {
            Activity.CYCLING: ActivityData(Activity.CYCLING),
            Activity.STRENGTH: ActivityData(Activity.STRENGTH),
        }
        map2[Activity.CYCLING].update(20, 8)  # Higher than map1
        map2[Activity.CYCLING].update(45, 2)  # New season
        map2[Activity.STRENGTH].update(10, 5)
        
        # Merge collections
        merged = ActivityData.merge_collections(map1, map2)
        
        # Check merged results
        assert len(merged) == 3  # CYCLING, YOGA, STRENGTH
        
        # CYCLING should have max from both collections
        cycling_data = merged[Activity.CYCLING]
        assert cycling_data.max_episode[20] == 8  # Max of 5 and 8
        assert cycling_data.max_episode[30] == 3  # Only in map1
        assert cycling_data.max_episode[45] == 2  # Only in map2
        
        # YOGA should be unchanged from map1
        yoga_data = merged[Activity.YOGA]
        assert yoga_data.max_episode[30] == 10
        
        # STRENGTH should be from map2
        strength_data = merged[Activity.STRENGTH]
        assert strength_data.max_episode[10] == 5
    
    def test_merge_collections_empty(self):
        """Test merging with empty collections."""
        map1 = {Activity.CYCLING: ActivityData(Activity.CYCLING)}
        map1[Activity.CYCLING].update(20, 5)
        
        # Merge with empty
        merged = ActivityData.merge_collections(map1, {})
        assert len(merged) == 1
        assert merged[Activity.CYCLING].max_episode[20] == 5
        
        # Merge empty with non-empty
        merged = ActivityData.merge_collections({}, map1)
        assert len(merged) == 1
        assert merged[Activity.CYCLING].max_episode[20] == 5
    
    def test_parse_activities_from_env(self):
        """Test parsing activities from environment variable string."""
        # Test empty/None input
        result = ActivityData.parse_activities_from_env("")
        expected_all_except_all = [a for a in Activity if a != Activity.ALL]
        assert set(result) == set(expected_all_except_all)
        
        result = ActivityData.parse_activities_from_env(None)
        assert set(result) == set(expected_all_except_all)
        
        # Test single activity by value
        result = ActivityData.parse_activities_from_env("cycling")
        assert result == [Activity.CYCLING]
        
        # Test single activity by name
        result = ActivityData.parse_activities_from_env("CYCLING")
        assert result == [Activity.CYCLING]
        
        # Test multiple activities
        result = ActivityData.parse_activities_from_env("cycling,yoga,strength")
        expected = [Activity.CYCLING, Activity.YOGA, Activity.STRENGTH]
        assert set(result) == set(expected)
        
        # Test with spaces
        result = ActivityData.parse_activities_from_env(" cycling , yoga , strength ")
        expected = [Activity.CYCLING, Activity.YOGA, Activity.STRENGTH]
        assert set(result) == set(expected)
        
        # Test mixed case
        result = ActivityData.parse_activities_from_env("Cycling,YOGA,strength")
        expected = [Activity.CYCLING, Activity.YOGA, Activity.STRENGTH]
        assert set(result) == set(expected)
        
        # Test invalid activity
        with pytest.raises(ValueError, match="Invalid activity"):
            ActivityData.parse_activities_from_env("invalid_activity")
        
        # Test mixed valid and invalid
        with pytest.raises(ValueError, match="Invalid activity"):
            ActivityData.parse_activities_from_env("cycling,invalid,yoga")
