"""Tests for scroll count tracking in metrics."""

import pytest
from src.core.metrics import ActivityScrapingStats, RunMetrics
from src.webscraper.models import ScrapingResult, ScrapingStatus


class TestScrollCountMetrics:
    """Test scroll count tracking in metrics."""
    
    def test_activity_scraping_stats_includes_scrolls_performed(self):
        """Test that ActivityScrapingStats includes scrolls_performed field."""
        stats = ActivityScrapingStats(
            activity="cycling",
            classes_found=10,
            classes_skipped=2,
            classes_added=8,
            errors=0,
            scrolls_performed=5,
            status="completed"
        )
        
        assert stats.scrolls_performed == 5
        
        # Test serialization
        data = stats.to_dict()
        assert 'scrolls_performed' in data
        assert data['scrolls_performed'] == 5
    
    def test_scraping_result_includes_scrolls_performed(self):
        """Test that ScrapingResult includes scrolls_performed field."""
        result = ScrapingResult(
            activity="cycling",
            classes=[],
            total_found=10,
            total_skipped=2,
            total_errors=0,
            status=ScrapingStatus.COMPLETED,
            scrolls_performed=7
        )
        
        assert result.scrolls_performed == 7
    
    def test_pr_summary_includes_scroll_count_in_activity_breakdown(self):
        """Test that PR summary includes scroll count in activity breakdown."""
        run_metrics = RunMetrics()
        
        # Set up activity stats with scroll count
        activity_stats = ActivityScrapingStats(
            activity="cycling",
            classes_found=54,
            classes_skipped=0,
            classes_added=1,
            errors=0,
            scrolls_performed=3,
            status="completed"
        )
        
        run_metrics.web_scraping.activities["cycling"] = activity_stats
        run_metrics.web_scraping.total_classes_added = 1
        
        pr_summary = run_metrics.get_pr_summary()
        
        # Check that the activity breakdown includes scroll count
        assert "### Subscription File Activity Breakdown" in pr_summary
        assert "**cycling:**" in pr_summary
        assert "(54 scraped, 0 skipped by scraper, 3 scrolls)" in pr_summary
    
    def test_pr_summary_shows_zero_scrolls_when_no_scraping_activity(self):
        """Test that PR summary shows 0 scrolls when there was no scraping activity."""
        run_metrics = RunMetrics()
        
        # Set up activity stats with no classes found (no scraping activity)
        activity_stats = ActivityScrapingStats(
            activity="cycling",
            classes_found=0,
            classes_skipped=0,
            classes_added=0,
            errors=0,
            scrolls_performed=5,  # This should not be shown since classes_found=0
            status="completed"
        )
        
        run_metrics.web_scraping.activities["cycling"] = activity_stats
        run_metrics.web_scraping.total_classes_added = 1  # Need at least 1 to show activity breakdown
        
        # Set up subscription changes to include cycling activity
        run_metrics.subscription_changes.subscriptions_after_cleanup_by_activity["cycling"] = 1
        
        pr_summary = run_metrics.get_pr_summary()
        
        # Check that scroll count is not shown when there was no scraping activity
        assert "### Subscription File Activity Breakdown" in pr_summary
        assert "**cycling:**" in pr_summary
        assert "(0 scraped, 0 skipped by scraper, 5 scrolls)" not in pr_summary
        assert "scraped, 0 skipped by scraper)" not in pr_summary  # Should not show scraping details at all
    
    def test_pr_summary_handles_missing_activity_stats(self):
        """Test that PR summary handles missing activity stats gracefully."""
        run_metrics = RunMetrics()
        
        # Don't set up any activity stats
        run_metrics.web_scraping.total_classes_added = 1
        
        pr_summary = run_metrics.get_pr_summary()
        
        # Should not crash and should handle missing stats gracefully
        assert "### Subscription File Activity Breakdown" in pr_summary
