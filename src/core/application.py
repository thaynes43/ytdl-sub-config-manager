"""Main application logic for ytdl-sub config manager."""

import argparse
from typing import Dict, Any

from ..io.file_manager import FileManager
from ..io.generic_directory_validator import GenericDirectoryValidator
from ..git_integration.subscription_manager import SubscriptionManager
from .logging import get_logger
from .metrics import RunMetrics, ActivityEpisodeStats, ActivityScrapingStats, SeasonStats

logger = get_logger(__name__)


class Application:
    """Main application class that orchestrates the scraping workflow."""
    
    def __init__(self):
        pass
    
    def _setup_file_logging(self, config) -> None:
        """Set up file logging if configured.
        
        Args:
            config: Configuration object with logging settings
        """
        if hasattr(config, 'log_file') and config.log_file:
            from ..core.logging import setup_logging
            
            # Reconfigure logging with file options
            setup_logging(
                level=config.log_level,
                format_type=config.log_format,
                log_file=config.log_file,
                max_file_size_mb=config.log_max_file_size_mb,
                backup_count=config.log_backup_count
            )
    
    def run(self, args: argparse.Namespace) -> int:
        """Run the application with parsed arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            if args.command == "scrape":
                # Load full configuration for scrape command
                from ..config import ConfigLoader
                from ..config.cli_config import CLIConfigManager
                
                cli_manager = CLIConfigManager()
                cli_config = cli_manager.args_to_config_dict(args)
                
                config_loader = ConfigLoader()
                config = config_loader.load_config(
                    config_file=args.config,
                    cli_args=cli_config
                )
                
                # Reconfigure logging with file options if specified
                self._setup_file_logging(config)
                
                return self.run_scrape_command(config)
                
            elif args.command == "validate":
                # Validate command doesn't need full config
                return self.run_validate_command(args)
                
            else:
                logger.error(f"Unknown command: {args.command}")
                return 1
                
        except Exception as e:
            logger.error(f"Application error: {e}")
            return 1
    
    def run_scrape_command(self, config) -> int:
        """Run the scrape command with the given configuration.
        
        Args:
            config: Configuration object
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        from pathlib import Path
        from ..io.subscription_history_manager import SubscriptionHistoryManager
        
        # Create metrics collector
        metrics = RunMetrics()
        metrics.subscription_timeout_days = config.subscription_timeout_days
        
        try:
            logger.info("Starting Peloton scraping workflow...")
            
            # Log the configuration
            config.log_config()
            
            # Initialize GitHub integration if configured
            github_manager = None
            if config.github_repo_url and config.github_token:
                logger.info("GitHub integration enabled - setting up repository")
                github_manager = SubscriptionManager.create_from_config(
                    repo_url=config.github_repo_url,
                    token=config.github_token,
                    subs_file_path=config.subs_file,
                    auto_merge=config.github_auto_merge,
                    temp_repo_dir=config.temp_repo_dir
                )
                
                # Bootstrap the repository
                setup_result = github_manager.setup_repository()
                if not setup_result.success:
                    logger.error(f"Failed to setup GitHub repository: {setup_result.message}")
                    return 1
                
                # Validate that the subscriptions file exists
                if not github_manager.validate_subscriptions_file():
                    logger.error("Subscriptions file validation failed")
                    github_manager.cleanup()
                    return 1
            else:
                # Log why GitHub integration is disabled
                if not config.github_repo_url and not config.github_token:
                    logger.info("GitHub integration disabled - no repository URL or token configured")
                elif not config.github_repo_url:
                    logger.info("GitHub integration disabled - no repository URL configured")
                elif not config.github_token:
                    logger.info("GitHub integration disabled - no GitHub token configured")
            
            # Load previous run snapshot for comparison (AFTER repo is cloned if using GitHub)
            previous_snapshot = None
            try:
                history_file = Path(config.subs_file).parent / "subscription-history.json"
                if history_file.exists():
                    temp_history = SubscriptionHistoryManager(config.subs_file, config.subscription_timeout_days, config.history_retention_days)
                    previous_snapshot = temp_history.get_last_run_snapshot()
                    if previous_snapshot:
                        logger.info(f"Loaded previous run snapshot from {previous_snapshot.run_timestamp}")
                        metrics.existing_episodes.total_episodes_on_disk_previous = previous_snapshot.videos_on_disk
                        metrics.existing_episodes.total_subscriptions_in_yaml_previous = previous_snapshot.videos_in_subscriptions
                        metrics.web_scraping.total_classes_found_previous = previous_snapshot.new_videos_added
                        # Store previous snapshot for detailed change tracking
                        metrics.existing_episodes.previous_snapshot = previous_snapshot
            except Exception as e:
                logger.warning(f"Could not load previous run snapshot: {e}")
            
            # Initialize file manager (with validation unless skipped)
            skip_validation = getattr(config, 'skip_validation', False)
            file_manager = FileManager(
                media_dir=config.media_dir,
                subs_file=config.subs_file,
                validate_and_repair=not skip_validation,
                validation_strategies=config.peloton_directory_validation_strategies,
                repair_strategies=config.peloton_directory_repair_strategies,
                episode_parsers=config.peloton_episode_parsers,
                subscription_timeout_days=config.subscription_timeout_days,
                history_retention_days=config.history_retention_days,
                metrics=metrics
            )
            
            # Get disk-only episode data for accurate disk count
            logger.info("Analyzing current episode data...")
            disk_data = file_manager.get_disk_episode_data()
            logger.info(f"Found {len(disk_data)} activities with episodes on disk.")
            
            # Collect existing episodes metrics from disk data
            metrics.existing_episodes.total_activities = len(disk_data)
            total_disk_episodes = 0
            for activity, activity_data in disk_data.items():
                # Use actual episode counts, not max episode numbers
                episode_count = sum(activity_data.episode_count.values())
                total_disk_episodes += episode_count
                
                # Create season stats with actual episode counts and highest episode numbers
                season_stats = {}
                for season in activity_data.max_episode.keys():
                    actual_count = activity_data.episode_count.get(season, 0)
                    highest_episode = activity_data.max_episode.get(season, 0)
                    season_stats[season] = SeasonStats(
                        season=season,
                        episode_count=actual_count,
                        highest_episode_number=highest_episode
                    )
                
                # Store activity stats
                activity_stats = ActivityEpisodeStats(
                    activity=activity.name,
                    total_episodes=episode_count,
                    seasons=season_stats
                )
                metrics.existing_episodes.activities[activity.name] = activity_stats
            
            metrics.existing_episodes.total_episodes_on_disk = total_disk_episodes
            logger.info(f"Total episodes on disk: {total_disk_episodes}")
            
            # Get subscriptions-only data for counting classes in subscriptions.yaml
            subscriptions_data = file_manager.get_subscriptions_episode_data()
            logger.info(f"Found {len(subscriptions_data)} activities with classes in subscriptions.")
            
            subscription_count = sum(
                sum(activity_data.episode_count.values()) 
                for activity_data in subscriptions_data.values()
            )
            metrics.existing_episodes.total_subscriptions_in_yaml = subscription_count
            metrics.subscription_changes.subscriptions_before_cleanup = subscription_count
            
            # Log summary in the requested format
            for activity, activity_data in disk_data.items():
                seasons_info = []
                total_episodes = sum(activity_data.episode_count.values())
                
                for season in sorted(activity_data.max_episode.keys()):
                    actual_count = activity_data.episode_count.get(season, 0)
                    max_ep = activity_data.max_episode.get(season, 0)
                    seasons_info.append(f"Season {season}: {actual_count} episodes (max E{max_ep})")
                
                logger.info(f"{activity.name} episodes ({total_episodes} total): {'; '.join(seasons_info)}")
            
            # Update existing subscription directories to match configuration
            logger.info("Updating subscription directories to match configuration...")
            file_manager.update_subscription_directories(config.media_dir)
            
            # Find existing class IDs to avoid duplicates
            logger.info("Finding existing class IDs...")
            existing_ids = file_manager.find_all_existing_class_ids()
            logger.info(f"Found {len(existing_ids)} existing classes to skip")
            metrics.existing_episodes.existing_class_ids_count = len(existing_ids)
            
            # Get stale and near-timeout subscriptions BEFORE cleanup
            stale_ids = file_manager.subscription_history_manager.get_stale_subscription_ids()
            metrics.subscription_history.stale_subscriptions_found = len(stale_ids)
            
            # Clean up subscriptions file
            logger.info("Cleaning up subscriptions file...")
            changes_made, total_removed = file_manager.cleanup_subscriptions()
            if changes_made:
                logger.info(f"Removed {total_removed} subscriptions from subscriptions file")
                # Split the removals between already-downloaded and stale
                # We'll estimate based on what we know about stale IDs
                if stale_ids:
                    metrics.subscription_changes.subscriptions_removed_stale = len(stale_ids)
                    metrics.subscription_changes.subscriptions_removed_already_downloaded = total_removed - len(stale_ids)
                else:
                    metrics.subscription_changes.subscriptions_removed_already_downloaded = total_removed
            else:
                logger.info("No cleanup needed in subscriptions file")
            
            # Sync existing subscriptions to history file
            logger.info("Syncing existing subscriptions to history file...")
            if not file_manager.subscription_history_manager.sync_existing_subscriptions():
                logger.warning("Failed to sync existing subscriptions to history file")
            
            metrics.subscription_history.history_synced = True
            
            # Get subscriptions data AFTER cleanup to get accurate counts
            logger.info("Getting subscriptions data after cleanup...")
            subscriptions_data_after_cleanup = file_manager.get_subscriptions_episode_data()
            
            subscription_count_after = sum(
                sum(activity_data.episode_count.values()) 
                for activity_data in subscriptions_data_after_cleanup.values()
            )
            metrics.existing_episodes.total_subscriptions_after_cleanup = subscription_count_after
            metrics.subscription_changes.subscriptions_after_cleanup = subscription_count_after
            
            # Store subscription counts by activity after cleanup
            for activity, activity_data in subscriptions_data_after_cleanup.items():
                activity_count = sum(activity_data.episode_count.values())
                metrics.subscription_changes.subscriptions_after_cleanup_by_activity[activity.name.lower()] = activity_count
            
            # Log subscriptions-only summary (after cleanup) using actual class counts
            for activity, activity_data in subscriptions_data_after_cleanup.items():
                # Get actual class count for this activity from subscriptions
                actual_count = 0
                for parser in file_manager.episode_manager.episode_parsers:
                    if 'subscription' in parser.__class__.__name__.lower():
                        try:
                            if hasattr(parser, 'find_subscription_class_ids_for_activity'):
                                activity_class_ids = parser.find_subscription_class_ids_for_activity(activity)
                                actual_count = len(activity_class_ids)
                                break
                        except Exception as e:
                            logger.error(f"Failed to get subscription class count for logging {activity}: {e}")
                
                logger.info(f"{activity.name} subscriptions: {actual_count} classes in subscriptions.yaml (after cleanup)")
            
            # Collect subscription history metrics
            tracked_ids = file_manager.subscription_history_manager.get_all_tracked_ids()
            metrics.subscription_history.total_tracked_subscriptions = len(tracked_ids)
            metrics.subscription_history.purge_limit_days = config.subscription_timeout_days
            metrics.subscription_history.warning_threshold_days = config.subscription_warning_threshold_days
            
            near_timeout_ids = file_manager.subscription_history_manager.get_subscriptions_near_timeout(
                config.subscription_warning_threshold_days
            )
            metrics.subscription_history.subscriptions_near_purge_limit = len(near_timeout_ids)
            
            # Implement actual Peloton scraping
            logger.info("Starting web scraping workflow")
            
            # Set scraping config values in metrics
            metrics.web_scraping.page_scrolls_config = config.peloton_page_scrolls
            metrics.web_scraping.dynamic_scrolling_enabled = config.peloton_dynamic_scrolling
            metrics.web_scraping.max_scrolls_config = config.peloton_max_scrolls
            metrics.web_scraping.class_limit_per_activity = config.peloton_class_limit_per_activity
            
            # Get scraper configuration
            scrapers_config = getattr(config, 'scrapers', {})
            if not scrapers_config:
                logger.error("No scrapers configuration found")
                metrics.finalize(success=False, error_message="No scrapers configuration found")
                return 1
            
            # Find Peloton scraper
            peloton_scraper_config = scrapers_config.get('peloton.com')
            if not peloton_scraper_config:
                logger.error("No peloton.com scraper configuration found")
                metrics.finalize(success=False, error_message="No peloton.com scraper configuration found")
                return 1
            
            try:
                # Create scraper manager
                from ..webscraper.scraper_factory import ScraperFactory
                from ..webscraper.models import ScrapingConfig
                
                logger.info("Creating Peloton scraper")
                scraper_manager = ScraperFactory.create_scraper(peloton_scraper_config)
                
                # Prepare scraping configurations for each activity
                scraping_configs = {}
                activities_to_scrape = []
                existing_class_ids = file_manager.find_all_existing_class_ids()
                
                # Get merged data for episode numbering (includes disk + subscriptions)
                merged_data = file_manager.get_merged_episode_data()
                
                # Filter activities that need scraping (not at or over limit)
                for activity in config.peloton_activities:
                    # Get episode numbering data for this activity (from merged data - includes disk + subscriptions)
                    activity_data = merged_data.get(activity)
                    episode_numbering = {}
                    if activity_data:
                        episode_numbering = dict(activity_data.max_episode)
                    
                    # Get subscriptions-only count for this activity (for limit checking)
                    subscriptions_count = 0
                    for parser in file_manager.episode_manager.episode_parsers:
                        if 'subscription' in parser.__class__.__name__.lower():
                            try:
                                if hasattr(parser, 'find_subscription_class_ids_for_activity'):
                                    activity_class_ids = parser.find_subscription_class_ids_for_activity(activity)
                                    subscriptions_count = len(activity_class_ids)
                                    logger.debug(f"Found {subscriptions_count} actual class IDs for {activity.name} in subscriptions")
                                    break
                            except Exception as e:
                                logger.error(f"Failed to get subscription class count for {activity}: {e}")
                    
                    if subscriptions_count == 0:
                        logger.warning(f"Could not get actual class count for {activity.name} - using 0 to prevent incorrect limits")
                    
                    # Check if activity is already at or over the limit
                    if subscriptions_count >= config.peloton_class_limit_per_activity:
                        logger.info(f"Skipping scraping for {activity.name}: already at limit ({subscriptions_count} >= {config.peloton_class_limit_per_activity})")
                        continue
                    
                    # Activity needs scraping - add to list and create config
                    activities_to_scrape.append(activity)
                    scraping_configs[activity.value] = ScrapingConfig(
                        activity=activity.value,
                        max_classes=config.peloton_class_limit_per_activity,
                        page_scrolls=config.peloton_page_scrolls,
                        existing_class_ids=existing_class_ids,
                        episode_numbering_data=episode_numbering,
                        subscriptions_existing_classes=subscriptions_count,
                        headless=peloton_scraper_config.get('headless', True),
                        container_mode=config.run_in_container,
                        scroll_pause_time=peloton_scraper_config.get('scroll_pause_time', 3.0),
                        login_wait_time=peloton_scraper_config.get('login_wait_time', 15.0),
                        page_load_wait_time=peloton_scraper_config.get('page_load_wait_time', 10.0),
                        dynamic_scrolling=config.peloton_dynamic_scrolling,
                        max_scrolls=config.peloton_max_scrolls
                    )
                
                # Perform scraping only for activities that need it
                if activities_to_scrape:
                    logger.info(f"Scraping {len(activities_to_scrape)} activities (skipped {len(config.peloton_activities) - len(activities_to_scrape)} already at limit)")
                    scraping_results = scraper_manager.scrape_activities(
                        username=config.peloton_username,
                        password=config.peloton_password,
                        activities=[activity.value for activity in activities_to_scrape],
                        configs=scraping_configs
                    )
                else:
                    logger.info("No activities need scraping - all are already at or over the limit")
                    scraping_results = {}
                
                # Process results and update subscriptions
                total_new_classes = 0
                new_subscription_urls = []
                for activity_name, result in scraping_results.items():
                    # Collect scraping metrics
                    activity_stats = ActivityScrapingStats(
                        activity=activity_name,
                        classes_found=result.total_found,
                        classes_skipped=result.total_skipped,
                        classes_added=len(result.classes) if result.status.value == "completed" else 0,
                        errors=result.total_errors,
                        scrolls_performed=result.scrolls_performed,
                        status=result.status.value,
                        error_message=result.error_message
                    )
                    metrics.web_scraping.activities[activity_name] = activity_stats
                    metrics.web_scraping.total_classes_found += result.total_found
                    metrics.web_scraping.total_classes_skipped += result.total_skipped
                    metrics.web_scraping.total_errors += result.total_errors
                    
                    if result.status.value == "completed":
                        subscription_data = result.get_subscription_data(config.media_dir)
                        if subscription_data:
                            # Add to subscriptions file
                            file_manager.add_new_subscriptions(subscription_data)
                            total_new_classes += len(result.classes)
                            metrics.web_scraping.total_classes_added += len(result.classes)
                            metrics.subscription_changes.subscriptions_added_new += len(result.classes)
                            logger.info(f"Added {len(result.classes)} new {activity_name} classes")
                            
                            # Collect URLs for tracking
                            for class_info in result.classes:
                                if hasattr(class_info, 'player_url') and class_info.player_url:
                                    new_subscription_urls.append(class_info.player_url)
                        else:
                            logger.info(f"No new {activity_name} subscriptions to add")
                    else:
                        logger.error(f"Failed to scrape {activity_name}: {result.error_message}")
                
                metrics.web_scraping.total_activities_scraped = len(scraping_results)
                
                if total_new_classes > 0:
                    logger.info(f"Successfully added {total_new_classes} new subscriptions to subscriptions")
                    
                    # Track new subscriptions in history file
                    if new_subscription_urls:
                        logger.info("Tracking new subscriptions in history file")
                        if file_manager.track_new_subscriptions(new_subscription_urls):
                            metrics.subscription_history.subscriptions_added_to_history = len(new_subscription_urls)
                        else:
                            logger.warning("Failed to track new subscriptions in history file")
                else:
                    logger.info("No new subscriptions found to add")
                
                # Final validation: Check for path conflicts and resolve them
                logger.info("Validating subscription file against filesystem for conflicts...")
                file_manager.validate_and_resolve_subscription_conflicts()
                
                # Get final activity totals after scraping
                final_merged_data = file_manager.get_merged_episode_data()
                total_final_subscriptions = 0
                for activity, activity_data in final_merged_data.items():
                    # Use actual subscription count instead of episode numbers
                    actual_subscription_count = 0
                    for parser in file_manager.episode_manager.episode_parsers:
                        if 'subscription' in parser.__class__.__name__.lower():
                            try:
                                if hasattr(parser, 'find_subscription_class_ids_for_activity'):
                                    activity_class_ids = parser.find_subscription_class_ids_for_activity(activity)
                                    actual_subscription_count = len(activity_class_ids)
                                    break
                            except Exception as e:
                                logger.error(f"Failed to get final subscription class count for {activity}: {e}")
                    
                    metrics.web_scraping.activity_totals[activity.name] = actual_subscription_count
                    total_final_subscriptions += actual_subscription_count
                    
                    # Check if over limit using actual subscription count (not episode numbers)
                    if actual_subscription_count > config.peloton_class_limit_per_activity:
                        metrics.web_scraping.activities_over_limit.append(activity.name)
                        logger.warning(f"⚠️  Activity {activity.name} has {actual_subscription_count} subscriptions, exceeding limit of {config.peloton_class_limit_per_activity}")
                
                # Update the final subscription count for accurate delta calculation
                metrics.existing_episodes.total_subscriptions_in_yaml = total_final_subscriptions
                
            except Exception as e:
                logger.error(f"Web scraping failed: {e}")
                metrics.finalize(success=False, error_message=f"Web scraping failed: {e}")
                if github_manager:
                    github_manager.cleanup()
                return 1
            
            # Finalize metrics
            metrics.finalize(success=True)
            
            # Log metrics summary
            logger.info("\n" + "="*60)
            logger.info(metrics.get_summary())
            logger.info("="*60)
            
            # Log detailed PR-style summary
            logger.info("\n" + "="*60)
            logger.info(metrics.get_pr_summary(file_manager.subscription_history_manager))
            logger.info("="*60)
            
            # Save run snapshot
            snapshot = metrics.create_snapshot()
            if not file_manager.subscription_history_manager.save_run_snapshot(snapshot):
                logger.warning("Failed to save run snapshot to history file")
            
            # Finalize GitHub integration if enabled
            if github_manager:
                logger.info("Finalizing GitHub integration...")
                
                # Generate PR body with metrics
                pr_body = metrics.get_pr_summary(file_manager.subscription_history_manager)
                
                finalize_result = github_manager.finalize_subscription_updates(
                    pr_title=f"Auto-update subscriptions - {metrics.run_id}",
                    pr_body=pr_body
                )
                
                if finalize_result.success:
                    if finalize_result.pr_url:
                        logger.info(f"GitHub workflow completed successfully: {finalize_result.pr_url}")
                    else:
                        logger.info(f"GitHub workflow completed: {finalize_result.message}")
                else:
                    logger.error(f"GitHub workflow failed: {finalize_result.message}")
                    github_manager.cleanup()
                    return 1
                
                # Cleanup resources
                github_manager.cleanup()
            
            logger.info("Scraping workflow completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Application error: {e}", exc_info=True)
            metrics.finalize(success=False, error_message=str(e))
            if github_manager:
                github_manager.cleanup()
            return 1
    
    
    def run_validate_command(self, args: argparse.Namespace) -> int:
        """Run the validate command with the given arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 for success, non-zero for error)
        """
        try:
            logger.info("Starting directory validation...")
            
            # Create validator with default Peloton strategies
            validator = GenericDirectoryValidator(
                media_dir=args.media_dir,
                validation_strategies=["src.io.peloton.activity_based_path_strategy:ActivityBasedPathStrategy"],
                repair_strategies=["src.io.peloton.repair_5050_strategy:Repair5050Strategy"],
                dry_run=args.dry_run
            )
            
            # Run validation and repair
            success = validator.validate_and_repair()
            
            if success:
                if args.dry_run:
                    logger.info("Directory validation completed (dry run)")
                else:
                    logger.info("Directory validation and repair completed successfully")
                return 0
            else:
                logger.error("Directory validation failed")
                return 1
                
        except Exception as e:
            logger.error(f"Directory validation failed: {e}")
            return 1
