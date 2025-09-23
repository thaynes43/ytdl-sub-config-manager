"""Main application logic for ytdl-sub config manager."""

import argparse
from typing import Dict, Any

from ..io.file_manager import FileManager
from ..io.generic_directory_validator import GenericDirectoryValidator
from .logging import get_logger

logger = get_logger(__name__)


class Application:
    """Main application class that orchestrates the scraping workflow."""
    
    def __init__(self):
        pass
    
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
        logger.info("Starting Peloton scraping workflow...")
        
        # Log the configuration
        config.log_config()
        
        # Initialize file manager (with validation unless skipped)
        skip_validation = getattr(config, 'skip_validation', False)
        file_manager = FileManager(
            media_dir=config.media_dir,
            subs_file=config.subs_file,
            validate_and_repair=not skip_validation,
            validation_strategies=config.peloton_directory_validation_strategies,
            repair_strategies=config.peloton_directory_repair_strategies,
            episode_parsers=config.peloton_episode_parsers
        )
        
        # Get merged episode data to understand current state
        logger.info("Analyzing current episode data...")
        merged_data = file_manager.get_merged_episode_data()
        logger.info(f"Found {len(merged_data)} activities with existing episodes.")
        
        # Log summary in the requested format
        for activity, activity_data in merged_data.items():
            seasons_info = []
            total_episodes = sum(activity_data.max_episode.values())
            
            for season in sorted(activity_data.max_episode.keys()):
                max_ep = activity_data.max_episode[season]
                seasons_info.append(f"Season {season}: {max_ep} episodes (max E{max_ep})")
            
            logger.info(f"{activity.name} episodes ({total_episodes} total): {'; '.join(seasons_info)}")
        
        # Find existing class IDs to avoid duplicates
        logger.info("Finding existing class IDs...")
        existing_ids = file_manager.find_all_existing_class_ids()
        logger.info(f"Found {len(existing_ids)} existing classes to skip")
        
        # Clean up subscriptions file
        logger.info("Cleaning up subscriptions file...")
        changes_made = file_manager.cleanup_subscriptions()
        if changes_made:
            logger.info("Removed already-downloaded classes from subscriptions")
        else:
            logger.info("No cleanup needed in subscriptions file")
        
        # Implement actual Peloton scraping
        logger.info("Starting web scraping workflow")
        
        # Get scraper configuration
        scrapers_config = getattr(config, 'scrapers', {})
        if not scrapers_config:
            logger.error("No scrapers configuration found")
            return 1
        
        # Find Peloton scraper
        peloton_scraper_config = scrapers_config.get('peloton.com')
        if not peloton_scraper_config:
            logger.error("No peloton.com scraper configuration found")
            return 1
        
        try:
            # Create scraper manager
            from ..webscraper.scraper_factory import ScraperFactory
            from ..webscraper.models import ScrapingConfig
            
            logger.info("Creating Peloton scraper")
            scraper_manager = ScraperFactory.create_scraper(peloton_scraper_config)
            
            # Prepare scraping configurations for each activity
            scraping_configs = {}
            existing_class_ids = file_manager.find_all_existing_class_ids()
            
            for activity in config.peloton_activities:
                # Get episode numbering data for this activity
                activity_data = merged_data.get(activity)
                episode_numbering = {}
                if activity_data:
                    episode_numbering = dict(activity_data.max_episode)
                
                scraping_configs[activity.value] = ScrapingConfig(
                    activity=activity.value,
                    max_classes=config.peloton_class_limit_per_activity,
                    page_scrolls=config.peloton_page_scrolls,
                    existing_class_ids=existing_class_ids,
                    episode_numbering_data=episode_numbering,
                    headless=peloton_scraper_config.get('headless', True),
                    container_mode=peloton_scraper_config.get('container_mode', True),
                    scroll_pause_time=peloton_scraper_config.get('scroll_pause_time', 3.0),
                    login_wait_time=peloton_scraper_config.get('login_wait_time', 15.0),
                    page_load_wait_time=peloton_scraper_config.get('page_load_wait_time', 10.0)
                )
            
            # Perform scraping
            logger.info(f"Scraping {len(config.peloton_activities)} activities")
            scraping_results = scraper_manager.scrape_activities(
                username=config.peloton_username,
                password=config.peloton_password,
                activities=[activity.value for activity in config.peloton_activities],
                configs=scraping_configs
            )
            
            # Process results and update subscriptions
            total_new_classes = 0
            for activity_name, result in scraping_results.items():
                if result.status.value == "completed":
                    subscription_data = result.get_subscription_data()
                    if subscription_data:
                        # Add to subscriptions file
                        file_manager.add_new_classes(subscription_data)
                        total_new_classes += len(result.classes)
                        logger.info(f"Added {len(result.classes)} new {activity_name} classes")
                    else:
                        logger.info(f"No new {activity_name} classes to add")
                else:
                    logger.error(f"Failed to scrape {activity_name}: {result.error_message}")
            
            if total_new_classes > 0:
                logger.info(f"Successfully added {total_new_classes} new classes to subscriptions")
            else:
                logger.info("No new classes found to add")
                
        except Exception as e:
            logger.error(f"Web scraping failed: {e}")
            return 1
        
        logger.info("Scraping workflow completed successfully")
        return 0
    
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
