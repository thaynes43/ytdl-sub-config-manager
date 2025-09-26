"""Additional tests for Application class to verify subscriptions count excludes disk files."""

from unittest.mock import patch, MagicMock

from src.core.application import Application
from src.core.models import Activity, ActivityData


class TestApplicationSubscriptionsCount:
    """Test that subscriptions count excludes files already on disk."""

    @patch('src.core.application.FileManager')
    @patch('src.webscraper.scraper_factory.ScraperFactory')
    def test_subscriptions_count_excludes_disk_files(self, mock_scraper_factory, mock_file_manager_class):
        """Test that subscriptions count excludes files already on disk."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = ['strategy1']
        mock_config.peloton_directory_repair_strategies = ['repair1']
        mock_config.peloton_episode_parsers = ['parser1']
        mock_config.skip_validation = False
        mock_config.scrapers = {
            'peloton.com': {
                'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
                'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
                'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
            }
        }
        mock_config.peloton_activities = [Activity.CYCLING]
        mock_config.peloton_class_limit_per_activity = 25
        mock_config.peloton_page_scrolls = 10
        mock_config.github_repo_url = ""
        mock_config.github_token = ""

        # Setup mock file manager
        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        # Mock merged data (includes disk + subscriptions) - has many episodes on disk
        merged_activity_data = ActivityData(activity=Activity.CYCLING)
        merged_activity_data.max_episode = {20: 100, 30: 150}  # 250 total episodes (disk + subscriptions)
        merged_data = {Activity.CYCLING: merged_activity_data}
        mock_file_manager.get_merged_episode_data.return_value = merged_data

        # Mock subscriptions data BEFORE cleanup (includes already-downloaded classes)
        subscriptions_before_cleanup = ActivityData(activity=Activity.CYCLING)
        subscriptions_before_cleanup.max_episode = {20: 80, 30: 120}  # 200 episodes in subscriptions (before cleanup)
        subscriptions_data_before = {Activity.CYCLING: subscriptions_before_cleanup}

        # Mock subscriptions data AFTER cleanup (only classes not yet downloaded)
        subscriptions_after_cleanup = ActivityData(activity=Activity.CYCLING)
        subscriptions_after_cleanup.max_episode = {20: 5, 30: 10}  # 15 episodes in subscriptions (after cleanup)
        subscriptions_data_after = {Activity.CYCLING: subscriptions_after_cleanup}

        # Configure get_subscriptions_episode_data to return different data on each call
        mock_file_manager.get_subscriptions_episode_data.side_effect = [
            subscriptions_data_before,  # First call (before cleanup)
            subscriptions_data_after    # Second call (after cleanup)
        ]

        mock_file_manager.find_all_existing_class_ids.return_value = {'id1', 'id2', 'id3'}
        mock_file_manager.cleanup_subscriptions.return_value = True
        mock_file_manager.add_new_subscriptions.return_value = None

        # Setup mock scraper manager
        mock_scraper_manager = MagicMock()
        mock_scraper_manager.scrape_activities.return_value = {}
        mock_scraper_factory.create_scraper.return_value = mock_scraper_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0

        # Verify that get_subscriptions_episode_data was called twice
        assert mock_file_manager.get_subscriptions_episode_data.call_count == 2

        # Verify that cleanup_subscriptions was called between the two calls
        mock_file_manager.cleanup_subscriptions.assert_called_once()

        # Verify the call order: first get_subscriptions, then cleanup, then get_subscriptions again
        calls = mock_file_manager.get_subscriptions_episode_data.call_args_list
        cleanup_calls = mock_file_manager.cleanup_subscriptions.call_args_list
        
        # The first call should happen before cleanup
        # The second call should happen after cleanup
        # This verifies that we're using the cleaned data for the final count
        assert len(calls) == 2
        assert len(cleanup_calls) == 1

    @patch('src.core.application.FileManager')
    @patch('src.webscraper.scraper_factory.ScraperFactory')
    def test_subscriptions_count_zero_after_cleanup(self, mock_scraper_factory, mock_file_manager_class):
        """Test that subscriptions count is zero when all classes are already downloaded."""
        # Setup mock config
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = ['strategy1']
        mock_config.peloton_directory_repair_strategies = ['repair1']
        mock_config.peloton_episode_parsers = ['parser1']
        mock_config.skip_validation = False
        mock_config.scrapers = {
            'peloton.com': {
                'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
                'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
                'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
            }
        }
        mock_config.peloton_activities = [Activity.CYCLING]
        mock_config.peloton_class_limit_per_activity = 25
        mock_config.peloton_page_scrolls = 10
        mock_config.github_repo_url = ""
        mock_config.github_token = ""

        # Setup mock file manager
        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        # Mock merged data (includes disk + subscriptions)
        merged_activity_data = ActivityData(activity=Activity.CYCLING)
        merged_activity_data.max_episode = {20: 50, 30: 75}  # 125 total episodes (disk + subscriptions)
        merged_data = {Activity.CYCLING: merged_activity_data}
        mock_file_manager.get_merged_episode_data.return_value = merged_data

        # Mock subscriptions data BEFORE cleanup (has some episodes)
        subscriptions_before_cleanup = ActivityData(activity=Activity.CYCLING)
        subscriptions_before_cleanup.max_episode = {20: 20, 30: 30}  # 50 episodes in subscriptions (before cleanup)
        subscriptions_data_before = {Activity.CYCLING: subscriptions_before_cleanup}

        # Mock subscriptions data AFTER cleanup (all classes already downloaded, so empty)
        subscriptions_after_cleanup = ActivityData(activity=Activity.CYCLING)
        subscriptions_after_cleanup.max_episode = {}  # 0 episodes in subscriptions (after cleanup)
        subscriptions_data_after = {Activity.CYCLING: subscriptions_after_cleanup}

        # Configure get_subscriptions_episode_data to return different data on each call
        mock_file_manager.get_subscriptions_episode_data.side_effect = [
            subscriptions_data_before,  # First call (before cleanup)
            subscriptions_data_after    # Second call (after cleanup)
        ]

        mock_file_manager.find_all_existing_class_ids.return_value = {'id1', 'id2', 'id3'}
        mock_file_manager.cleanup_subscriptions.return_value = True
        mock_file_manager.add_new_subscriptions.return_value = None

        # Setup mock scraper manager
        mock_scraper_manager = MagicMock()
        mock_scraper_manager.scrape_activities.return_value = {}
        mock_scraper_factory.create_scraper.return_value = mock_scraper_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0

        # Verify that get_subscriptions_episode_data was called twice
        assert mock_file_manager.get_subscriptions_episode_data.call_count == 2

        # Verify that cleanup_subscriptions was called between the two calls
        mock_file_manager.cleanup_subscriptions.assert_called_once()

        # Verify the call order: first get_subscriptions, then cleanup, then get_subscriptions again
        calls = mock_file_manager.get_subscriptions_episode_data.call_args_list
        cleanup_calls = mock_file_manager.cleanup_subscriptions.call_args_list
        
        # The first call should happen before cleanup
        # The second call should happen after cleanup
        # This verifies that we're using the cleaned data for the final count
        assert len(calls) == 2
        assert len(cleanup_calls) == 1

    @patch('src.core.application.FileManager')
    @patch('src.webscraper.scraper_factory.ScraperFactory')
    def test_subscriptions_count_multiple_activities(self, mock_scraper_factory, mock_file_manager_class):
        """Test that subscriptions count is calculated correctly for multiple activities."""
        # Setup mock config with multiple activities
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = ['strategy1']
        mock_config.peloton_directory_repair_strategies = ['repair1']
        mock_config.peloton_episode_parsers = ['parser1']
        mock_config.skip_validation = False
        mock_config.scrapers = {
            'peloton.com': {
                'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
                'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
                'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
            }
        }
        mock_config.peloton_activities = [Activity.CYCLING, Activity.STRENGTH]
        mock_config.peloton_class_limit_per_activity = 25
        mock_config.peloton_page_scrolls = 10
        mock_config.github_repo_url = ""
        mock_config.github_token = ""

        # Setup mock file manager
        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        # Mock merged data for both activities
        cycling_merged = ActivityData(activity=Activity.CYCLING)
        cycling_merged.max_episode = {20: 100, 30: 150}  # 250 total episodes
        strength_merged = ActivityData(activity=Activity.STRENGTH)
        strength_merged.max_episode = {20: 50, 30: 75}   # 125 total episodes
        merged_data = {Activity.CYCLING: cycling_merged, Activity.STRENGTH: strength_merged}
        mock_file_manager.get_merged_episode_data.return_value = merged_data

        # Mock subscriptions data AFTER cleanup (only classes not yet downloaded)
        cycling_subscriptions = ActivityData(activity=Activity.CYCLING)
        cycling_subscriptions.max_episode = {20: 5, 30: 10}  # 15 episodes in subscriptions (after cleanup)
        strength_subscriptions = ActivityData(activity=Activity.STRENGTH)
        strength_subscriptions.max_episode = {20: 3, 30: 7}   # 10 episodes in subscriptions (after cleanup)
        subscriptions_data_after = {Activity.CYCLING: cycling_subscriptions, Activity.STRENGTH: strength_subscriptions}

        # Configure get_subscriptions_episode_data to return the same data twice (after cleanup)
        mock_file_manager.get_subscriptions_episode_data.return_value = subscriptions_data_after

        mock_file_manager.find_all_existing_class_ids.return_value = {'id1', 'id2', 'id3'}
        mock_file_manager.cleanup_subscriptions.return_value = True
        mock_file_manager.add_new_subscriptions.return_value = None

        # Setup mock scraper manager
        mock_scraper_manager = MagicMock()
        mock_scraper_manager.scrape_activities.return_value = {}
        mock_scraper_factory.create_scraper.return_value = mock_scraper_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0

        # Verify that get_subscriptions_episode_data was called twice
        assert mock_file_manager.get_subscriptions_episode_data.call_count == 2

        # Verify that cleanup_subscriptions was called between the two calls
        mock_file_manager.cleanup_subscriptions.assert_called_once()

        # Verify the call order: first get_subscriptions, then cleanup, then get_subscriptions again
        calls = mock_file_manager.get_subscriptions_episode_data.call_args_list
        cleanup_calls = mock_file_manager.cleanup_subscriptions.call_args_list
        
        # The first call should happen before cleanup
        # The second call should happen after cleanup
        # This verifies that we're using the cleaned data for the final count
        assert len(calls) == 2
        assert len(cleanup_calls) == 1

    @patch('src.core.application.FileManager')
    @patch('src.webscraper.scraper_factory.ScraperFactory')
    def test_subscriptions_count_uses_actual_class_ids_not_max_episodes(self, mock_scraper_factory, mock_file_manager_class):
        """Test that subscriptions count uses actual class IDs, not max episode numbers.
        
        This test specifically catches the bug where we were using sum(max_episode.values())
        instead of counting actual class IDs in subscriptions.
        """
        # Setup mock config
        mock_config = MagicMock()
        mock_config.media_dir = '/test/media'
        mock_config.subs_file = '/test/subs.yaml'
        mock_config.peloton_directory_validation_strategies = ['strategy1']
        mock_config.peloton_directory_repair_strategies = ['repair1']
        mock_config.peloton_episode_parsers = ['parser1']
        mock_config.skip_validation = False
        mock_config.scrapers = {
            'peloton.com': {
                'login_strategy': 'src.webscraper.peloton.login_strategy:PelotonLoginStrategy',
                'session_manager': 'src.webscraper.session_manager:GenericSessionManager',
                'scraper_strategy': 'src.webscraper.peloton.scraper_strategy:PelotonScraperStrategy'
            }
        }
        mock_config.peloton_activities = [Activity.CYCLING]
        mock_config.peloton_class_limit_per_activity = 25
        mock_config.peloton_page_scrolls = 10
        mock_config.github_repo_url = ""
        mock_config.github_token = ""

        # Setup mock file manager
        mock_file_manager = MagicMock()
        mock_file_manager_class.return_value = mock_file_manager

        # Mock merged data
        merged_activity_data = ActivityData(activity=Activity.CYCLING)
        merged_activity_data.max_episode = {20: 100, 30: 150}
        merged_data = {Activity.CYCLING: merged_activity_data}
        mock_file_manager.get_merged_episode_data.return_value = merged_data

        # Mock subscriptions data with HIGH max episode numbers
        # This simulates the bug scenario: max episodes are high but actual class count is low
        subscriptions_after_cleanup = ActivityData(activity=Activity.CYCLING)
        subscriptions_after_cleanup.max_episode = {20: 499, 30: 500}  # VERY high max episodes (sum = 999)
        subscriptions_data_after = {Activity.CYCLING: subscriptions_after_cleanup}
        mock_file_manager.get_subscriptions_episode_data.return_value = subscriptions_data_after

        # Create a mock subscription parser that returns the ACTUAL class count (not max episodes)
        mock_subscription_parser = MagicMock()
        mock_subscription_parser.__class__.__name__ = 'EpisodesFromSubscriptions'
        mock_subscription_parser.find_subscription_class_ids_for_activity.return_value = {'id1', 'id2', 'id3'}  # Only 3 actual classes
        
        # Setup the episode manager to return our mock parser
        mock_file_manager.episode_manager.episode_parsers = [mock_subscription_parser]

        mock_file_manager.find_all_existing_class_ids.return_value = set()
        mock_file_manager.cleanup_subscriptions.return_value = True
        mock_file_manager.add_new_subscriptions.return_value = None

        # Setup mock scraper manager
        mock_scraper_manager = MagicMock()
        mock_scraper_manager.scrape_activities.return_value = {}
        mock_scraper_factory.create_scraper.return_value = mock_scraper_manager

        app = Application()
        result = app.run_scrape_command(mock_config)

        assert result == 0

        # Verify that find_subscription_class_ids_for_activity was called to get the actual count
        mock_subscription_parser.find_subscription_class_ids_for_activity.assert_called_once_with(Activity.CYCLING)
        
        # This test would have caught the bug: we should use actual class count (3)
        # NOT sum of max episodes (499 + 500 = 999)