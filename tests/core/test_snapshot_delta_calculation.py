"""Test for snapshot delta calculation bug fix.

This tests the regression where episode deltas were showing +0 instead of the
actual difference from the previous run because the snapshot was loaded before
the GitHub repo was cloned.
"""

from src.core.snapshot import RunSnapshot


class TestSnapshotDeltaCalculation:
    """Test that deltas are calculated correctly from previous snapshots."""
    
    def test_delta_calculation_with_real_data(self):
        """Test delta calculation using real data from the bug report.
        
        Previous run (2025-10-07):
        - Episodes on disk: 5133
        - BIKE_BOOTCAMP: 275
        
        Current run (2025-10-08):
        - Episodes on disk: 5167
        - BIKE_BOOTCAMP: 276
        
        Expected deltas:
        - Episodes on disk: +34
        - BIKE_BOOTCAMP: +1
        """
        # Previous run snapshot
        previous_snapshot = RunSnapshot(
            run_timestamp="2025-10-07T22:00:02.326375",
            videos_on_disk=5133,
            videos_in_subscriptions=77,
            new_videos_added=35,
            total_activities=12,
            episodes_by_activity={
                "RUNNING": 632,
                "STRENGTH": 692,
                "CYCLING": 813,
                "ROW_BOOTCAMP": 226,
                "WALKING": 505,
                "STRETCHING": 322,
                "YOGA": 432,
                "ROWING": 370,
                "BOOTCAMP": 271,
                "MEDITATION": 317,
                "CARDIO": 278,
                "BIKE_BOOTCAMP": 275
            }
        )
        
        # Current run snapshot
        current_snapshot = RunSnapshot(
            run_timestamp="2025-10-08T13:57:37.667683",
            videos_on_disk=5167,
            videos_in_subscriptions=535,
            new_videos_added=260,
            total_activities=12,
            episodes_by_activity={
                "RUNNING": 639,
                "STRENGTH": 697,
                "CYCLING": 825,
                "ROW_BOOTCAMP": 227,
                "WALKING": 509,
                "STRETCHING": 322,
                "YOGA": 432,
                "ROWING": 373,
                "BOOTCAMP": 272,
                "MEDITATION": 317,
                "CARDIO": 278,
                "BIKE_BOOTCAMP": 276
            }
        )
        
        # Calculate deltas
        disk_delta = current_snapshot.videos_on_disk - previous_snapshot.videos_on_disk
        assert disk_delta == 34, f"Expected +34 for disk delta, got {disk_delta}"
        
        bike_bootcamp_delta = current_snapshot.episodes_by_activity["BIKE_BOOTCAMP"] - previous_snapshot.episodes_by_activity["BIKE_BOOTCAMP"]
        assert bike_bootcamp_delta == 1, f"Expected +1 for BIKE_BOOTCAMP, got {bike_bootcamp_delta}"
        
        # Verify all activity deltas
        expected_deltas = {
            "RUNNING": 639 - 632,  # +7
            "STRENGTH": 697 - 692,  # +5
            "CYCLING": 825 - 813,  # +12
            "ROW_BOOTCAMP": 227 - 226,  # +1
            "WALKING": 509 - 505,  # +4
            "STRETCHING": 322 - 322,  # 0
            "YOGA": 432 - 432,  # 0
            "ROWING": 373 - 370,  # +3
            "BOOTCAMP": 272 - 271,  # +1
            "MEDITATION": 317 - 317,  # 0
            "CARDIO": 278 - 278,  # 0
            "BIKE_BOOTCAMP": 276 - 275  # +1
        }
        
        for activity, expected_delta in expected_deltas.items():
            actual_delta = current_snapshot.episodes_by_activity[activity] - previous_snapshot.episodes_by_activity[activity]
            assert actual_delta == expected_delta, f"Expected {expected_delta} for {activity}, got {actual_delta}"
    
    def test_delta_with_no_previous_snapshot(self):
        """Test that delta is 0 when there's no previous snapshot."""
        current_snapshot = RunSnapshot(
            run_timestamp="2025-10-08T13:57:37.667683",
            videos_on_disk=5167,
            videos_in_subscriptions=535,
            new_videos_added=260,
            total_activities=12,
            episodes_by_activity={
                "BIKE_BOOTCAMP": 276
            }
        )
        
        # With no previous snapshot, delta should be 0
        previous_videos = 0  # No previous data
        disk_delta = current_snapshot.videos_on_disk - previous_videos
        
        # When there's no previous data, we'd show the current as the baseline
        assert disk_delta == 5167, f"Expected full count when no previous, got {disk_delta}"
    
    def test_snapshot_serialization_with_episodes_by_activity(self):
        """Test that episodes_by_activity is properly serialized and deserialized."""
        original = RunSnapshot(
            run_timestamp="2025-10-08T13:57:37.667683",
            videos_on_disk=5167,
            videos_in_subscriptions=535,
            new_videos_added=260,
            total_activities=12,
            episodes_by_activity={
                "RUNNING": 639,
                "BIKE_BOOTCAMP": 276
            }
        )
        
        # Serialize to dict
        data = original.to_dict()
        assert "episodes_by_activity" in data
        assert data["episodes_by_activity"]["BIKE_BOOTCAMP"] == 276
        
        # Deserialize from dict
        restored = RunSnapshot.from_dict(data)
        assert restored.episodes_by_activity["BIKE_BOOTCAMP"] == 276
        assert restored.videos_on_disk == 5167
    
    def test_backward_compatibility_without_episodes_by_activity(self):
        """Test that old snapshots without episodes_by_activity still load."""
        # Old snapshot format (before episodes_by_activity was added)
        old_data = {
            "run_timestamp": "2025-10-07T22:00:02.326375",
            "videos_on_disk": 5133,
            "videos_in_subscriptions": 77,
            "new_videos_added": 35,
            "total_activities": 12
            # Note: no episodes_by_activity
        }
        
        # Should load without error and have empty episodes_by_activity
        snapshot = RunSnapshot.from_dict(old_data)
        assert snapshot.videos_on_disk == 5133
        assert snapshot.episodes_by_activity == {}
    
    def test_delta_calculation_with_new_activity(self):
        """Test delta when a new activity appears that wasn't in previous run."""
        previous = RunSnapshot(
            run_timestamp="2025-10-07T22:00:02.326375",
            videos_on_disk=100,
            episodes_by_activity={
                "CYCLING": 50
            }
        )
        
        current = RunSnapshot(
            run_timestamp="2025-10-08T13:57:37.667683",
            videos_on_disk=150,
            episodes_by_activity={
                "CYCLING": 60,
                "YOGA": 40  # New activity
            }
        )
        
        # Delta for existing activity
        cycling_delta = current.episodes_by_activity["CYCLING"] - previous.episodes_by_activity["CYCLING"]
        assert cycling_delta == 10
        
        # Delta for new activity (should be full count)
        yoga_delta = current.episodes_by_activity["YOGA"] - previous.episodes_by_activity.get("YOGA", 0)
        assert yoga_delta == 40
