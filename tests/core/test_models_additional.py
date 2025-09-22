"""Additional tests for models.py to improve coverage."""

from src.core.models import Activity, ActivityData


class TestModelsAdditional:
    """Additional tests for models to reach missing lines."""

    def test_activity_data_get_next_episode(self):
        """Test get_next_episode method."""
        activity_data = ActivityData(activity=Activity.CYCLING)
        activity_data.max_episode = {20: 5, 30: 10}
        
        # Test existing season
        assert activity_data.get_next_episode(20) == 6
        assert activity_data.get_next_episode(30) == 11
        
        # Test non-existing season (should return 1)
        assert activity_data.get_next_episode(45) == 1

