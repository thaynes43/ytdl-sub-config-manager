"""Tests for the subscription summary fix."""

import pytest
from src.core.metrics import RunMetrics, SubscriptionChangesMetrics, WebScrapingMetrics, ActivityScrapingStats


class TestSubscriptionSummaryFix:
    """Test that the subscription summary shows correct counts without deltas."""
    
    def test_subscription_summary_shows_correct_counts_and_deltas(self):
        """Test that the subscription summary shows YAML subscriptions with correct counts."""
        run_metrics = RunMetrics()
        
        # Set up subscription changes with actual subscription counts
        run_metrics.subscription_changes.subscriptions_after_cleanup_by_activity = {
            "cycling": 25,
            "strength": 30,
            "walking": 20
        }
        
        # Set up web scraping activities with added counts
        run_metrics.web_scraping.activities = {
            "cycling": ActivityScrapingStats(
                activity="cycling",
                classes_found=10,
                classes_skipped=5,
                classes_added=3,  # 3 new classes added
                errors=0,
                scrolls_performed=2,
                status="completed"
            ),
            "strength": ActivityScrapingStats(
                activity="strength",
                classes_found=8,
                classes_skipped=2,
                classes_added=0,  # No new classes added
                errors=0,
                scrolls_performed=1,
                status="completed"
            ),
            "walking": ActivityScrapingStats(
                activity="walking",
                classes_found=5,
                classes_skipped=1,
                classes_added=2,  # 2 new classes added
                errors=0,
                scrolls_performed=1,
                status="completed"
            )
        }
        
        # Set up total subscriptions (final counts after scraping)
        run_metrics.subscription_changes.subscriptions_after_cleanup = 80  # 28 + 30 + 22
        run_metrics.existing_episodes.total_subscriptions_in_yaml = 80  # Total subscriptions in YAML
        
        pr_summary = run_metrics.get_pr_summary()
        
        # Check that the summary shows correct final counts (existing + added)
        assert "**Subscriptions in YAML:** 80" in pr_summary
        assert "  - cycling: 28 subscriptions" in pr_summary  # 25 + 3
        assert "  - strength: 30 subscriptions" in pr_summary  # 30 + 0
        assert "  - walking: 22 subscriptions" in pr_summary  # 20 + 2
    
    def test_subscription_summary_shows_correct_counts_after_removal(self):
        """Test that the subscription summary shows correct counts when classes are removed."""
        run_metrics = RunMetrics()
        
        # Set up subscription changes with actual subscription counts
        run_metrics.subscription_changes.subscriptions_after_cleanup_by_activity = {
            "cycling": 22,  # Reduced from 25
            "strength": 30
        }
        
        # Set up web scraping activities with negative added counts (classes removed)
        run_metrics.web_scraping.activities = {
            "cycling": ActivityScrapingStats(
                activity="cycling",
                classes_found=0,
                classes_skipped=0,
                classes_added=-3,  # 3 classes removed
                errors=0,
                scrolls_performed=0,
                status="completed"
            ),
            "strength": ActivityScrapingStats(
                activity="strength",
                classes_found=0,
                classes_skipped=0,
                classes_added=0,  # No change
                errors=0,
                scrolls_performed=0,
                status="completed"
            )
        }
        
        # Set up total subscriptions (final counts after scraping)
        run_metrics.subscription_changes.subscriptions_after_cleanup = 49  # 19 + 30
        run_metrics.existing_episodes.total_subscriptions_in_yaml = 49  # Total subscriptions in YAML
        
        pr_summary = run_metrics.get_pr_summary()
        
        # Check that the summary shows correct final counts (existing + added)
        assert "**Subscriptions in YAML:** 49" in pr_summary
        assert "  - cycling: 19 subscriptions" in pr_summary  # 22 + (-3)
        assert "  - strength: 30 subscriptions" in pr_summary  # 30 + 0
    
    def test_subscription_summary_handles_empty_activities(self):
        """Test that the subscription summary handles activities with no subscriptions."""
        run_metrics = RunMetrics()
        
        # Set up subscription changes with some activities having 0 subscriptions
        run_metrics.subscription_changes.subscriptions_after_cleanup_by_activity = {
            "cycling": 0,  # No subscriptions
            "strength": 15
        }
        
        # Set up web scraping activities
        run_metrics.web_scraping.activities = {
            "cycling": ActivityScrapingStats(
                activity="cycling",
                classes_found=0,
                classes_skipped=0,
                classes_added=0,
                errors=0,
                scrolls_performed=0,
                status="completed"
            ),
            "strength": ActivityScrapingStats(
                activity="strength",
                classes_found=5,
                classes_skipped=2,
                classes_added=3,
                errors=0,
                scrolls_performed=1,
                status="completed"
            )
        }
        
        # Set up total subscriptions (final counts after scraping)
        run_metrics.subscription_changes.subscriptions_after_cleanup = 18  # 0 + 18
        run_metrics.existing_episodes.total_subscriptions_in_yaml = 18  # Total subscriptions in YAML
        
        pr_summary = run_metrics.get_pr_summary()
        
        # Check that the summary shows correct final counts including 0
        assert "**Subscriptions in YAML:** 18" in pr_summary
        assert "  - cycling: 0 subscriptions" in pr_summary  # 0 + 0
        assert "  - strength: 18 subscriptions" in pr_summary  # 15 + 3
    
    def test_subscription_summary_handles_missing_web_scraping_data(self):
        """Test that the summary handles missing web scraping data gracefully."""
        run_metrics = RunMetrics()
        
        # Set up subscription changes
        run_metrics.subscription_changes.subscriptions_after_cleanup_by_activity = {
            "cycling": 25,
            "strength": 30
        }
        
        # Don't set up web scraping activities (simulating no scraping run)
        run_metrics.web_scraping.activities = {}
        
        # Set up total subscriptions
        run_metrics.subscription_changes.subscriptions_after_cleanup = 55  # 25 + 30
        run_metrics.existing_episodes.total_subscriptions_in_yaml = 55  # Total subscriptions in YAML
        
        pr_summary = run_metrics.get_pr_summary()
        
        # Check that the summary shows correct counts without deltas when no scraping data
        assert "**Subscriptions in YAML:** 55" in pr_summary
        assert "  - cycling: 25 subscriptions" in pr_summary
        assert "  - strength: 30 subscriptions" in pr_summary
