"""Tests for dynamic scrolling configuration in metrics."""

import pytest
from src.core.metrics import WebScrapingMetrics, RunMetrics


class TestDynamicScrollingMetrics:
    """Test dynamic scrolling configuration in metrics."""
    
    def test_web_scraping_metrics_dynamic_scrolling_defaults(self):
        """Test that WebScrapingMetrics has correct defaults for dynamic scrolling."""
        metrics = WebScrapingMetrics()
        
        assert metrics.dynamic_scrolling_enabled is False
        assert metrics.max_scrolls_config == 0
    
    def test_web_scraping_metrics_dynamic_scrolling_custom_values(self):
        """Test that WebScrapingMetrics accepts custom dynamic scrolling values."""
        metrics = WebScrapingMetrics(
            dynamic_scrolling_enabled=True,
            max_scrolls_config=100
        )
        
        assert metrics.dynamic_scrolling_enabled is True
        assert metrics.max_scrolls_config == 100
    
    def test_web_scraping_metrics_to_dict_includes_dynamic_scrolling(self):
        """Test that to_dict includes dynamic scrolling fields."""
        metrics = WebScrapingMetrics(
            dynamic_scrolling_enabled=True,
            max_scrolls_config=75
        )
        
        data = metrics.to_dict()
        
        assert 'dynamic_scrolling_enabled' in data
        assert 'max_scrolls_config' in data
        assert data['dynamic_scrolling_enabled'] is True
        assert data['max_scrolls_config'] == 75
    
    def test_web_scraping_metrics_summary_with_dynamic_scrolling(self):
        """Test that get_summary includes dynamic scrolling information."""
        metrics = WebScrapingMetrics(
            total_activities_scraped=3,
            total_classes_found=15,
            dynamic_scrolling_enabled=True,
            max_scrolls_config=50
        )
        
        summary = metrics.get_summary()
        
        assert "dynamic_scrolling=true" in summary
        assert "max_scrolls=50" in summary
        assert "page_scrolls=" not in summary
    
    def test_web_scraping_metrics_summary_without_dynamic_scrolling(self):
        """Test that get_summary includes page_scrolls when dynamic scrolling is disabled."""
        metrics = WebScrapingMetrics(
            total_activities_scraped=3,
            total_classes_found=15,
            dynamic_scrolling_enabled=False,
            page_scrolls_config=10
        )
        
        summary = metrics.get_summary()
        
        assert "page_scrolls=10" in summary
        assert "dynamic_scrolling=" not in summary
        assert "max_scrolls=" not in summary
    
    def test_run_metrics_pr_summary_includes_dynamic_scrolling_config(self):
        """Test that PR summary includes dynamic scrolling configuration."""
        # Create a RunMetrics with dynamic scrolling enabled
        run_metrics = RunMetrics()
        run_metrics.web_scraping.dynamic_scrolling_enabled = True
        run_metrics.web_scraping.max_scrolls_config = 50
        run_metrics.web_scraping.page_scrolls_config = 10
        run_metrics.web_scraping.class_limit_per_activity = 25
        
        pr_summary = run_metrics.get_pr_summary()
        
        # Check that the configuration section includes dynamic scrolling
        assert "### Configuration" in pr_summary
        assert "**Dynamic scrolling:** True" in pr_summary
        assert "**Max scrolls:** 50" in pr_summary
        assert "**Page scrolls:** 10" not in pr_summary  # Should not show when dynamic scrolling is enabled
        assert "**Class limit per activity:** 25" in pr_summary
    
    def test_run_metrics_pr_summary_without_dynamic_scrolling_config(self):
        """Test that PR summary shows dynamic scrolling as False when disabled."""
        # Create a RunMetrics with dynamic scrolling disabled
        run_metrics = RunMetrics()
        run_metrics.web_scraping.dynamic_scrolling_enabled = False
        run_metrics.web_scraping.max_scrolls_config = 0
        run_metrics.web_scraping.page_scrolls_config = 10
        run_metrics.web_scraping.class_limit_per_activity = 25
        
        pr_summary = run_metrics.get_pr_summary()
        
        # Check that the configuration section shows dynamic scrolling as False
        assert "### Configuration" in pr_summary
        assert "**Dynamic scrolling:** False" in pr_summary
        assert "**Max scrolls:** 0" not in pr_summary  # Should not show when dynamic scrolling is disabled
        assert "**Page scrolls:** 10" in pr_summary
        assert "**Class limit per activity:** 25" in pr_summary
