"""Tests for the metrics collection system."""

import pytest
import json
from datetime import datetime

from src.core.metrics import (
    DirectoryRepairMetrics,
    ActivityEpisodeStats,
    ExistingEpisodesMetrics,
    ActivityScrapingStats,
    WebScrapingMetrics,
    SubscriptionChangesMetrics,
    SubscriptionHistoryMetrics,
    RunSnapshot,
    RunMetrics
)


class TestDirectoryRepairMetrics:
    """Tests for DirectoryRepairMetrics."""
    
    def test_default_values(self):
        """Test that default values are zero."""
        metrics = DirectoryRepairMetrics()
        assert metrics.total_episodes_scanned == 0
        assert metrics.corrupted_locations_found == 0
        assert metrics.corrupted_locations_repaired == 0
        assert metrics.parent_directories_repaired == 0
        assert metrics.thumbnails_generated == 0
        assert metrics.episode_conflicts_found == 0
        assert metrics.episode_conflicts_resolved == 0
        assert metrics.repair_passes_executed == 0
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        metrics = DirectoryRepairMetrics(
            total_episodes_scanned=100,
            corrupted_locations_repaired=5,
            episode_conflicts_resolved=2
        )
        
        data = metrics.to_dict()
        assert data['total_episodes_scanned'] == 100
        assert data['corrupted_locations_repaired'] == 5
        assert data['episode_conflicts_resolved'] == 2
    
    def test_summary_no_episodes(self):
        """Test summary when no episodes found."""
        metrics = DirectoryRepairMetrics(total_episodes_scanned=0)
        summary = metrics.get_summary()
        assert "No episodes found" in summary
    
    def test_summary_no_repairs(self):
        """Test summary when no repairs needed."""
        metrics = DirectoryRepairMetrics(total_episodes_scanned=100)
        summary = metrics.get_summary()
        assert "100 episodes" in summary
        assert "no repairs needed" in summary
    
    def test_summary_with_repairs(self):
        """Test summary with various repairs."""
        metrics = DirectoryRepairMetrics(
            total_episodes_scanned=100,
            corrupted_locations_repaired=5,
            parent_directories_repaired=3,
            thumbnails_generated=10,
            episode_conflicts_resolved=2
        )
        summary = metrics.get_summary()
        assert "100 episodes" in summary
        assert "5 corrupted locations repaired" in summary
        assert "10 thumbnails generated" in summary
        assert "3 parent directories cleaned" in summary
        assert "2 episode conflicts resolved" in summary


class TestActivityEpisodeStats:
    """Tests for ActivityEpisodeStats."""
    
    def test_creation(self):
        """Test creating activity stats."""
        from src.core.metrics import SeasonStats
        
        stats = ActivityEpisodeStats(
            activity="strength",
            total_episodes=25,
            seasons={
                20: SeasonStats(season=20, episode_count=10, highest_episode_number=10),
                30: SeasonStats(season=30, episode_count=15, highest_episode_number=15)
            }
        )
        assert stats.activity == "strength"
        assert stats.total_episodes == 25
        assert stats.seasons[20].episode_count == 10
        assert stats.seasons[20].highest_episode_number == 10
        assert stats.seasons[30].episode_count == 15
        assert stats.seasons[30].highest_episode_number == 15
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        from src.core.metrics import SeasonStats
        
        stats = ActivityEpisodeStats(
            activity="yoga",
            total_episodes=15,
            seasons={
                10: SeasonStats(season=10, episode_count=5, highest_episode_number=5),
                20: SeasonStats(season=20, episode_count=10, highest_episode_number=10)
            }
        )
        data = stats.to_dict()
        assert data['activity'] == "yoga"
        assert data['total_episodes'] == 15
        assert data['seasons']['10']['episode_count'] == 5
        assert data['seasons']['10']['highest_episode_number'] == 5
        assert data['seasons']['20']['episode_count'] == 10
        assert data['seasons']['20']['highest_episode_number'] == 10


class TestExistingEpisodesMetrics:
    """Tests for ExistingEpisodesMetrics."""
    
    def test_default_values(self):
        """Test default values."""
        metrics = ExistingEpisodesMetrics()
        assert metrics.total_activities == 0
        assert metrics.total_episodes_on_disk == 0
        assert metrics.total_subscriptions_in_yaml == 0
        assert metrics.existing_class_ids_count == 0
        assert len(metrics.activities) == 0
    
    def test_to_dict_with_activities(self):
        """Test dictionary conversion with activities."""
        metrics = ExistingEpisodesMetrics(
            total_activities=2,
            total_episodes_on_disk=40,
            total_subscriptions_in_yaml=10
        )
        
        from src.core.metrics import SeasonStats
        
        metrics.activities['strength'] = ActivityEpisodeStats(
            activity="strength",
            total_episodes=25,
            seasons={
                20: SeasonStats(season=20, episode_count=10, highest_episode_number=10),
                30: SeasonStats(season=30, episode_count=15, highest_episode_number=15)
            }
        )
        
        data = metrics.to_dict()
        assert data['total_activities'] == 2
        assert data['total_episodes_on_disk'] == 40
        assert 'strength' in data['activities']
        assert data['activities']['strength']['total_episodes'] == 25
    
    def test_summary(self):
        """Test summary generation."""
        metrics = ExistingEpisodesMetrics(
            total_activities=12,
            total_episodes_on_disk=184,
            total_subscriptions_in_yaml=23,
            total_subscriptions_after_cleanup=20,
            existing_class_ids_count=195
        )
        
        summary = metrics.get_summary()
        assert "12 activities" in summary
        assert "184 episodes on disk" in summary
        assert "(+0)" in summary  # No previous data, so shows +0
        assert "23 subscriptions in YAML" in summary
        assert "195 unique class IDs" in summary


class TestActivityScrapingStats:
    """Tests for ActivityScrapingStats."""
    
    def test_creation(self):
        """Test creating scraping stats."""
        stats = ActivityScrapingStats(
            activity="strength",
            classes_found=25,
            classes_skipped=10,
            classes_added=15,
            errors=0,
            status="completed"
        )
        assert stats.activity == "strength"
        assert stats.classes_found == 25
        assert stats.classes_added == 15
        assert stats.status == "completed"
    
    def test_to_dict_no_error(self):
        """Test dictionary conversion without error message."""
        stats = ActivityScrapingStats(
            activity="yoga",
            classes_found=10,
            classes_added=10,
            status="completed"
        )
        data = stats.to_dict()
        assert 'error_message' not in data
    
    def test_to_dict_with_error(self):
        """Test dictionary conversion with error message."""
        stats = ActivityScrapingStats(
            activity="cycling",
            errors=1,
            status="failed",
            error_message="Connection timeout"
        )
        data = stats.to_dict()
        # Note: The current implementation removes None error_message
        # but keeps it if set
        assert data.get('error_message') == "Connection timeout"


class TestWebScrapingMetrics:
    """Tests for WebScrapingMetrics."""
    
    def test_default_values(self):
        """Test default values."""
        metrics = WebScrapingMetrics()
        assert metrics.total_activities_scraped == 0
        assert metrics.total_classes_found == 0
        assert metrics.total_classes_skipped == 0
        assert metrics.total_classes_added == 0
        assert metrics.total_errors == 0
        assert len(metrics.activities) == 0
    
    def test_to_dict_with_activities(self):
        """Test dictionary conversion with activities."""
        metrics = WebScrapingMetrics(
            total_activities_scraped=2,  # type: ignore
            total_classes_found=35,  # type: ignore
            total_classes_skipped=10,  # type: ignore
            total_classes_added=25  # type: ignore
        )
        
        metrics.activities['strength'] = ActivityScrapingStats(
            activity="strength",
            classes_found=25,
            classes_added=15,
            status="completed"
        )
        
        data = metrics.to_dict()
        assert data['total_activities_scraped'] == 2
        assert 'strength' in data['activities']
    
    def test_summary_no_activities(self):
        """Test summary when no activities scraped."""
        metrics = WebScrapingMetrics()
        summary = metrics.get_summary()
        assert "No activities scraped" in summary
    
    def test_summary_with_activities(self):
        """Test summary with scraped activities."""
        metrics = WebScrapingMetrics(
            total_activities_scraped=3,  # type: ignore
            total_classes_found=50,  # type: ignore
            total_classes_skipped=10,  # type: ignore
            total_classes_added=40  # type: ignore
        )
        
        summary = metrics.get_summary()
        assert "3 activities" in summary
        assert "50 classes found" in summary
        assert "10 skipped" in summary
        assert "40 added" in summary
    
    def test_summary_with_errors(self):
        """Test summary with errors."""
        metrics = WebScrapingMetrics(
            total_activities_scraped=2,  # type: ignore
            total_classes_found=20,  # type: ignore
            total_classes_added=18,  # type: ignore
            total_errors=2  # type: ignore
        )
        
        summary = metrics.get_summary()
        assert "2 errors" in summary


class TestSubscriptionChangesMetrics:
    """Tests for SubscriptionChangesMetrics."""
    
    def test_default_values(self):
        """Test default values."""
        metrics = SubscriptionChangesMetrics()
        assert metrics.subscriptions_removed_already_downloaded == 0
        assert metrics.subscriptions_removed_stale == 0
        assert metrics.subscriptions_added_new == 0
        assert metrics.subscription_directories_updated == 0
        assert metrics.subscription_titles_sanitized == 0
        assert metrics.subscription_conflicts_resolved == 0
        assert metrics.subscriptions_before_cleanup == 0
        assert metrics.subscriptions_after_cleanup == 0
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        metrics = SubscriptionChangesMetrics(
            subscriptions_removed_already_downloaded=5,
            subscriptions_added_new=15,
            subscription_conflicts_resolved=2,
            subscriptions_before_cleanup=100,
            subscriptions_after_cleanup=80
        )
        
        data = metrics.to_dict()
        assert data['subscriptions_removed_already_downloaded'] == 5
        assert data['subscriptions_added_new'] == 15
        assert data['subscription_conflicts_resolved'] == 2
        assert data['subscriptions_before_cleanup'] == 100
        assert data['subscriptions_after_cleanup'] == 80
    
    def test_summary_no_changes(self):
        """Test summary when no changes made."""
        metrics = SubscriptionChangesMetrics()
        summary = metrics.get_summary()
        assert "No changes to subscriptions.yaml" in summary
    
    def test_summary_with_changes(self):
        """Test summary with various changes."""
        metrics = SubscriptionChangesMetrics(
            subscriptions_before_cleanup=100,
            subscriptions_removed_already_downloaded=5,
            subscriptions_removed_stale=3,
            subscriptions_added_new=15,
            subscription_directories_updated=20,
            subscription_titles_sanitized=2,
            subscription_conflicts_resolved=1,
            subscriptions_after_cleanup=80
        )
        
        summary = metrics.get_summary()
        assert "File started with 100 subscriptions" in summary
        assert "Removed 5 because they were found on disk" in summary
        assert "Removed 3 because they expired" in summary
        assert "15 new added" in summary
        assert "20 directories updated" in summary
        assert "2 titles sanitized" in summary
        assert "1 conflicts resolved" in summary
        assert "80 subscriptions remain in the base file" in summary


class TestSubscriptionHistoryMetrics:
    """Tests for SubscriptionHistoryMetrics."""
    
    def test_default_values(self):
        """Test default values."""
        metrics = SubscriptionHistoryMetrics()
        assert metrics.total_tracked_subscriptions == 0
        assert metrics.subscriptions_added_to_history == 0
        assert metrics.subscriptions_removed_from_history == 0
        assert metrics.stale_subscriptions_found == 0
        assert metrics.history_synced is False
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        metrics = SubscriptionHistoryMetrics(
            total_tracked_subscriptions=100,
            subscriptions_added_to_history=10,
            history_synced=True
        )
        
        data = metrics.to_dict()
        assert data['total_tracked_subscriptions'] == 100
        assert data['subscriptions_added_to_history'] == 10
        assert data['history_synced'] is True
    
    def test_summary(self):
        """Test summary generation."""
        metrics = SubscriptionHistoryMetrics(
            total_tracked_subscriptions=105,
            subscriptions_added_to_history=10,
            subscriptions_removed_from_history=5,
            stale_subscriptions_found=3
        )
        
        summary = metrics.get_summary()
        assert "105 subscriptions" in summary
        assert "10 added" in summary
        assert "5 removed" in summary
        assert "3 stale" in summary


class TestRunSnapshot:
    """Tests for RunSnapshot."""
    
    def test_creation(self):
        """Test creating a snapshot."""
        timestamp = datetime.now().isoformat()
        snapshot = RunSnapshot(
            run_timestamp=timestamp,
            videos_on_disk=100,
            videos_in_subscriptions=25,
            new_videos_added=10,
            total_activities=12
        )
        
        assert snapshot.run_timestamp == timestamp
        assert snapshot.videos_on_disk == 100
        assert snapshot.videos_in_subscriptions == 25
        assert snapshot.new_videos_added == 10
        assert snapshot.total_activities == 12
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        timestamp = "2025-09-26T10:30:45.123456"
        snapshot = RunSnapshot(
            run_timestamp=timestamp,
            videos_on_disk=100,
            new_videos_added=10
        )
        
        data = snapshot.to_dict()
        assert data['run_timestamp'] == timestamp
        assert data['videos_on_disk'] == 100
        assert data['new_videos_added'] == 10
    
    def test_from_dict(self):
        """Test creating snapshot from dictionary."""
        data = {
            'run_timestamp': "2025-09-26T10:30:45.123456",
            'videos_on_disk': 100,
            'videos_in_subscriptions': 25,
            'new_videos_added': 10,
            'total_activities': 12
        }
        
        snapshot = RunSnapshot.from_dict(data)
        assert snapshot.run_timestamp == data['run_timestamp']
        assert snapshot.videos_on_disk == 100
        assert snapshot.total_activities == 12
    
    def test_from_dict_missing_optional_fields(self):
        """Test creating snapshot from dict with missing optional fields."""
        data = {
            'run_timestamp': "2025-09-26T10:30:45.123456"
        }
        
        snapshot = RunSnapshot.from_dict(data)
        assert snapshot.run_timestamp == data['run_timestamp']
        assert snapshot.videos_on_disk == 0
        assert snapshot.videos_in_subscriptions == 0


class TestRunMetrics:
    """Tests for RunMetrics."""
    
    def test_creation(self):
        """Test creating run metrics."""
        metrics = RunMetrics()
        
        assert metrics.run_id is not None
        assert metrics.start_time is not None
        assert metrics.end_time is None
        assert metrics.success is True
        assert metrics.error_message is None
        
        # Verify all stage metrics exist
        assert isinstance(metrics.directory_repair, DirectoryRepairMetrics)
        assert isinstance(metrics.existing_episodes, ExistingEpisodesMetrics)
        assert isinstance(metrics.web_scraping, WebScrapingMetrics)
        assert isinstance(metrics.subscription_changes, SubscriptionChangesMetrics)
        assert isinstance(metrics.subscription_history, SubscriptionHistoryMetrics)
    
    def test_finalize_success(self):
        """Test finalizing with success."""
        metrics = RunMetrics()
        assert metrics.end_time is None
        
        metrics.finalize(success=True)
        
        assert metrics.end_time is not None
        assert metrics.success is True
        assert metrics.error_message is None
    
    def test_finalize_failure(self):
        """Test finalizing with failure."""
        metrics = RunMetrics()
        
        metrics.finalize(success=False, error_message="Test error")
        
        assert metrics.end_time is not None
        assert metrics.success is False
        assert metrics.error_message == "Test error"
    
    def test_to_dict(self):
        """Test dictionary conversion."""
        metrics = RunMetrics()
        metrics.directory_repair.total_episodes_scanned = 100
        metrics.existing_episodes.total_activities = 12
        metrics.finalize(success=True)
        
        data = metrics.to_dict()
        
        assert 'run_id' in data
        assert 'start_time' in data
        assert 'end_time' in data
        assert data['success'] is True
        assert 'directory_repair' in data
        assert data['directory_repair']['total_episodes_scanned'] == 100
        assert data['existing_episodes']['total_activities'] == 12
    
    def test_to_json(self):
        """Test JSON conversion."""
        metrics = RunMetrics()
        metrics.directory_repair.total_episodes_scanned = 100
        
        json_str = metrics.to_json()
        data = json.loads(json_str)
        
        assert 'run_id' in data
        assert data['directory_repair']['total_episodes_scanned'] == 100
    
    def test_get_summary(self):
        """Test generating complete summary."""
        metrics = RunMetrics()
        metrics.directory_repair.total_episodes_scanned = 100
        metrics.existing_episodes.total_activities = 12
        metrics.web_scraping.total_activities_scraped = 2
        metrics.web_scraping.total_classes_added = 15
        metrics.finalize(success=True)
        
        summary = metrics.get_summary()
        
        assert "Run Summary" in summary
        assert metrics.run_id in summary
        assert "Directory Repair:" in summary
        assert "Existing Episodes:" in summary
        assert "Web Scraping:" in summary
        assert "100 episodes" in summary
        assert "12 activities" in summary
        assert "15 added" in summary
    
    def test_get_summary_with_error(self):
        """Test summary with error."""
        metrics = RunMetrics()
        metrics.finalize(success=False, error_message="Test error occurred")
        
        summary = metrics.get_summary()
        
        assert "ERROR: Test error occurred" in summary
    
    def test_get_pr_summary(self):
        """Test generating PR summary."""
        metrics = RunMetrics()
        metrics.existing_episodes.total_episodes_on_disk = 100
        metrics.existing_episodes.total_subscriptions_in_yaml = 20
        metrics.existing_episodes.total_activities = 12
        metrics.web_scraping.total_classes_added = 15
        metrics.web_scraping.total_classes_found = 25
        metrics.web_scraping.total_classes_skipped = 10
        metrics.web_scraping.class_limit_per_activity = 25
        metrics.web_scraping.page_scrolls_config = 10
        
        # Add activity breakdown
        metrics.web_scraping.activities['strength'] = ActivityScrapingStats(
            activity="strength",
            classes_found=15,
            classes_skipped=7,
            classes_added=8,
            status="completed"
        )
        metrics.web_scraping.activities['yoga'] = ActivityScrapingStats(
            activity="yoga",
            classes_found=10,
            classes_skipped=3,
            classes_added=7,
            status="completed"
        )
        
        metrics.subscription_changes.subscriptions_removed_already_downloaded = 5
        metrics.subscription_changes.subscriptions_removed_stale = 3
        
        pr_summary = metrics.get_pr_summary()
        
        assert "## Subscription Update Summary" in pr_summary
        assert metrics.run_id in pr_summary
        assert "### Configuration" in pr_summary
        assert "Class limit per activity:** 25" in pr_summary
        assert "Page scrolls:** 10" in pr_summary
        assert "Activities:** 2 scraped" in pr_summary
        assert "### Subscription File Summary" in pr_summary
        assert "Removed 5 because they were found on disk, 3 because they expired" in pr_summary
        assert "### Subscription File Activity Breakdown" in pr_summary
        assert "**strength:**" in pr_summary and "existing," in pr_summary and "added," in pr_summary and "total" in pr_summary
        assert "**yoga:**" in pr_summary and "existing," in pr_summary and "added," in pr_summary and "total" in pr_summary
        assert "After scraper updates, we are now tracking" in pr_summary
        assert "Episodes on disk:** 100" in pr_summary
        assert "Subscriptions in YAML:** 20" in pr_summary  # Just the final count, not double-counted
        assert "Activities with episodes on disk:** 12" in pr_summary
        assert "### Directory Validation" in pr_summary
    
    def test_get_pr_summary_no_new_classes(self):
        """Test PR summary when no new classes found."""
        metrics = RunMetrics()
        metrics.web_scraping.total_classes_added = 0
        
        pr_summary = metrics.get_pr_summary()
        
        assert "No new classes found" in pr_summary
    
    def test_get_pr_summary_with_directory_repairs(self):
        """Test PR summary with directory repairs."""
        metrics = RunMetrics()
        metrics.directory_repair.total_episodes_scanned = 100
        metrics.directory_repair.corrupted_locations_repaired = 5
        metrics.directory_repair.episode_conflicts_resolved = 2
        
        pr_summary = metrics.get_pr_summary()
        
        assert "### Directory Validation" in pr_summary
        assert "100 episodes" in pr_summary
        assert "5 corrupted locations repaired" in pr_summary
    
    def test_create_snapshot(self):
        """Test creating run snapshot."""
        metrics = RunMetrics()
        metrics.existing_episodes.total_episodes_on_disk = 100
        metrics.existing_episodes.total_subscriptions_in_yaml = 20
        metrics.existing_episodes.total_activities = 12
        metrics.web_scraping.total_classes_added = 15
        
        snapshot = metrics.create_snapshot()
        
        assert snapshot.run_timestamp == metrics.start_time
        assert snapshot.videos_on_disk == 100
        assert snapshot.videos_in_subscriptions == 35  # 20 + 15
        assert snapshot.new_videos_added == 15
        assert snapshot.total_activities == 12


class TestIntegration:
    """Integration tests for the metrics system."""
    
    def test_complete_workflow_metrics(self):
        """Test collecting metrics through a complete workflow."""
        metrics = RunMetrics()
        
        # Stage 1: Directory repair
        metrics.directory_repair.total_episodes_scanned = 100
        metrics.directory_repair.corrupted_locations_repaired = 3
        
        # Stage 2: Existing episodes
        metrics.existing_episodes.total_activities = 12
        metrics.existing_episodes.total_episodes_on_disk = 97
        metrics.existing_episodes.total_subscriptions_in_yaml = 20
        metrics.existing_episodes.existing_class_ids_count = 117
        
        # Stage 3: Web scraping
        metrics.web_scraping.total_activities_scraped = 3
        metrics.web_scraping.total_classes_found = 25
        metrics.web_scraping.total_classes_skipped = 10
        metrics.web_scraping.total_classes_added = 15
        
        # Stage 4: Subscription changes
        metrics.subscription_changes.subscriptions_removed_already_downloaded = 5
        metrics.subscription_changes.subscriptions_added_new = 15
        
        # Stage 5: Subscription history
        metrics.subscription_history.total_tracked_subscriptions = 127
        metrics.subscription_history.subscriptions_added_to_history = 15
        
        # Finalize
        metrics.finalize(success=True)
        
        # Verify summary
        summary = metrics.get_summary()
        assert "Run Summary" in summary
        assert "100 episodes" in summary
        assert "15 added" in summary
        
        # Verify PR summary
        pr_summary = metrics.get_pr_summary()
        assert "### Subscription File Summary" in pr_summary
        assert "Removed 5 because they were found on disk" in pr_summary
        
        # Verify snapshot
        snapshot = metrics.create_snapshot()
        assert snapshot.videos_on_disk == 97
        assert snapshot.new_videos_added == 15
        
        # Verify JSON serialization
        data = metrics.to_dict()
        assert data['success'] is True
        assert data['directory_repair']['total_episodes_scanned'] == 100

