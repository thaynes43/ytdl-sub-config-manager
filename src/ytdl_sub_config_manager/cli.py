"""Command-line interface for ytdl-sub config manager."""

import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from .core.config import ConfigLoader
from .core.logging import setup_logging, get_logger


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="ytdl-sub Config Manager - Peloton scraper for ytdl-sub subscriptions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s scrape --source peloton --limit 25
  %(prog)s scrape --activities cycling,yoga --subs-file /path/to/subs.yaml
  %(prog)s scrape --config config.yaml --log-level DEBUG
        """
    )
    
    # Global options
    parser.add_argument(
        "--config",
        type=str,
        help="Path to YAML configuration file"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set logging level (default: INFO)"
    )
    parser.add_argument(
        "--log-format",
        choices=["standard", "json"],
        default="standard",
        help="Set log format (default: standard)"
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scrape command
    scrape_parser = subparsers.add_parser(
        "scrape",
        help="Run the scraping workflow"
    )
    
    # Peloton configuration
    peloton_group = scrape_parser.add_argument_group("Peloton Configuration")
    peloton_group.add_argument(
        "--source",
        choices=["peloton"],
        default="peloton",
        help="Source to scrape (currently only peloton supported)"
    )
    peloton_group.add_argument(
        "--username",
        type=str,
        help="Peloton username (overrides PELOTON_USERNAME env var)"
    )
    peloton_group.add_argument(
        "--password",
        type=str,
        help="Peloton password (overrides PELOTON_PASSWORD env var)"
    )
    peloton_group.add_argument(
        "--activities",
        type=str,
        help="Comma-separated list of activities to scrape (e.g., cycling,yoga)"
    )
    peloton_group.add_argument(
        "--limit",
        type=int,
        help="Maximum classes to scrape per activity (default: 25)"
    )
    peloton_group.add_argument(
        "--scrolls",
        type=int,
        help="Number of page scrolls to perform (default: 10)"
    )
    
    # File paths
    file_group = scrape_parser.add_argument_group("File Configuration")
    file_group.add_argument(
        "--media-dir",
        type=str,
        help="Path to media directory for inventory scanning"
    )
    file_group.add_argument(
        "--subs-file",
        type=str,
        help="Path to subscriptions YAML file"
    )
    
    # GitHub integration
    github_group = scrape_parser.add_argument_group("GitHub Integration")
    github_group.add_argument(
        "--github-repo",
        type=str,
        help="GitHub repository URL for PR creation"
    )
    github_group.add_argument(
        "--github-token",
        type=str,
        help="GitHub token for repository access"
    )
    
    # Runtime options
    runtime_group = scrape_parser.add_argument_group("Runtime Options")
    runtime_group.add_argument(
        "--container",
        action="store_true",
        help="Run in container mode (use system chromium)"
    )
    runtime_group.add_argument(
        "--no-container",
        action="store_true",
        help="Run in local mode (use webdriver-manager)"
    )
    
    return parser


def parse_args(args: Optional[list] = None) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Validate arguments
    if not parsed_args.command:
        parser.error("No command specified. Use 'scrape' to run the scraping workflow.")
    
    # Handle container/no-container conflict
    if parsed_args.command == "scrape":
        if parsed_args.container and parsed_args.no_container:
            parser.error("Cannot specify both --container and --no-container")
    
    return parsed_args


def args_to_dict(args: argparse.Namespace) -> Dict[str, Any]:
    """Convert parsed arguments to dictionary for config loading."""
    config_dict = {}
    
    # Map CLI args to config keys
    if hasattr(args, 'username') and args.username:
        config_dict['username'] = args.username
    if hasattr(args, 'password') and args.password:
        config_dict['password'] = args.password
    if hasattr(args, 'activities') and args.activities:
        config_dict['activities'] = args.activities
    if hasattr(args, 'limit') and args.limit:
        config_dict['limit'] = args.limit
    if hasattr(args, 'scrolls') and args.scrolls:
        config_dict['scrolls'] = args.scrolls
    if hasattr(args, 'media_dir') and args.media_dir:
        config_dict['media_dir'] = args.media_dir
    if hasattr(args, 'subs_file') and args.subs_file:
        config_dict['subs_file'] = args.subs_file
    if hasattr(args, 'github_repo') and args.github_repo:
        config_dict['github_repo'] = args.github_repo
    if hasattr(args, 'github_token') and args.github_token:
        config_dict['github_token'] = args.github_token
    
    # Handle container flag
    if hasattr(args, 'container') and args.container:
        config_dict['container'] = True
    elif hasattr(args, 'no_container') and args.no_container:
        config_dict['container'] = False
    
    # Add global options
    if args.log_level:
        config_dict['log_level'] = args.log_level
    if args.log_format:
        config_dict['log_format'] = args.log_format
    
    return config_dict


def run_scrape_command(config) -> int:
    """Run the scrape command with the given configuration.
    
    Args:
        config: Configuration object
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    logger = get_logger(__name__)
    
    try:
        logger.info("Starting Peloton scraping workflow...")
        
        # Log the configuration
        config.log_config()
        
        # TODO: Implement actual scraping workflow
        logger.info("Scraping workflow completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Scraping workflow failed: {e}")
        return 1


def main() -> int:
    """Main entry point for the CLI."""
    try:
        # Parse command line arguments
        args = parse_args()
        
        # Set up logging early
        setup_logging(level=args.log_level, format_type=args.log_format)
        logger = get_logger(__name__)
        
        logger.info("Starting ytdl-sub Config Manager")
        
        # Load configuration
        config_loader = ConfigLoader()
        cli_config = args_to_dict(args)
        
        try:
            config = config_loader.load_config(
                config_file=args.config,
                cli_args=cli_config
            )
        except Exception as e:
            logger.error(f"Configuration error: {e}")
            return 1
        
        # Execute command
        if args.command == "scrape":
            return run_scrape_command(config)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        # Set up basic logging if it wasn't set up yet
        if not get_logger(__name__).handlers:
            setup_logging()
        logger = get_logger(__name__)
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
