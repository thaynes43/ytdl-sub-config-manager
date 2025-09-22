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
        
        # TODO: Implement actual Peloton scraping
        logger.warning("Actual Peloton scraping not yet implemented")
        logger.info("Scraping workflow would continue with:")
        logger.info("1. Initialize Peloton session")
        logger.info("2. Scrape classes for each configured activity")
        logger.info("3. Generate episode data with correct numbering")
        logger.info("4. Update subscriptions file")
        logger.info("5. Create GitHub PR if configured")
        
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
